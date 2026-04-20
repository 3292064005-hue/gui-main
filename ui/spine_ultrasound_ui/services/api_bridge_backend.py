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
from .api_bridge_lease_service import ApiBridgeLeaseService
from .api_bridge_verdict_service import ApiBridgeVerdictService
from .backend_authoritative_contract_service import BackendAuthoritativeContractService
from .backend_command_error_service import BackendCommandErrorService
from .backend_error_mapper import BackendErrorMapper  # explicit authority edge for backend error normalization
from .backend_base import BackendBase
from .backend_capability_matrix_service import BackendCapabilityMatrixService
from .backend_control_plane_projection_service import BackendControlPlaneProjectionService
from .backend_control_plane_service import BackendControlPlaneService
from .backend_errors import BackendOperationError, normalize_backend_exception
from .backend_link_service import BackendLinkMetrics, BackendLinkService
from .backend_projection_cache import BackendProjectionCache
from .ipc_protocol import ReplyEnvelope, TelemetryEnvelope

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
        deployment_profile: str = "dev",
    ) -> None:
        """Create the API bridge backend.

        Args:
            root_dir: Runtime working directory for persisted local artifacts.
            base_url: Base HTTP URL for the headless adapter.
            request_timeout_s: Per-request timeout in seconds.
            health_poll_interval_s: Poll period for status/health/control-plane.
            snapshot_poll_interval_s: Poll period for REST telemetry fallback.
            deployment_profile: Deployment profile name used to suppress lease
                mutations for read-only review desktops.
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
        self._projection_service = BackendControlPlaneProjectionService()
        self._authoritative_service = BackendAuthoritativeContractService()
        self._projection_cache = BackendProjectionCache()
        self._metrics = BackendLinkMetrics(using_websocket_telemetry=ws_connect is not None, using_websocket_media=ws_connect is not None)
        self._deployment_profile = str(deployment_profile or "dev").strip().lower()
        self._actor_id = os.getenv("SPINE_ACTOR_ID", f"desktop-{socket.gethostname()}")
        self._workspace = os.getenv("SPINE_WORKSPACE", "desktop")
        self._role = os.getenv("SPINE_ROLE", "operator")
        self._lease_id = ""
        self._lease_service = ApiBridgeLeaseService(self)
        self._verdict_service = ApiBridgeVerdictService(self)

    def _lease_allowed(self) -> bool:
        """Return whether the backend may mutate control-lease state.

        Review desktops are read-only surfaces and must not acquire/refresh a
        control lease as a side effect of startup or verdict queries.
        """
        return self._deployment_profile != "review"

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
        if self._lease_allowed():
            self._lease_service.ensure_control_lease()
        else:
            self._log("INFO", "review profile active: skip API-side control lease acquisition.")
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
            A normalized reply envelope. Transport/HTTP errors are normalized
            through the canonical backend command error service.
        """
        request_payload = dict(payload or {})
        command_context = dict(context or {})
        include_lease = bool(command_context.get("include_lease", True))
        effective_include_lease = include_lease and self._lease_allowed()
        started_ns = now_ns()
        with self._lock:
            self._metrics.commands_sent += 1
            self._metrics.last_command = command
        if effective_include_lease:
            self._lease_service.ensure_control_lease(force=bool(command_context.get("force_lease_refresh")))
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
                    lease_id=self._lease_id,
                    include_lease=effective_include_lease,
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
                _, failed = BackendCommandErrorService.build_reply(RuntimeError(message), command=command, context="api-command", data={"http_status": response.status_code, "command": command})
                return failed
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
                if effective_include_lease and ("控制权" in reply.message or "lease" in reply.message.lower()):
                    self._lease_service.ensure_control_lease(force=True)
                remember_backend_error(self._last_errors, f"{command}: {reply.message}")
            self._log("INFO" if reply.ok else "WARN", f"API {command}: {reply.message or ('OK' if reply.ok else 'FAILED')}")
            return reply
        except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
            normalized, failed = BackendCommandErrorService.build_reply(exc, command=command, context="api-command", data={"command": command})
            with self._lock:
                self._metrics.commands_failed += 1
                self._metrics.last_error = normalized.message
            remember_backend_error(self._last_errors, f"{command}: {normalized.error_type}: {normalized.message}")
            self._log("ERROR", f"API {command} 失败：{normalized.error_type}: {normalized.message}")
            return failed
    def capability_matrix(self) -> dict[str, dict[str, Any]]:
        """Return the explicit capability contract for the API bridge surface."""
        return BackendCapabilityMatrixService.build({
            "camera": "monitor_only",
            "ultrasound": "monitor_only",
            "reconstruction": "monitor_only",
            "recording": "monitor_only",
        })

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
            control_authority = dict(self._control_authority_cache)
        control_plane = self._projection_service.build(
            control_plane=control_plane,
            authoritative_envelope=authoritative_envelope,
            projection_cache=self._projection_cache,
            control_authority=control_authority,
        )
        snapshot = self.link_service.build_snapshot(
            mode="api",
            http_base=self.base_url,
            ws_base=self.ws_base,
            status=status,
            health=health,
            metrics=metrics,
            extra_errors=errors,
            control_plane=control_plane,
            local_runtime_config=self.config.to_dict(),
            authoritative_runtime_envelope=authoritative_envelope,
        )
        snapshot["media_capabilities"] = self.media_capabilities()
        snapshot["capability_matrix"] = self.capability_matrix()
        return snapshot
    def resolve_authoritative_runtime_envelope(self) -> dict[str, Any]:
        """Return the canonical runtime-owned authoritative envelope for read consumers."""
        with self._lock:
            envelope = dict(self._authoritative_envelope)
        if envelope:
            return envelope
        return self._authoritative_service.build_unavailable_authoritative_runtime_envelope(
            authority_source="api_bridge",
            detail="api bridge has not received a runtime-published authoritative envelope",
            desired_runtime_config=self.config,
            envelope_origin="api_bridge_cache_empty",
        )

    def resolve_control_authority(self) -> dict[str, Any]:
        """Return the canonical control-authority snapshot for read consumers."""
        return dict(self.resolve_authoritative_runtime_envelope().get("control_authority", {}))
    def acquire_control_lease(self, *, force: bool = False) -> dict[str, Any]:
        """Acquire a runtime-owned control lease through the API bridge."""
        return dict(self._lease_service.acquire_control_lease(force=force))
    def renew_control_lease(self, *, ttl_s: int | None = None) -> dict[str, Any]:
        """Renew the currently cached runtime-owned control lease."""
        return dict(self._lease_service.renew_control_lease(ttl_s=ttl_s))
    def release_control_lease(self, *, reason: str = "") -> dict[str, Any]:
        """Release the currently cached runtime-owned control lease."""
        return dict(self._lease_service.release_control_lease(reason=reason))
    def resolve_final_verdict(self, plan=None, config: RuntimeConfig | None = None, *, read_only: bool) -> dict[str, Any]:
        """Resolve the authoritative runtime final verdict through the canonical backend API."""
        return self._verdict_service.resolve_final_verdict(plan, config, read_only=read_only)
    def query_final_verdict_snapshot(self) -> dict[str, Any]:
        """Compatibility wrapper for the read-only final-verdict snapshot API."""
        return self.resolve_final_verdict(read_only=True)
    def compile_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict[str, Any]:
        """Compatibility wrapper for compile-time final-verdict resolution."""
        return self.resolve_final_verdict(plan, config, read_only=False)
    def get_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict[str, Any]:
        return self.compile_final_verdict(plan, config)
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
                envelope_resp = self._client.get("/api/v1/authoritative-runtime-envelope")
                envelope_resp.raise_for_status()
                status = status_resp.json()
                health = health_resp.json()
                control_plane = control_resp.json()
                authoritative_envelope = self._authoritative_service.normalize_authoritative_runtime_envelope(
                    envelope_resp.json() if envelope_resp.content else {},
                    authority_source="api_bridge",
                    desired_runtime_config=self.config,
                    allow_direct_payload=True,
                )
                if not authoritative_envelope:
                    authoritative_envelope = self._authoritative_service.build_unavailable_authoritative_runtime_envelope(
                        authority_source="api_bridge",
                        detail="headless API did not return a runtime-published authoritative envelope",
                        desired_runtime_config=self.config,
                        envelope_origin="api_bridge_health_loop_missing_envelope",
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
        authoritative_envelope = self._authoritative_service.normalize_authoritative_runtime_envelope(
            reply.data,
            authority_source="api_bridge",
            desired_runtime_config=self.config,
            allow_direct_payload=True,
        )
        verdict = self._authoritative_service.extract_final_verdict(reply.data)
        if not verdict:
            verdict = dict(authoritative_envelope.get("final_verdict", {}))
        if verdict:
            with self._lock:
                self._last_final_verdict = dict(verdict)
        if authoritative_envelope:
            with self._lock:
                self._authoritative_envelope = authoritative_envelope
                self._control_authority_cache = dict(authoritative_envelope.get("control_authority", {}))
            self._projection_cache.update_partition("authoritative_runtime_envelope", authoritative_envelope)
            self._projection_cache.update_partition("control_authority", authoritative_envelope.get("control_authority", {}))
    def _log(self, level: str, message: str) -> None:
        try:
            self.log_generated.emit(level, f"[{now_text()}] {message}")
        except RuntimeError:
            pass

