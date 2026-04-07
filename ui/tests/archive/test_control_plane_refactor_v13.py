from __future__ import annotations

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.control_plane_snapshot_service import ControlPlaneSnapshotService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter


def test_deployment_profile_service_resolves_review_profile() -> None:
    service = DeploymentProfileService({"SPINE_READ_ONLY_MODE": "1"})
    snapshot = service.build_snapshot(RuntimeConfig())
    assert snapshot["name"] == "review"
    assert snapshot["review_only"] is True
    assert snapshot["allows_write_commands"] is False


def test_control_plane_snapshot_service_marks_blocked_when_authority_blocked() -> None:
    snapshot = ControlPlaneSnapshotService().build(
        backend_link={"summary_state": "ready", "summary_label": "link ok", "blockers": [], "warnings": []},
        control_authority={"summary_state": "blocked", "summary_label": "authority blocked", "blockers": [{"name": "lease_conflict", "detail": "occupied"}], "warnings": []},
        deployment_profile={"name": "clinical", "requires_strict_control_authority": True, "review_only": False},
    )
    assert snapshot["summary_state"] == "blocked"
    assert any(item["section"] == "control_authority" for item in snapshot["blockers"])


def test_headless_adapter_control_plane_status_includes_deployment_profile() -> None:
    adapter = HeadlessAdapter(mode="mock", command_host="127.0.0.1", command_port=5656, telemetry_host="127.0.0.1", telemetry_port=5657)
    control_plane = adapter.control_plane_status()
    assert control_plane["deployment_profile"]["name"] in {"dev", "research", "clinical", "review"}
    assert "unified_snapshot" in control_plane
    assert control_plane["unified_snapshot"]["summary_state"] in {"ready", "degraded", "blocked"}
