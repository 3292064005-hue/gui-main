from __future__ import annotations

import json
import os
import socket
import threading
from collections import deque
from pathlib import Path
from typing import Any, Optional

import httpx
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils import ensure_dir, now_ns, now_text

from .api_bridge_backend_helpers import build_command_headers, decode_pixmap_payload, remember_backend_error
from .backend_authoritative_contract_service import BackendAuthoritativeContractService
from .backend_base import BackendBase
from .backend_control_plane_service import BackendControlPlaneService
from .backend_error_mapper import BackendErrorMapper
from .backend_errors import BackendOperationError, normalize_backend_exception
from .backend_link_service import BackendLinkMetrics, BackendLinkService
from .backend_projection_cache import BackendProjectionCache
from .ipc_protocol import ReplyEnvelope, TelemetryEnvelope
from .scan_plan_contract import runtime_scan_plan_payload

try:  # pragma: no cover
    from websockets.sync.client import connect as ws_connect
    from websockets.exceptions import WebSocketException
except ImportError:  # pragma: no cover
    ws_connect = None  # type: ignore
    WebSocketException = RuntimeError  # type: ignore


ERROR_HISTORY_LIMIT = 8
INITIAL_WS_RECONNECT_DELAY_S = 0.25
MAX_WS_RECONNECT_DELAY_S = 2.0


