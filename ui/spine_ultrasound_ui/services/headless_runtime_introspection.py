from __future__ import annotations

from typing import Any, Protocol

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.ipc_protocol import PROTOCOL_VERSION, protocol_schema


class HeadlessRuntimeHost(Protocol):
    mode: str
    command_host: str
    command_port: int
    telemetry_host: str
    telemetry_port: int
    _thread: Any
    read_only_mode: bool
    telemetry_cache: Any
    role_matrix: Any
    topic_registry: Any
    command_policy_service: Any
    control_authority: Any
    deployment_profile_service: Any
    runtime_config_snapshot_data: dict[str, Any]

    def _read_manifest_if_available(self) -> dict[str, Any]: ...
    def _resolve_session_dir(self) -> Any: ...
    def _derive_recovery_state(self, core: dict[str, Any]) -> str: ...


class HeadlessRuntimeIntrospection:
    def __init__(self, host: HeadlessRuntimeHost):
        self.host = host

    def status(self) -> dict[str, Any]:
        state = self.host.telemetry_cache.status_slice()
        core = state["core"]
        robot = state["robot"]
        safety = state["safety"]
        manifest = self.host._read_manifest_if_available()
        return {
            "backend_mode": self.host.mode,
            "command_endpoint": f"{self.host.command_host}:{self.host.command_port}",
            "telemetry_endpoint": f"{self.host.telemetry_host}:{self.host.telemetry_port}",
            "execution_state": core.get("execution_state", "BOOT"),
            "powered": robot.get("powered", False),
            "safe_to_scan": safety.get("safe_to_scan", False),
            "protocol_version": PROTOCOL_VERSION,
            "session_id": core.get("session_id", getattr(self.host, "_current_session_id", "")),
            "session_locked": bool(self.host._resolve_session_dir()),
            "force_sensor_provider": manifest.get("force_sensor_provider", ""),
            "robot_model": manifest.get("robot_profile", {}).get("robot_model", ""),
            "software_version": manifest.get("software_version", ""),
            "build_id": manifest.get("build_id", ""),
            "topics": state["topics"],
            "read_only_mode": self.host.read_only_mode,
            "control_authority": self.host.control_authority.snapshot(),
            "deployment_profile": self.host.deployment_profile_service.build_snapshot(RuntimeConfig.from_dict(self.host.runtime_config_snapshot_data or {})),
        }

    def health(self) -> dict[str, Any]:
        state = self.host.telemetry_cache.health_slice()
        manifest = self.host._read_manifest_if_available()
        core = state["core"]
        robot = state["robot"]
        return {
            "backend_mode": self.host.mode,
            "adapter_running": self.host._thread is not None and self.host._thread.is_alive(),
            "protocol_version": PROTOCOL_VERSION,
            "topics": state["topics"],
            "latest_telemetry_age_ms": state["latest_telemetry_age_ms"],
            "telemetry_stale": state["telemetry_stale"],
            "stale_threshold_ms": state["stale_threshold_ms"],
            "recovery_state": self.host._derive_recovery_state(core),
            "force_sensor_provider": manifest.get("force_sensor_provider", ""),
            "robot_model": manifest.get("robot_profile", {}).get("robot_model", ""),
            "session_locked": bool(self.host._resolve_session_dir()),
            "build_id": manifest.get("build_id", ""),
            "software_version": manifest.get("software_version", ""),
            "execution_state": core.get("execution_state", "BOOT"),
            "powered": robot.get("powered", False),
            "read_only_mode": self.host.read_only_mode,
            "control_authority": self.host.control_authority.snapshot(),
        }

    def schema(self) -> dict[str, Any]:
        payload = protocol_schema()
        payload["topic_catalog"] = self.topic_catalog()
        payload["control_authority"] = {
            "strict_mode": self.host.control_authority.strict_mode,
            "auto_issue_implicit_lease": self.host.control_authority.auto_issue_implicit_lease,
            "default_ttl_s": self.host.control_authority.lease_ttl_s,
        }
        return payload

    def topic_catalog(self) -> dict[str, Any]:
        return self.host.topic_registry.catalog()

    def role_catalog(self) -> dict[str, Any]:
        return self.host.role_matrix.catalog()

    def command_policy_catalog(self) -> dict[str, Any]:
        return self.host.command_policy_service.catalog()

    def control_authority_status(self) -> dict[str, Any]:
        return self.host.control_authority.snapshot()
