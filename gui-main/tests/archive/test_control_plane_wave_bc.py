from __future__ import annotations

from spine_ultrasound_ui.services.control_authority_service import ControlAuthorityService
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter
from spine_ultrasound_ui.services.control_plane_snapshot_service import ControlPlaneSnapshotService


def test_control_authority_service_supports_renew_and_profile_provenance() -> None:
    service = ControlAuthorityService(strict_mode=True, auto_issue_implicit_lease=False)
    acquired = service.acquire(
        actor_id="desktop-a",
        role="operator",
        workspace="desktop",
        session_id="S1",
        intent_reason="scan",
        deployment_profile="clinical",
    )
    assert acquired["ok"] is True
    lease_id = acquired["lease"]["lease_id"]
    renewed = service.renew(lease_id=lease_id, actor_id="desktop-a")
    assert renewed["ok"] is True
    snap = service.snapshot()
    assert snap["owner_provenance"]["deployment_profile"] == "clinical"
    assert snap["session_binding"] == "S1"


def test_headless_adapter_blocks_write_commands_in_review_profile() -> None:
    adapter = HeadlessAdapter(mode="mock", command_host="127.0.0.1", command_port=5656, telemetry_host="127.0.0.1", telemetry_port=5657)
    adapter.set_runtime_config({"requires_single_control_source": False})
    adapter.deployment_profile_service._env["SPINE_READ_ONLY_MODE"] = "1"
    reply = adapter.command("connect_robot", {"_command_context": {"actor_id": "reviewer", "workspace": "review", "role": "operator", "profile": "review", "intent": "inspect"}})
    assert reply["ok"] is False
    assert "只读" in reply["message"]


def test_control_plane_snapshot_exposes_canonical_sections() -> None:
    snapshot = ControlPlaneSnapshotService().build(
        backend_link={
            "summary_state": "ready",
            "summary_label": "link ok",
            "control_plane": {
                "protocol_status": {"summary_state": "ready", "summary_label": "协议一致", "detail": "v1"},
                "config_sync": {"summary_state": "ready", "summary_label": "配置一致", "detail": "match"},
                "topic_coverage": {"summary_state": "ready", "summary_label": "主题覆盖完整", "detail": "ok"},
                "command_window": {"summary_state": "ready", "summary_label": "命令窗口健康", "detail": "ok"},
                "control_authority": {"summary_state": "ready", "summary_label": "控制权已锁定", "detail": "desktop-a"},
            },
        },
        control_authority={"summary_state": "ready", "summary_label": "控制权已锁定", "detail": "desktop-a", "owner": {"actor_id": "desktop-a"}},
        deployment_profile={"name": "clinical", "requires_strict_control_authority": True, "review_only": False},
        session_governance={"summary_state": "ready", "summary_label": "会话已锁定", "detail": "ok", "session_locked": True, "session_id": "S1"},
        evidence_seal={"summary_state": "ready", "summary_label": "seal ok", "detail": "ok"},
    )
    assert snapshot["ownership_state"]["summary_state"] == "ready"
    assert snapshot["session_lock"]["session_locked"] is True
    assert snapshot["deployment_profile"]["name"] == "clinical"
    assert snapshot["summary_state"] in {"ready", "degraded", "blocked"}