class ApiBridgeBackend(QObject, BackendBase):
    """HTTP/WebSocket backend for the headless adapter surface.

    Public methods and signals intentionally preserve the legacy backend shape.
    Internally the backend now normalizes authoritative runtime facts through a
    shared service and tracks partition revisions for control-plane caching.
    """

    telemetry_received = Signal(object)
    log_generated = Signal(str, str)
    camera_pixmap_ready = Signal(QPixmap)
    ultrasound_pixmap_ready = Signal(QPixmap)
    reconstruction_pixmap_ready = Signal(QPixmap)

    def __init__(
        self,
        root_dir: Path,
        base_url: str = "http://127.0.0.1:8000",
        *,
        request_timeout_s: float = 4.0,
        health_poll_interval_s: float = 1.0,
        snapshot_poll_interval_s: float = 0.5,
    ) -> None:
        """Create the API bridge backend.

        Args:
            root_dir: Runtime working directory for persisted local artifacts.
            base_url: Base HTTP URL for the headless adapter.
            request_timeout_s: Per-request timeout in seconds.
            health_poll_interval_s: Poll period for status/health/control-plane.
            snapshot_poll_interval_s: Poll period for REST telemetry fallback.
        """
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.config = RuntimeConfig()
        self.link_service = BackendLinkService()
        self.base_url = self.link_service.normalize_http_base(base_url)
        self.ws_base = self.link_service.infer_ws_base(self.base_url)
        self.request_timeout_s = float(request_timeout_s)
        self.health_poll_interval_s = float(health_poll_interval_s)
        self.snapshot_poll_interval_s = float(snapshot_poll_interval_s)
        self._client = httpx.Client(base_url=self.base_url, timeout=self.request_timeout_s)
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._status_cache: dict[str, Any] = {}
        self._health_cache: dict[str, Any] = {}
        self._runtime_config_cache: dict[str, Any] = {}
        self._schema_cache: dict[str, Any] = {}
        self._topic_catalog_cache: dict[str, Any] = {}
        self._recent_commands_cache: list[dict[str, Any]] = []
        self._control_plane_cache: dict[str, Any] = {}
        self._control_authority_cache: dict[str, Any] = {}
        self._authoritative_envelope: dict[str, Any] = {}
        self._last_errors: deque[str] = deque(maxlen=ERROR_HISTORY_LIMIT)
        self._last_final_verdict: dict[str, Any] = {}
        self._control_plane_service = BackendControlPlaneService()
        self._authoritative_service = BackendAuthoritativeContractService()
        self._projection_cache = BackendProjectionCache()
        self._metrics = BackendLinkMetrics(using_websocket_telemetry=ws_connect is not None, using_websocket_media=ws_connect is not None)
        self._actor_id = os.getenv("SPINE_ACTOR_ID", f"desktop-{socket.gethostname()}")
        self._workspace = os.getenv("SPINE_WORKSPACE", "desktop")
        self._role = os.getenv("SPINE_ROLE", "operator")
        self._lease_id = ""

    def start(self) -> None:
        """Start polling/streaming loops and synchronize local runtime config."""
        if self._threads:
            return
        self._stop.clear()
        self._spawn(self._health_loop, "api-health-loop")
        if ws_connect is not None:
            self._spawn(self._telemetry_ws_loop, "api-telemetry-ws")
            self._spawn(lambda: self._media_ws_loop("camera", self.camera_pixmap_ready), "api-camera-ws")
            self._spawn(lambda: self._media_ws_loop("ultrasound", self.ultrasound_pixmap_ready), "api-ultrasound-ws")
        else:
            self._spawn(self._snapshot_poll_loop, "api-snapshot-poll")
            self._log("WARN", "websockets 依赖不可用，已退回 REST 快照轮询模式。")
        self._ensure_control_lease()
        self._push_runtime_config()
        self._log("INFO", f"ApiBridgeBackend 已启动，HTTP {self.base_url} / WS {self.ws_base}")

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        """Update desired runtime config and push it to the API surface."""
        self.config = config
        self._projection_cache.update_partition("desired_runtime_config", config.to_dict())
        self._push_runtime_config()

    def send_command(self, command: str, payload: Optional[dict] = None, *, context: Optional[dict] = None) -> ReplyEnvelope:
        """Send a command to the HTTP command surface.

        Args:
            command: Canonical runtime command name.
            payload: Command payload dictionary.
            context: Optional command-side control/actor context.

        Returns:
            A normalized reply envelope. Transport errors are converted to the
            existing compatibility reply shape through BackendErrorMapper.
        """
        request_payload = dict(payload or {})
        command_context = dict(context or {})
        started_ns = now_ns()
        with self._lock:
            self._metrics.commands_sent += 1
            self._metrics.last_command = command
        self._ensure_control_lease(force=bool(command_context.get("force_lease_refresh")))
        try:
            response = self._client.post(
                f"/api/v1/commands/{command}",
                json=request_payload,
                headers=build_command_headers(
                    intent=str(command_context.get("intent_reason") or command),
                    actor_id=str(command_context.get("actor_id") or self._actor_id),
                    workspace=str(command_context.get("workspace") or self._workspace),
                    role=str(command_context.get("role") or self._role),
                    session_id=str(command_context.get("session_id") or ""),
                    include_lease=bool(command_context.get("include_lease", True)),
                ),
            )
            latency_ms = int((now_ns() - started_ns) / 1_000_000)
            with self._lock:
                self._metrics.last_command_latency_ms = latency_ms
            body = response.json() if response.content else {}
            if response.status_code >= 400:
                detail = body.get("detail") if isinstance(body, dict) else None
                message = str(detail or f"HTTP {response.status_code}")
                with self._lock:
                    self._metrics.commands_failed += 1
                    self._metrics.last_error = message
                remember_backend_error(self._last_errors, f"{command}: {message}")
                self._log("WARN", f"API {command}: {message}")
                return BackendErrorMapper.reply_from_exception(RuntimeError(message), data={"http_status": response.status_code, "command": command}, command=command, context="api-command")
            reply = ReplyEnvelope(
                ok=bool(body.get("ok", False)),
                message=str(body.get("message", "")),
                request_id=str(body.get("request_id", "")),
                data=dict(body.get("data", {})),
                protocol_version=int(body.get("protocol_version", 1)),
            )
            self._capture_reply_contracts(reply)
            if not reply.ok:
                with self._lock:
                    self._metrics.commands_failed += 1
                    self._metrics.last_error = reply.message
                if "控制权" in reply.message or "lease" in reply.message.lower():
                    self._ensure_control_lease(force=True)
                remember_backend_error(self._last_errors, f"{command}: {reply.message}")
            self._log("INFO" if reply.ok else "WARN", f"API {command}: {reply.message or ('OK' if reply.ok else 'FAILED')}")
            return reply
        except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
            normalized = normalize_backend_exception(exc, command=command, context="api-command")
            with self._lock:
                self._metrics.commands_failed += 1
                self._metrics.last_error = normalized.message
            remember_backend_error(self._last_errors, f"{command}: {normalized.error_type}: {normalized.message}")
            self._log("ERROR", f"API {command} 失败：{normalized.error_type}: {normalized.message}")
            return BackendErrorMapper.reply_from_exception(normalized, data={"command": command}, command=command, context="api-command")

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._status_cache)

    def health(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._health_cache)

    def link_snapshot(self) -> dict[str, Any]:
        """Build the canonical backend-link snapshot consumed by the desktop UI."""
        with self._lock:
            status = dict(self._status_cache)
            health = dict(self._health_cache)
            metrics = BackendLinkMetrics(**self._metrics.__dict__)
            errors = list(self._last_errors)
            control_plane = dict(self._control_plane_cache)
            authoritative_envelope = dict(self._authoritative_envelope)
            if self._control_authority_cache:
                control_plane.setdefault("control_authority", dict(self._control_authority_cache))
            if authoritative_envelope:
                control_plane["authoritative_runtime_envelope"] = authoritative_envelope
                control_plane.setdefault("control_authority", dict(authoritative_envelope.get("control_authority", {})))
                control_plane["runtime_config_applied"] = dict(authoritative_envelope.get("runtime_config_applied", {}))
                control_plane["final_verdict"] = dict(authoritative_envelope.get("final_verdict", {}))
                control_plane["session_freeze"] = dict(authoritative_envelope.get("session_freeze", {}))
                control_plane["plan_digest"] = dict(authoritative_envelope.get("plan_digest", {}))
                projection_snapshot = self._projection_cache.snapshot()
                control_plane["projection_revision"] = projection_snapshot["revision"]
                control_plane["projection_partitions"] = projection_snapshot["partitions"]
        return self.link_service.build_snapshot(
            mode="api",
            http_base=self.base_url,
            ws_base=self.ws_base,
            status=status,
            health=health,
            metrics=metrics,
            extra_errors=errors,
            control_plane=control_plane,
            local_runtime_config=self.config.to_dict(),
        )

    def get_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict[str, Any]:
        """Return the authoritative final verdict for the active or supplied plan."""
        query_payloads = []
        if plan is not None:
            query_payloads.append((
                "compile_scan_plan",
                {
                    "scan_plan": runtime_scan_plan_payload(plan),
                    "config_snapshot": config.to_dict() if config is not None else self.config.to_dict(),
                },
            ))
        query_payloads.append(("query_final_verdict", {}))
        for command_name, payload in query_payloads:
            reply = self.send_command(command_name, payload, context={"include_lease": False, "intent_reason": command_name})
            verdict = self._authoritative_service.extract_final_verdict(reply.data)
            if verdict:
                return verdict
        with self._lock:
            cached = dict(self._last_final_verdict)
            control_plane = dict(self._control_plane_cache)
        return cached or self._authoritative_service.extract_final_verdict(control_plane)

    def close(self) -> None:
        """Stop background loops and close the HTTP client."""
        self._stop.set()
        for thread in list(self._threads):
            if thread.is_alive():
                thread.join(timeout=1.0)
        self._threads.clear()
        self._client.close()

    def _spawn(self, target, name: str) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        self._threads.append(thread)
        thread.start()

    def _push_runtime_config(self) -> None:
        """Push desired runtime config to the adapter and refresh local cache."""
        try:
            response = self._client.put(
                "/api/v1/runtime-config",
                json=self.config.to_dict(),
                headers=self._command_headers(intent="runtime-config", include_lease=False),
            )
            response.raise_for_status()
            body = response.json() if response.content else {}
            with self._lock:
                self._runtime_config_cache = dict(body)
            self._projection_cache.update_partition("runtime_config", body)
            self._log("INFO", "运行配置已同步到 headless API。")
        except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
            normalized = normalize_backend_exception(exc, context="runtime-config")
            remember_backend_error(self._last_errors, f"runtime-config: {normalized.error_type}: {normalized.message}")
            self._log("WARN", f"运行配置同步失败：{normalized.error_type}: {normalized.message}")

    def _health_loop(self) -> None:
        """Continuously refresh status, health, and control-plane snapshots."""
        while not self._stop.is_set():
            try:
                status_resp = self._client.get("/api/v1/status")
                status_resp.raise_for_status()
                health_resp = self._client.get("/api/v1/health")
                health_resp.raise_for_status()
                control_resp = self._client.get("/api/v1/control-plane")
                control_resp.raise_for_status()
                status = status_resp.json()
                health = health_resp.json()
                control_plane = control_resp.json()
                authoritative_envelope = self._authoritative_service.normalize_payload(
                    control_plane,
                    authority_source="api_bridge",
                    desired_runtime_config=self.config,
                    fallback_control_authority=self._control_authority_cache,
                )
                with self._lock:
                    self._status_cache = status
                    self._health_cache = health
                    self._control_plane_cache = dict(control_plane)
                    self._control_authority_cache = dict(authoritative_envelope.get("control_authority", {}))
                    self._runtime_config_cache = dict(control_plane.get("runtime_config", {}))
                    self._schema_cache = dict(control_plane.get("schema", {}))
                    self._topic_catalog_cache = dict(control_plane.get("topics", {}))
                    self._recent_commands_cache = list(control_plane.get("recent_commands", {}).get("recent_commands", []))
                    self._last_final_verdict = dict(authoritative_envelope.get("final_verdict", {}))
                    self._authoritative_envelope = authoritative_envelope
                    self._metrics.rest_reachable = True
                    self._metrics.last_status_poll_ns = now_ns()
                self._projection_cache.update_partition("status", status)
                self._projection_cache.update_partition("health", health)
                self._projection_cache.update_partition("schema", self._schema_cache)
                self._projection_cache.update_partition("topics", self._topic_catalog_cache)
                self._projection_cache.update_partition("recent_commands", {"recent_commands": self._recent_commands_cache})
                self._projection_cache.update_partition("control_plane", control_plane)
                self._projection_cache.update_partition("control_authority", authoritative_envelope.get("control_authority", {}))
                self._projection_cache.update_partition("authoritative_runtime_envelope", authoritative_envelope)
                if ws_connect is None:
                    self._pull_snapshot_once()
            except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
                normalized = normalize_backend_exception(exc, context="health-loop")
                with self._lock:
                    self._metrics.rest_reachable = False
                    self._health_cache = {"adapter_running": False, "telemetry_stale": True}
                remember_backend_error(self._last_errors, f"health: {normalized.error_type}: {normalized.message}")
                self._log("WARN", f"API 健康检查失败：{normalized.error_type}: {normalized.message}")
            self._stop.wait(self.health_poll_interval_s)

    def _snapshot_poll_loop(self) -> None:
        while not self._stop.is_set():
            self._pull_snapshot_once()
            self._stop.wait(self.snapshot_poll_interval_s)

    def _pull_snapshot_once(self) -> None:
        """Pull telemetry snapshots through REST when WebSocket streaming is absent."""
        try:
            response = self._client.get("/api/v1/telemetry/snapshot")
            response.raise_for_status()
            items = response.json() if response.content else []
            if items:
                with self._lock:
                    self._metrics.telemetry_connected = True
                for item in items if isinstance(items, list) else []:
                    self._emit_snapshot_item(item)
            else:
                with self._lock:
                    self._metrics.telemetry_connected = False
        except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
            normalized = normalize_backend_exception(exc, context="snapshot-poll")
            with self._lock:
                self._metrics.telemetry_connected = False
            remember_backend_error(self._last_errors, f"snapshot: {normalized.error_type}: {normalized.message}")
            self._log("WARN", f"遥测快照拉取失败：{normalized.error_type}: {normalized.message}")

    def _telemetry_ws_loop(self) -> None:
        assert ws_connect is not None
        url = f"{self.ws_base}/ws/telemetry"
        reconnect_delay_s = INITIAL_WS_RECONNECT_DELAY_S
        while not self._stop.is_set():
            try:
                with ws_connect(url, open_timeout=self.request_timeout_s, close_timeout=1.0) as ws:
                    with self._lock:
                        self._metrics.telemetry_connected = True
                    reconnect_delay_s = INITIAL_WS_RECONNECT_DELAY_S
                    self._log("INFO", "已连接 headless telemetry WebSocket。")
                    for raw in ws:
                        if self._stop.is_set():
                            break
                        self._emit_snapshot_item(json.loads(raw))
            except (WebSocketException, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
                normalized = normalize_backend_exception(exc, context="telemetry-ws")
                with self._lock:
                    self._metrics.telemetry_connected = False
                    self._metrics.reconnect_count += 1
                remember_backend_error(self._last_errors, f"telemetry-ws: {normalized.error_type}: {normalized.message}")
                self._log("WARN", f"telemetry WebSocket 断开：{normalized.error_type}: {normalized.message}")
                self._stop.wait(reconnect_delay_s)
                reconnect_delay_s = min(MAX_WS_RECONNECT_DELAY_S, reconnect_delay_s * 2.0)

    def _media_ws_loop(self, channel: str, signal) -> None:
        assert ws_connect is not None
        url = f"{self.ws_base}/ws/{channel}"
        metric_name = f"{channel}_connected"
        reconnect_delay_s = INITIAL_WS_RECONNECT_DELAY_S
        while not self._stop.is_set():
            try:
                with ws_connect(url, open_timeout=self.request_timeout_s, close_timeout=1.0) as ws:
                    with self._lock:
                        setattr(self._metrics, metric_name, True)
                    reconnect_delay_s = INITIAL_WS_RECONNECT_DELAY_S
                    self._log("INFO", f"已连接 {channel} WebSocket。")
                    for raw in ws:
                        if self._stop.is_set():
                            break
                        pixmap = decode_pixmap_payload(raw)
                        if pixmap is not None:
                            signal.emit(pixmap)
            except (WebSocketException, OSError, RuntimeError, ValueError, TypeError) as exc:
                normalized = normalize_backend_exception(exc, context=f"{channel}-ws")
                with self._lock:
                    setattr(self._metrics, metric_name, False)
                    self._metrics.reconnect_count += 1
                remember_backend_error(self._last_errors, f"{channel}-ws: {normalized.error_type}: {normalized.message}")
                self._log("WARN", f"{channel} WebSocket 断开：{normalized.error_type}: {normalized.message}")
                self._stop.wait(reconnect_delay_s)
                reconnect_delay_s = min(MAX_WS_RECONNECT_DELAY_S, reconnect_delay_s * 2.0)

    def _emit_snapshot_item(self, item: dict[str, Any]) -> None:
        topic = str(item.get("topic", ""))
        if not topic:
            return
        env = TelemetryEnvelope(topic=topic, data=dict(item.get("data", {})), ts_ns=int(item.get("ts_ns", now_ns()) or now_ns()))
        self._projection_cache.update_partition(f"topic:{topic}", {"topic": topic, "data": env.data, "ts_ns": env.ts_ns})
        self.telemetry_received.emit(env)

    def _capture_reply_contracts(self, reply: ReplyEnvelope) -> None:
        authoritative_envelope = self._authoritative_service.normalize_payload(
            reply.data,
            authority_source="api_bridge",
            desired_runtime_config=self.config,
            fallback_control_authority=self._control_authority_cache,
        )
        verdict = dict(authoritative_envelope.get("final_verdict", {}))
        if verdict:
            with self._lock:
                self._last_final_verdict = verdict
        if authoritative_envelope:
            with self._lock:
                self._authoritative_envelope = authoritative_envelope
                self._control_authority_cache = dict(authoritative_envelope.get("control_authority", {}))
            self._projection_cache.update_partition("authoritative_runtime_envelope", authoritative_envelope)
            self._projection_cache.update_partition("control_authority", authoritative_envelope.get("control_authority", {}))

    def _ensure_control_lease(self, *, force: bool = False) -> None:
        """Acquire or refresh the API-side control lease."""
        if self._lease_id and not force:
            return
        try:
            response = self._client.post(
                "/api/v1/control-lease/acquire",
                json={
                    "actor_id": self._actor_id,
                    "role": self._role,
                    "workspace": self._workspace,
                    "intent_reason": "desktop_control_plane",
                    "source": "api_bridge_backend",
                },
                headers=build_command_headers(intent="acquire-control-lease", actor_id=self._actor_id, workspace=self._workspace, role=self._role, include_lease=False),
            )
            response.raise_for_status()
            body = response.json() if response.content else {}
            lease = dict(body.get("lease", {}))
            authoritative = self._authoritative_service.build(
                authority_source="api_bridge",
                control_authority=body,
                runtime_config_applied=self._runtime_config_cache,
                desired_runtime_config=self.config,
                final_verdict=self._last_final_verdict,
                detail="headless API control lease snapshot",
            )
            with self._lock:
                self._control_authority_cache = dict(authoritative.get("control_authority", {}))
                self._authoritative_envelope = authoritative
                self._lease_id = str(lease.get("lease_id", "") or self._lease_id)
            self._projection_cache.update_partition("control_authority", authoritative.get("control_authority", {}))
            self._projection_cache.update_partition("authoritative_runtime_envelope", authoritative)
        except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
            normalized = normalize_backend_exception(exc, context="control-lease")
            remember_backend_error(self._last_errors, f"control-lease: {normalized.error_type}: {normalized.message}")
            self._log("WARN", f"控制权租约获取失败：{normalized.error_type}: {normalized.message}")

    def _log(self, level: str, message: str) -> None:
        try:
            self.log_generated.emit(level, f"[{now_text()}] {message}")
        except RuntimeError:
            pass

