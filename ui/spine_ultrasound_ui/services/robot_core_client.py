from __future__ import annotations

import socket
import ssl
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils import ensure_dir, now_text

from .backend_authoritative_contract_service import BackendAuthoritativeContractService
from .backend_base import BackendBase
from .backend_control_plane_service import BackendControlPlaneService
from .backend_error_mapper import BackendErrorMapper
from .backend_errors import normalize_backend_exception
from .backend_projection_cache import BackendProjectionCache
from .core_transport import parse_telemetry_payload, send_tls_command
from .ipc_protocol import ReplyEnvelope
from .protobuf_transport import DEFAULT_TLS_SERVER_NAME, create_client_ssl_context, recv_length_prefixed_message
from .runtime_command_catalog import is_plan_compile_command, is_write_command
from .scan_plan_contract import runtime_scan_plan_payload


RECENT_COMMAND_LIMIT = 12
RECENT_TOPIC_LIMIT = 128
INITIAL_RECONNECT_DELAY_S = 0.25
MAX_RECONNECT_DELAY_S = 2.0


class RobotCoreClientBackend(QObject, BackendBase):
    """Desktop backend for the direct ``cpp_robot_core`` transport.

    The backend keeps the external public surface stable while normalizing all
    runtime-owned facts through ``BackendAuthoritativeContractService`` and
    tracking partition revisions via ``BackendProjectionCache``.
    """

    telemetry_received = Signal(object)
    log_generated = Signal(str, str)

    def __init__(
        self,
        root_dir: Path,
        command_host: str = "127.0.0.1",
        command_port: int = 5656,
        telemetry_host: str = "127.0.0.1",
        telemetry_port: int = 5657,
    ) -> None:
        """Initialize the direct core backend.

        Args:
            root_dir: Workspace root used for local runtime files.
            command_host: robot_core command host.
            command_port: robot_core command port.
            telemetry_host: robot_core telemetry host.
            telemetry_port: robot_core telemetry port.
        """
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.command_host = command_host
        self.command_port = command_port
        self.telemetry_host = telemetry_host
        self.telemetry_port = telemetry_port
        self.config = RuntimeConfig()
        self._telemetry_thread: Optional[threading.Thread] = None
        self._telemetry_stop = threading.Event()
        self._ssl_context = create_client_ssl_context()
        self._control_plane_service = BackendControlPlaneService()
        self._authoritative_service = BackendAuthoritativeContractService()
        self._projection_cache = BackendProjectionCache()
        self._recent_commands: deque[dict[str, Any]] = deque(maxlen=RECENT_COMMAND_LIMIT)
        self._latest_topics: set[str] = set()
        self._latest_topic_order: deque[str] = deque(maxlen=RECENT_TOPIC_LIMIT)
        self._latest_telemetry_ns = 0
        self._telemetry_connected = False
        self._reconnect_count = 0
        self._lock = threading.Lock()
        self._control_plane_cache: dict[str, Any] = {}
        self._authoritative_envelope: dict[str, Any] = {}
        self._last_final_verdict: dict[str, Any] = {}

    def start(self) -> None:
        """Start the telemetry loop and prime authoritative runtime facts."""
        self._start_telemetry_loop()
        self._refresh_authoritative_runtime_snapshot(reason="startup")
        self._log(
            "INFO",
            f"RobotCoreClientBackend 已启动，命令通道 {self.command_host}:{self.command_port} (TLS/Protobuf)，遥测通道 {self.telemetry_host}:{self.telemetry_port} (TLS/Protobuf)",
        )

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        """Update desired runtime config cached on the desktop side."""
        self.config = config
        self._projection_cache.update_partition("desired_runtime_config", self.config.to_dict())
        self._log("INFO", "运行时配置已同步到 AppController。")

    def send_command(self, command: str, payload: Optional[dict] = None, *, context: Optional[dict] = None) -> ReplyEnvelope:
        """Send a TLS/Protobuf command to ``cpp_robot_core``.

        Args:
            command: Runtime command name.
            payload: JSON-serializable command payload.
            context: Optional command context forwarded under ``_command_context``.

        Returns:
            Reply envelope. Transport failures are mapped to compatibility reply
            envelopes instead of raising through the historical surface.
        """
        try:
            request_payload = dict(payload or {})
            if context:
                request_payload.setdefault("_command_context", dict(context))
            reply = send_tls_command(self.command_host, self.command_port, self._ssl_context, command, request_payload)
            self._remember_recent_command(command, reply)
            self._capture_reply_contracts(reply)
            if command != "get_authoritative_runtime_envelope" and (is_write_command(command) or is_plan_compile_command(command)):
                self._refresh_authoritative_runtime_snapshot(reason=command)
            self._log("INFO", f"{command}: {reply.message or ('OK' if reply.ok else 'FAILED')}")
            return reply
        except (OSError, TimeoutError, ConnectionError, ValueError, TypeError, RuntimeError, ssl.SSLError) as exc:
            normalized = normalize_backend_exception(exc, command=command, context="robot-core-command")
            failed = BackendErrorMapper.reply_from_exception(normalized, data={"command": command}, command=command, context="robot-core-command")
            self._remember_recent_command(command, failed)
            self._log("ERROR", f"{command}: {normalized.error_type}: {normalized.message}")
            return failed

    def resolve_final_verdict(self, plan=None, config: RuntimeConfig | None = None, *, read_only: bool) -> dict[str, Any]:
        """Resolve the authoritative final verdict through the canonical backend API."""
        if read_only:
            reply = self.send_command("query_final_verdict", {})
            verdict = self._authoritative_service.extract_final_verdict(reply.data)
            if verdict:
                return verdict
            with self._lock:
                cached = dict(self._last_final_verdict)
                envelope = dict(self._authoritative_envelope)
                control_plane = dict(self._control_plane_cache)
            return cached or self._authoritative_service.extract_final_verdict(envelope) or self._authoritative_service.extract_final_verdict(control_plane)

        compile_payload = {
            "scan_plan": runtime_scan_plan_payload(plan),
            "config_snapshot": config.to_dict() if config is not None else self.config.to_dict(),
        }
        reply = self.send_command("validate_scan_plan", compile_payload)
        verdict = self._authoritative_service.extract_final_verdict(reply.data)
        if verdict:
            return verdict
        return self.resolve_final_verdict(read_only=True)

    def query_final_verdict_snapshot(self) -> dict[str, Any]:
        """Compatibility wrapper for the read-only final-verdict snapshot API."""
        return self.resolve_final_verdict(read_only=True)

    def compile_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict[str, Any]:
        """Compatibility wrapper for compile-time final-verdict resolution."""
        return self.resolve_final_verdict(plan, config, read_only=False)

    def get_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict[str, Any]:
        return self.compile_final_verdict(plan, config)

    def close(self) -> None:
        """Stop the telemetry loop and join the background thread."""
        self._telemetry_stop.set()
        thread = self._telemetry_thread
        if thread and thread.is_alive():
            thread.join(timeout=1.5)

    def link_snapshot(self) -> dict[str, Any]:
        """Build the normalized backend link snapshot.

        Returns:
            Backend link snapshot with a runtime-owned authoritative envelope and
            partition metadata.
        """
        telemetry_age_ms = None
        if self._latest_telemetry_ns:
            telemetry_age_ms = max(0, int((time.time_ns() - self._latest_telemetry_ns) / 1_000_000))
        if not self._authoritative_envelope:
            self._refresh_authoritative_runtime_snapshot(reason="link_snapshot")
        with self._lock:
            authoritative = dict(self._authoritative_envelope)
            last_final_verdict = dict(self._last_final_verdict)
        if last_final_verdict and not authoritative.get("final_verdict"):
            authoritative["final_verdict"] = last_final_verdict
        applied_runtime_config = dict(authoritative.get("runtime_config_applied", {}))
        runtime_config_payload: dict[str, Any]
        if applied_runtime_config:
            runtime_config_payload = {"runtime_config": applied_runtime_config}
        else:
            runtime_config_payload = {
                "runtime_config": {},
                "summary_state": "degraded",
                "summary_label": "运行时已应用配置缺失",
                "detail": "robot_core 尚未返回 authoritative runtime_config_applied；禁止回填本地 desired config 伪装为 applied config。",
            }
        projection_snapshot = self._projection_cache.snapshot()
        control_plane = self._control_plane_service.build(
            local_config=self.config,
            runtime_config=runtime_config_payload,
            schema={"protocol_version": int(authoritative.get("protocol_version", 1))},
            status={
                "protocol_version": int(authoritative.get("protocol_version", 1)),
                "backend_mode": "core",
                "command_endpoint": f"{self.command_host}:{self.command_port}",
                "telemetry_endpoint": f"{self.telemetry_host}:{self.telemetry_port}",
                "projection_revision": projection_snapshot["revision"],
            },
            health={
                "protocol_version": int(authoritative.get("protocol_version", 1)),
                "adapter_running": True,
                "telemetry_stale": telemetry_age_ms is None or telemetry_age_ms > 500,
                "latest_telemetry_age_ms": telemetry_age_ms,
            },
            topic_catalog={"topics": [{"name": item} for item in sorted(self._latest_topics)]},
            recent_commands=list(self._recent_commands),
            control_authority=authoritative.get("control_authority", {}),
        )
        control_plane["authoritative_runtime_envelope"] = authoritative
        control_plane["runtime_config_applied"] = dict(applied_runtime_config)
        control_plane["final_verdict"] = dict(authoritative.get("final_verdict", {}))
        control_plane["session_freeze"] = dict(authoritative.get("session_freeze", {}))
        control_plane["plan_digest"] = dict(authoritative.get("plan_digest", {}))
        if authoritative.get("final_verdict"):
            control_plane["control_plane_snapshot"] = {
                **dict(control_plane.get("control_plane_snapshot", {})),
                "model_precheck": dict(authoritative["final_verdict"]),
            }
        blockers = []
        if not self._telemetry_connected:
            blockers.append({"name": "robot_core 遥测未连通", "detail": "尚未收到 TLS/Protobuf 遥测。"})
        blockers.extend(control_plane.get("blockers", []))
        warnings = list(control_plane.get("warnings", []))
        summary_state = "blocked" if blockers else ("degraded" if warnings else "ready")
        with self._lock:
            self._control_plane_cache = dict(control_plane)
        self._projection_cache.update_partition("control_plane", control_plane)
        return {
            "mode": "core",
            "summary_state": summary_state,
            "summary_label": "robot_core 直连" if summary_state == "ready" else ("robot_core 直连阻塞" if summary_state == "blocked" else "robot_core 直连降级"),
            "detail": f"TLS/Protobuf command={self.command_host}:{self.command_port} telemetry={self.telemetry_host}:{self.telemetry_port}",
            "command_success_rate": int(round((sum(1 for item in self._recent_commands if item.get("ok")) / len(self._recent_commands)) * 100)) if self._recent_commands else 100,
            "telemetry_connected": self._telemetry_connected,
            "camera_connected": False,
            "ultrasound_connected": False,
            "rest_reachable": True,
            "using_websocket_telemetry": False,
            "using_websocket_media": False,
            "http_base": f"tls://{self.command_host}:{self.command_port}",
            "ws_base": f"tls://{self.telemetry_host}:{self.telemetry_port}",
            "blockers": blockers,
            "warnings": warnings,
            "reconnect_count": self._reconnect_count,
            "control_plane": control_plane,
            "projection_revision": projection_snapshot["revision"],
            "projection_partitions": projection_snapshot["partitions"],
        }

    def _start_telemetry_loop(self) -> None:
        if self._telemetry_thread and self._telemetry_thread.is_alive():
            return
        self._telemetry_stop.clear()
        self._telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self._telemetry_thread.start()

    def _telemetry_loop(self) -> None:
        reconnect_delay_s = INITIAL_RECONNECT_DELAY_S
        while not self._telemetry_stop.is_set():
            try:
                with socket.create_connection((self.telemetry_host, self.telemetry_port), timeout=1.0) as raw_sock:
                    raw_sock.settimeout(2.0)
                    raw_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    with self._ssl_context.wrap_socket(raw_sock, server_hostname=DEFAULT_TLS_SERVER_NAME) as tls_sock:
                        self._telemetry_connected = True
                        reconnect_delay_s = INITIAL_RECONNECT_DELAY_S
                        self._log("INFO", "已连接 robot_core 遥测通道。")
                        while not self._telemetry_stop.is_set():
                            env = parse_telemetry_payload(recv_length_prefixed_message(tls_sock))
                            self._remember_topic(env.topic)
                            self._latest_telemetry_ns = int(getattr(env, "ts_ns", 0) or 0)
                            self._projection_cache.update_partition(f"topic:{env.topic}", {"topic": env.topic, "ts_ns": self._latest_telemetry_ns})
                            self.telemetry_received.emit(env)
            except (OSError, TimeoutError, ConnectionError, ssl.SSLError) as exc:
                normalized = normalize_backend_exception(exc, context="telemetry-loop")
                self._telemetry_connected = False
                self._reconnect_count += 1
                if self._telemetry_stop.is_set():
                    break
                self._log("WARN", f"遥测通道异常：{normalized.error_type}: {normalized.message}")
                time.sleep(reconnect_delay_s)
                reconnect_delay_s = min(MAX_RECONNECT_DELAY_S, reconnect_delay_s * 2.0)
            except (ValueError, TypeError, RuntimeError) as exc:
                normalized = normalize_backend_exception(exc, context="telemetry-loop")
                self._telemetry_connected = False
                self._reconnect_count += 1
                if self._telemetry_stop.is_set():
                    break
                self._log("WARN", f"遥测帧解析异常：{normalized.error_type}: {normalized.message}")
                time.sleep(reconnect_delay_s)
                reconnect_delay_s = min(MAX_RECONNECT_DELAY_S, reconnect_delay_s * 2.0)

    def _remember_recent_command(self, command: str, reply: ReplyEnvelope) -> None:
        entry = {"command": command, "ok": bool(reply.ok), "message": str(reply.message)}
        self._recent_commands.append(entry)
        self._projection_cache.update_partition("recent_commands", list(self._recent_commands))

    def _remember_topic(self, topic: str) -> None:
        topic_name = str(topic).strip()
        if not topic_name or topic_name in self._latest_topics:
            return
        if len(self._latest_topic_order) >= RECENT_TOPIC_LIMIT and self._latest_topic_order:
            expired = self._latest_topic_order.popleft()
            self._latest_topics.discard(expired)
        self._latest_topic_order.append(topic_name)
        self._latest_topics.add(topic_name)
        self._projection_cache.update_partition("topic_catalog", {"topics": [{"name": item} for item in sorted(self._latest_topics)]})

    def _capture_reply_contracts(self, reply: ReplyEnvelope) -> None:
        verdict = self._authoritative_service.extract_final_verdict(reply.data)
        if verdict:
            with self._lock:
                self._last_final_verdict = verdict
            self._projection_cache.update_partition("final_verdict", verdict)
        envelope = self._authoritative_service.normalize_payload(
            reply.data,
            authority_source="cpp_robot_core",
            desired_runtime_config=self.config,
        )
        if envelope.get("control_authority") or envelope.get("runtime_config_applied"):
            with self._lock:
                self._authoritative_envelope = envelope
            self._projection_cache.update_partition("authoritative_runtime_envelope", envelope)

    def _refresh_authoritative_runtime_snapshot(self, *, reason: str) -> None:
        try:
            reply = send_tls_command(
                self.command_host,
                self.command_port,
                self._ssl_context,
                "get_authoritative_runtime_envelope",
                {"reason": reason},
            )
        except (OSError, TimeoutError, ConnectionError, ssl.SSLError, ValueError, TypeError, RuntimeError) as exc:
            normalized = normalize_backend_exception(exc, context="authoritative-refresh")
            self._log("WARN", f"权威快照刷新失败：{normalized.error_type}: {normalized.message}")
            return
        self._remember_recent_command("get_authoritative_runtime_envelope", reply)
        envelope = self._authoritative_service.normalize_payload(
            reply.data,
            authority_source="cpp_robot_core",
            desired_runtime_config=self.config,
            fallback_control_authority={
                "summary_state": "degraded",
                "summary_label": "直接核心运行时权威快照缺少控制权细节",
                "detail": "fallback authority metadata used until runtime publishes a full control-authority payload",
                "owner": {"actor_id": "core-runtime", "workspace": "core", "role": "runtime", "session_id": ""},
                "owner_provenance": {"source": "cpp_robot_core", "reason": "direct_core_single_source_fallback"},
            },
        )
        with self._lock:
            self._authoritative_envelope = envelope
            verdict = self._authoritative_service.extract_final_verdict(envelope)
            if verdict:
                self._last_final_verdict = verdict
        self._projection_cache.update_partition("authoritative_runtime_envelope", envelope)
        if envelope.get("final_verdict"):
            self._projection_cache.update_partition("final_verdict", envelope["final_verdict"])

    def _log(self, level: str, message: str) -> None:
        try:
            self.log_generated.emit(level, f"[{now_text()}] {message}")
        except RuntimeError:
            pass
