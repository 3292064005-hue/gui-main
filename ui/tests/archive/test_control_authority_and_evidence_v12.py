from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.session_service import SessionService
from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan, ScanSegment, ScanWaypoint
from spine_ultrasound_ui.services.control_authority_service import ControlAuthorityService
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter


def _preview_plan() -> ScanPlan:
    return ScanPlan(
        session_id="",
        plan_id="PREVIEW_TEST",
        approach_pose=ScanWaypoint(0, 0, 1, 180, 0, 90),
        retreat_pose=ScanWaypoint(0, 0, 2, 180, 0, 90),
        segments=[ScanSegment(segment_id=1, waypoints=[ScanWaypoint(0, 0, 0, 180, 0, 90)], target_pressure=8.0, scan_direction="up")],
    )


def test_control_authority_service_rejects_conflicting_owner() -> None:
    service = ControlAuthorityService(strict_mode=True, auto_issue_implicit_lease=False)
    first = service.acquire(actor_id="desktop-a", role="operator", workspace="desktop", session_id="S1", intent_reason="scan")
    assert first["ok"] is True
    second = service.acquire(actor_id="desktop-b", role="operator", workspace="desktop", session_id="S1", intent_reason="scan")
    assert second["ok"] is False
    snapshot = service.snapshot()
    assert snapshot["has_owner"] is True
    assert snapshot["owner"]["actor_id"] == "desktop-a"


def test_headless_adapter_blocks_conflicting_command_context() -> None:
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )
    ok_reply = adapter.command("connect_robot", {"_command_context": {"actor_id": "desktop-a", "workspace": "desktop", "role": "operator"}})
    assert ok_reply["ok"] is True
    blocked_reply = adapter.command("power_on", {"_command_context": {"actor_id": "desktop-b", "workspace": "desktop", "role": "operator"}})
    assert blocked_reply["ok"] is False
    assert "控制权" in blocked_reply["message"]
    authority = adapter.control_authority_status()
    assert authority["owner"]["actor_id"] == "desktop-a"


def test_session_service_writes_session_evidence_seal(tmp_path: Path) -> None:
    config = RuntimeConfig()
    service = SessionService(ExperimentManager(tmp_path))
    service.create_experiment(config)
    preview_plan = _preview_plan()
    service.save_preview_plan(preview_plan)
    locked = service.ensure_locked(
        config,
        {"robot": {"connected": True}},
        preview_plan,
        protocol_version=1,
        safety_thresholds={"sensor_timeout_ms": 500},
        device_health_snapshot={"pressure": {"fresh": True}},
        patient_registration={"source": "camera"},
        control_authority={
            "summary_state": "ready",
            "summary_label": "控制权已锁定",
            "detail": "desktop-a@desktop/operator",
            "owner": {"actor_id": "desktop-a", "workspace": "desktop", "role": "operator"},
            "active_lease": {"lease_id": "lease-1"},
        },
    )
    seal_path = locked.session_dir / "meta" / "session_evidence_seal.json"
    assert seal_path.exists()
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    assert seal["session_id"] == locked.session_id
    assert seal["seal_digest"]
    manifest = json.loads((locked.session_dir / "meta" / "manifest.json").read_text(encoding="utf-8"))
    assert "session_evidence_seal" in manifest["artifact_registry"]
    assert manifest["control_authority"]["summary_label"] == "控制权已锁定"
