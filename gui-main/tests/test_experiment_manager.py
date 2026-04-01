import json
from pathlib import Path

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.models import ScanPlan, ScanSegment, ScanWaypoint


def test_create_and_lock_session(tmp_path):
    mgr = ExperimentManager(tmp_path)
    exp = mgr.create({"pressure_target": 1.5})
    preview_plan = ScanPlan(
        session_id="",
        plan_id="PREVIEW_TEST",
        approach_pose=ScanWaypoint(0, 0, 1, 180, 0, 90),
        retreat_pose=ScanWaypoint(0, 0, 2, 180, 0, 90),
        segments=[ScanSegment(segment_id=1, waypoints=[ScanWaypoint(0, 0, 0, 180, 0, 90)], target_pressure=1.5, scan_direction="up")],
    )
    session = mgr.lock_session(
        exp_id=exp["exp_id"],
        config_snapshot={"pressure_target": 1.5},
        device_roster={"robot": {"connected": True}},
        software_version="0.2.0",
        build_id="dev",
        scan_plan=preview_plan,
    )
    manifest = json.loads((Path(session["session_dir"]) / "meta" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["experiment_id"] == exp["exp_id"]
    assert manifest["session_id"] == session["session_id"]
    assert manifest["scan_plan_hash"] == ScanPlan.from_dict(session["scan_plan"]).plan_hash()


def test_append_artifact_preserves_manifest_semantics(tmp_path):
    mgr = ExperimentManager(tmp_path)
    exp = mgr.create({"pressure_target": 1.5})
    preview_plan = ScanPlan(
        session_id="",
        plan_id="PREVIEW_TEST",
        approach_pose=ScanWaypoint(0, 0, 1, 180, 0, 90),
        retreat_pose=ScanWaypoint(0, 0, 2, 180, 0, 90),
        segments=[ScanSegment(segment_id=1, waypoints=[ScanWaypoint(0, 0, 0, 180, 0, 90)], target_pressure=1.5, scan_direction="up")],
    )
    session = mgr.lock_session(
        exp_id=exp["exp_id"],
        config_snapshot={"pressure_target": 1.5},
        device_roster={"robot": {"connected": True}},
        software_version="0.2.0",
        build_id="dev",
        scan_plan=preview_plan,
    )
    session_dir = Path(session["session_dir"])
    before = mgr.load_manifest(session_dir)
    artifact_path = session_dir / "export" / "summary.txt"
    artifact_path.write_text("ok", encoding="utf-8")
    after = mgr.append_artifact(session_dir, "summary_text", artifact_path)
    assert after["scan_plan_hash"] == before["scan_plan_hash"]
    assert after["experiment_id"] == before["experiment_id"]
    assert after["artifacts"]["summary_text"] == "export/summary.txt"
