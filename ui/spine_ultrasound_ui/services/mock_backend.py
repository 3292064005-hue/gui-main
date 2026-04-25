from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils import ensure_dir, generate_demo_pixmap

from .backend_authoritative_contract_service import BackendAuthoritativeContractService
from .backend_base import BackendBase
from .backend_control_plane_service import BackendControlPlaneService
from .backend_projection_cache import BackendProjectionCache
from .ipc_protocol import ReplyEnvelope, TelemetryEnvelope, is_write_command
from .mock_core_runtime import MockCoreRuntime
from .scan_plan_contract import runtime_scan_plan_payload


class MockBackend(QObject, BackendBase):
    """In-process mock backend.

    Public behavior remains compatible with the legacy mock backend while the
    control-plane and final-verdict surfaces now consume the same authoritative
    envelope normalizer used by the real backends.
    """

    telemetry_received = Signal(object)
    log_generated = Signal(str, str)
    camera_pixmap_ready = Signal(QPixmap)
    ultrasound_pixmap_ready = Signal(QPixmap)
    reconstruction_pixmap_ready = Signal(QPixmap)

    def __init__(self, root_dir: Path):
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.runtime = MockCoreRuntime()
        self.config = RuntimeConfig()
        self.runtime.update_runtime_config(self.config)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._control_plane_service = BackendControlPlaneService()
        self._authoritative_service = BackendAuthoritativeContractService()
        self._projection_cache = BackendProjectionCache()
        self._recent_commands: list[dict] = []
        self._authoritative_envelope: dict = self._build_authoritative_envelope()

    def start(self) -> None:
        self.timer.start(120)
        self._emit_telemetry(self.runtime.telemetry_snapshot())

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        self.config = config
        self.runtime.update_runtime_config(config)
        self._authoritative_envelope = self._build_authoritative_envelope()
        self._projection_cache.update_partition("desired_runtime_config", config.to_dict())
        self._projection_cache.update_partition("authoritative_runtime_envelope", self._authoritative_envelope)
        self._emit_telemetry(self.runtime.telemetry_snapshot())

    def send_command(self, command: str, payload: Optional[dict] = None, *, context: Optional[dict] = None) -> ReplyEnvelope:
        request_payload = dict(payload or {})
        if context:
            request_payload.setdefault("_command_context", dict(context))
        reply = self.runtime.handle_command(command, request_payload)
        self._recent_commands.append({"command": command, "ok": bool(reply.ok), "message": str(reply.message)})
        self._recent_commands = self._recent_commands[-12:]
        self.log_generated.emit("INFO" if reply.ok else "ERROR", f"[mock_core] {command}: {reply.message}")
        authoritative = self._authoritative_service.normalize_authoritative_runtime_envelope(
            reply.data,
            authority_source="mock_runtime",
            desired_runtime_config=self.config,
            allow_direct_payload=True,
        )
        if authoritative:
            self._authoritative_envelope = authoritative
            self._projection_cache.update_partition("authoritative_runtime_envelope", authoritative)
            self._projection_cache.update_partition("control_authority", authoritative.get("control_authority", {}))
        # Avoid recursive governance refresh loops during read-only asset aggregation.
        # Write commands still publish fresh telemetry immediately; read commands rely on
        # the periodic tick or explicit runtime polling.
        if is_write_command(command):
            self._emit_telemetry(self.runtime.telemetry_snapshot())
        return reply

    def link_snapshot(self) -> dict:
        topics = [{"name": item.topic} for item in self.runtime.telemetry_snapshot()]
        authoritative = self._authoritative_envelope or self._build_authoritative_envelope()
        control_plane = self._control_plane_service.build(
            local_config=self.config,
            runtime_config={"runtime_config": self.config.to_dict()},
            schema={"protocol_version": 1},
            status={"protocol_version": 1, "backend_mode": "mock", "execution_state": self.runtime.execution_state.value},
            health={"protocol_version": 1, "adapter_running": True, "telemetry_stale": False, "latest_telemetry_age_ms": 0},
            topic_catalog={"topics": topics},
            recent_commands=list(self._recent_commands),
            control_authority=dict(authoritative.get("control_authority", {})),
        )
        control_plane["authoritative_runtime_envelope"] = authoritative
        control_plane["runtime_config_applied"] = dict(authoritative.get("runtime_config_applied", {}))
        control_plane["final_verdict"] = dict(authoritative.get("final_verdict", {}))
        control_plane["session_freeze"] = dict(authoritative.get("session_freeze", {}))
        control_plane["plan_digest"] = dict(authoritative.get("plan_digest", {}))
        projection_snapshot = self._projection_cache.snapshot()
        control_plane["projection_revision"] = projection_snapshot["revision"]
        control_plane["projection_partitions"] = projection_snapshot["partitions"]
        return {
            "mode": "mock",
            "summary_state": "ready",
            "summary_label": "本地 mock 内联",
            "detail": "桌面与 mock contract-replay runtime 进程内直连。",
            "command_success_rate": 100,
            "telemetry_connected": True,
            "camera_connected": True,
            "ultrasound_connected": True,
            "rest_reachable": True,
            "using_websocket_telemetry": False,
            "using_websocket_media": False,
            "http_base": "inproc://mock",
            "ws_base": "inproc://mock",
            "blockers": [],
            "warnings": [],
            "control_plane": control_plane,
            "authoritative_runtime_envelope": authoritative,
            "control_authority": dict(authoritative.get("control_authority", {})),
            "final_verdict": dict(authoritative.get("final_verdict", {})),
            "projection_revision": projection_snapshot["revision"],
            "projection_partitions": projection_snapshot["partitions"],
        }

    def resolve_authoritative_runtime_envelope(self) -> dict[str, Any]:
        """Return the canonical authoritative runtime envelope for read consumers."""
        if not self._authoritative_envelope:
            self._authoritative_envelope = self._build_authoritative_envelope()
        return dict(self._authoritative_envelope)

    def resolve_control_authority(self) -> dict[str, Any]:
        """Return the canonical control-authority snapshot for read consumers."""
        return dict(self.resolve_authoritative_runtime_envelope().get("control_authority", {}))

    def resolve_final_verdict(self, plan=None, config: RuntimeConfig | None = None, *, read_only: bool) -> dict:
        """Resolve the authoritative final verdict through the canonical backend API."""
        if read_only:
            verdict = self._authoritative_service.extract_final_verdict(self._authoritative_envelope)
            if verdict:
                return verdict
            return dict(self.runtime.last_final_verdict or {})

        plan_payload = runtime_scan_plan_payload(plan) or {}
        config_payload = config.to_dict() if config is not None else self.config.to_dict()
        verdict = self.runtime.compile_scan_plan_verdict(plan_payload, config_payload)
        self._authoritative_envelope = self._build_authoritative_envelope(final_verdict=verdict)
        self._projection_cache.update_partition("authoritative_runtime_envelope", self._authoritative_envelope)
        return verdict

    def query_final_verdict_snapshot(self) -> dict:
        """Compatibility wrapper for the read-only final-verdict snapshot API."""
        return self.resolve_final_verdict(read_only=True)

    def compile_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict:
        """Compatibility wrapper for compile-time final-verdict resolution."""
        return self.resolve_final_verdict(plan, config, read_only=False)

    def get_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict:
        return self.compile_final_verdict(plan, config)

    def close(self) -> None:
        """Stop the mock backend and release timer-backed Qt resources."""
        if self.timer.isActive():
            self.timer.stop()
        try:
            self.timer.timeout.disconnect(self._tick)
        except (RuntimeError, TypeError):
            pass

    def _tick(self) -> None:
        self.phase += 0.12
        self._emit_telemetry(self.runtime.tick())
        if generate_demo_pixmap is None:
            return
        self.camera_pixmap_ready.emit(generate_demo_pixmap(720, 360, "camera", self.phase))
        self.ultrasound_pixmap_ready.emit(generate_demo_pixmap(720, 360, "ultrasound", self.phase))
        self.reconstruction_pixmap_ready.emit(generate_demo_pixmap(720, 360, "reconstruction", self.phase))

    def _emit_telemetry(self, messages: list[TelemetryEnvelope]) -> None:
        self._authoritative_envelope = self._build_authoritative_envelope()
        self._projection_cache.update_partition("authoritative_runtime_envelope", self._authoritative_envelope)
        for message in messages:
            if not message.ts_ns:
                message.ts_ns = uuid.uuid4().int % (10**12)
            self._projection_cache.update_partition(f"topic:{message.topic}", {"topic": message.topic, "data": message.data, "ts_ns": message.ts_ns})
            self.telemetry_received.emit(message)

    def _local_control_authority(self) -> dict:
        return {
            "summary_state": "ready",
            "summary_label": "本地控制权",
            "detail": "single backend owner",
            "owner": {"actor_id": "desktop-local", "workspace": "desktop", "role": "operator", "session_id": ""},
            "active_lease": {"lease_id": "local", "actor_id": "desktop-local", "workspace": "desktop", "role": "operator", "expires_in_s": 9999},
        }

    def _build_authoritative_envelope(self, *, final_verdict: dict | None = None) -> dict:
        payload = self.runtime.handle_command("get_authoritative_runtime_envelope", {}).data
        if final_verdict:
            payload = dict(payload)
            payload["final_verdict"] = final_verdict
        return self._authoritative_service.normalize_authoritative_runtime_envelope(
            payload,
            authority_source="mock_runtime",
            desired_runtime_config=self.config,
            allow_direct_payload=True,
        )
