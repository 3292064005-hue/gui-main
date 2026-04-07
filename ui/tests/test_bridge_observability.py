from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.core.telemetry_store import TelemetryStore
from spine_ultrasound_ui.core.view_state_factory import ViewStateFactory
from spine_ultrasound_ui.models import RuntimeConfig, WorkflowArtifacts
from spine_ultrasound_ui.services.bridge_observability_service import BridgeObservabilityService
from spine_ultrasound_ui.services.ipc_protocol import TelemetryEnvelope
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.utils import now_ns


def _apply_topic(store: TelemetryStore, topic: str, data: dict, *, age_ms: int = 0) -> None:
    store.apply(TelemetryEnvelope(topic=topic, data=data, ts_ns=now_ns() - age_ms * 1_000_000))


def _base_store() -> TelemetryStore:
    store = TelemetryStore()
    _apply_topic(store, "core_state", {"execution_state": "AUTO_READY", "session_id": "S1"}, age_ms=10)
    _apply_topic(store, "robot_state", {"powered": True, "operate_mode": "automatic"}, age_ms=15)
    _apply_topic(store, "safety_status", {"safe_to_scan": True, "safe_to_arm": True, "active_interlocks": []}, age_ms=12)
    _apply_topic(store, "contact_state", {"mode": "NO_CONTACT", "confidence": 0.8, "pressure_current": 7.8, "recommended_action": "IDLE"}, age_ms=30)
    _apply_topic(store, "scan_progress", {"active_segment": 0, "overall_progress": 0.0, "frame_id": 0}, age_ms=25)
    return store


def test_bridge_observability_blocks_on_stale_required_topic() -> None:
    store = _base_store()
    # Make core_state stale enough to violate the contract.
    _apply_topic(store, "core_state", {"execution_state": "AUTO_READY", "session_id": "S1"}, age_ms=2500)
    service = BridgeObservabilityService()
    result = service.build(store, {"control_plane": {"command_window": {"recent_commands": []}}}, WorkflowArtifacts())
    assert result["summary_state"] == "blocked"
    blocker_names = {item["name"] for item in result["blockers"]}
    assert "core_state 数据陈旧" in blocker_names


def test_bridge_observability_blocks_when_command_not_observed() -> None:
    store = _base_store()
    service = BridgeObservabilityService()
    result = service.build(
        store,
        {"control_plane": {"command_window": {"recent_commands": [{"command": "start_scan", "ok": True, "message": "started"}]}}},
        WorkflowArtifacts(session_locked=True),
    )
    assert result["summary_state"] == "blocked"
    assert result["command_observability"]["latest_checked_command"] == "start_scan"
    assert result["command_observability"]["summary_label"] == "命令确认缺失"


def test_view_state_factory_includes_bridge_observability_gate() -> None:
    backend = MockBackend(Path("/tmp/mock-runtime-bridge"))
    controller_store = _base_store()
    payload = ViewStateFactory().build(
        controller_store,
        RuntimeConfig(),
        WorkflowArtifacts(),
        None,
        backend_link={"summary_state": "ready", "detail": "ok", "control_plane": {"config_sync": {"summary_state": "ready", "detail": "ok"}, "protocol_status": {"summary_state": "ready", "detail": "ok"}}},
        bridge_observability={"summary_state": "blocked", "detail": "core_state stale"},
    ).to_dict()
    names = [item["name"] for item in payload["readiness"]["checks"]]
    assert "桥接观测契约正常" in names
    bridge_check = next(item for item in payload["readiness"]["checks"] if item["name"] == "桥接观测契约正常")
    assert bridge_check["ready"] is False
