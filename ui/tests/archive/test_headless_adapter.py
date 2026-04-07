from __future__ import annotations

import json
import time
from pathlib import Path

from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter


def test_headless_adapter_mock_command_path_updates_status():
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )

    assert adapter.command("connect_robot")["ok"] is True
    assert adapter.command("power_on")["ok"] is True
    assert adapter.command("set_auto_mode")["ok"] is True

    status = adapter.status()
    assert status["backend_mode"] == "mock"
    assert status["execution_state"] == "AUTO_READY"
    assert status["powered"] is True


def test_headless_adapter_mock_loop_populates_snapshot_topics():
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )
    adapter.start()
    try:
        time.sleep(0.15)
        topics = {item["topic"] for item in adapter.snapshot()}
        assert "core_state" in topics
        assert "safety_status" in topics
        assert "recording_status" in topics
    finally:
        adapter.stop()


def test_headless_adapter_rejects_unknown_commands():
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )
    try:
        adapter.command("definitely_not_a_real_command")
    except ValueError as exc:
        assert "unsupported command" in str(exc)
    else:
        raise AssertionError("unknown commands should be rejected")


def test_headless_adapter_exposes_protocol_schema():
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )

    schema = adapter.schema()
    assert schema["api_version"] == "v1"
    assert "lock_session" in schema["commands"]
    assert "safety_status" in schema["telemetry_topics"]


def test_headless_adapter_rejects_invalid_lock_session_payload():
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )
    try:
        adapter.command("lock_session", {"session_id": "S1"})
    except ValueError as exc:
        assert "missing required fields" in str(exc)
    else:
        raise AssertionError("invalid lock_session payload should be rejected before reaching runtime")


def test_headless_adapter_health_and_session_views(tmp_path):
    adapter = HeadlessAdapter(
        mode="mock",
        command_host="127.0.0.1",
        command_port=5656,
        telemetry_host="127.0.0.1",
        telemetry_port=5657,
    )
    adapter.command("connect_robot")
    adapter.command("power_on")
    adapter.command("set_auto_mode")
    session_dir = Path(tmp_path) / "session"
    adapter.command(
        "lock_session",
        {
            "session_id": "S1",
            "session_dir": str(session_dir),
            "config_snapshot": {"force_sensor_provider": "mock_force_sensor"},
            "device_roster": {},
            "scan_plan_hash": "hash-1",
        },
    )
    (session_dir / "export").mkdir(parents=True, exist_ok=True)
    (session_dir / "replay").mkdir(parents=True, exist_ok=True)
    (session_dir / "export" / "session_report.json").write_text(
        json.dumps({"session_id": "S1", "quality_summary": {"avg_quality_score": 0.81}}),
        encoding="utf-8",
    )
    (session_dir / "replay" / "replay_index.json").write_text(
        json.dumps({"session_id": "S1", "streams": {"camera": {"frame_count": 4}}}),
        encoding="utf-8",
    )
    (session_dir / "export" / "session_trends.json").write_text(
        json.dumps({"session_id": "S1", "history": [], "current": {"avg_quality_score": 0.81}, "trends": {}, "history_window": 5, "history_count": 0, "fleet_summary": {"sessions": 0}}),
        encoding="utf-8",
    )
    (session_dir / "export" / "diagnostics_pack.json").write_text(
        json.dumps({"session_id": "S1", "health_snapshot": {"execution_state": "AUTO_READY"}, "last_commands": [], "last_alarms": [], "summary": {"command_count": 0}}),
        encoding="utf-8",
    )
    (session_dir / "derived" / "sync").mkdir(parents=True, exist_ok=True)
    (session_dir / "derived" / "sync" / "frame_sync_index.json").write_text(
        json.dumps({"session_id": "S1", "rows": [{"frame_id": 1, "segment_id": 0, "usable": True, "quality_score": 0.9, "contact_confidence": 0.8, "ts_ns": 123}], "summary": {"usable_ratio": 0.75, "frame_count": 1}}),
        encoding="utf-8",
    )
    journal_path = session_dir / "raw" / "ui" / "command_journal.jsonl"
    annotations_path = session_dir / "raw" / "ui" / "annotations.jsonl"
    annotations_path.parent.mkdir(parents=True, exist_ok=True)
    annotations_path.write_text(json.dumps({"data": {"kind": "alarm", "message": "x"}}) + "\n", encoding="utf-8")

    health = adapter.health()
    current = adapter.current_session()
    report = adapter.current_report()
    replay = adapter.current_replay()
    trends = adapter.current_trends()
    diagnostics = adapter.current_diagnostics()
    annotations = adapter.current_annotations()
    command_trace = adapter.current_command_trace()
    assessment = adapter.current_assessment()

    assert health["backend_mode"] == "mock"
    assert current["session_id"] == "S1"
    assert current["trends_available"] is True
    assert current["diagnostics_available"] is True
    assert report["quality_summary"]["avg_quality_score"] == 0.81
    assert replay["streams"]["camera"]["frame_count"] == 4
    assert trends["session_id"] == "S1"
    assert diagnostics["summary"]["command_count"] == 0
    assert annotations["annotations"][0]["kind"] == "alarm"
    assert journal_path.exists()
