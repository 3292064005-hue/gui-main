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


def test_update_manifest_rejects_artifact_boundary_mutations(tmp_path):
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
    try:
        mgr.update_manifest(
            session_dir,
            artifacts={"source_frame_set": "derived/sync/source_frame_set.json"},
            artifact_registry={
                "source_frame_set": {
                    "artifact_type": "source_frame_set",
                    "path": "derived/sync/source_frame_set.json",
                    "schema": "source_frame_set.schema.json",
                }
            },
        )
    except RuntimeError as exc:
        assert 'update_manifest cannot modify' in str(exc)
    else:
        raise AssertionError('update_manifest should reject artifact boundary mutations')
    after = mgr.load_manifest(session_dir)
    assert after["artifacts"] == before["artifacts"]
    assert after["artifact_registry"] == before["artifact_registry"]


def test_update_manifest_rejects_canonical_manifest_snapshot_mutations(tmp_path):
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
    try:
        mgr.update_manifest(
            session_dir,
            source_frame_set={},
            source_frame_set_hash='bogus',
        )
    except RuntimeError as exc:
        assert 'sync_canonical_manifest_fields' in str(exc)
        assert 'source_frame_set' in str(exc)
        assert 'source_frame_set_hash' in str(exc)
    else:
        raise AssertionError('update_manifest should reject canonical manifest snapshot mutations')
    after = mgr.load_manifest(session_dir)
    assert after["source_frame_set"] == before["source_frame_set"]
    assert after["source_frame_set_hash"] == before["source_frame_set_hash"]


def test_sync_canonical_manifest_fields_rejects_hash_only_updates(tmp_path):
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
    try:
        mgr.sync_canonical_manifest_fields(session_dir, source_frame_set_hash='bogus')
    except RuntimeError as exc:
        assert 'requires the matching canonical payload' in str(exc)
        assert 'source_frame_set_hash' in str(exc)
    else:
        raise AssertionError('sync_canonical_manifest_fields should reject hash-only updates')
    after = mgr.load_manifest(session_dir)
    assert after["source_frame_set_hash"] == before["source_frame_set_hash"]
    assert after["source_frame_set"] == before["source_frame_set"]
