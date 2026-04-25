from spine_ultrasound_ui.models import RuntimeConfig, SystemState
from spine_ultrasound_ui.services.mock_core_runtime import MockCoreRuntime


def test_mock_runtime_command_flow_creates_path_validated_state(tmp_path):
    runtime = MockCoreRuntime()
    runtime.update_runtime_config(RuntimeConfig())
    assert runtime.handle_command("connect_robot").ok
    assert runtime.handle_command("power_on").ok
    assert runtime.handle_command("set_auto_mode").ok
    assert runtime.handle_command("lock_session", {"session_id": "S1", "session_dir": str(tmp_path), "device_roster": {}}).ok
    assert runtime.handle_command(
        "load_scan_plan",
        {
            "scan_plan": {
                "session_id": "S1",
                "plan_id": "P1",
                "approach_pose": {"x": 0, "y": 0, "z": 1, "rx": 180, "ry": 0, "rz": 90},
                "retreat_pose": {"x": 0, "y": 0, "z": 2, "rx": 180, "ry": 0, "rz": 90},
                "segments": [{"segment_id": 1, "waypoints": [{"x": 0, "y": 0, "z": 0, "rx": 180, "ry": 0, "rz": 90}], "target_pressure": 1.5, "scan_direction": "up"}],
            }
        },
    ).ok
    assert runtime.execution_state == SystemState.PATH_VALIDATED


def test_mock_runtime_tick_emits_core_state_topic():
    runtime = MockCoreRuntime()
    topics = {env.topic for env in runtime.tick()}
    assert "core_state" in topics
    assert "safety_status" in topics


def test_mock_runtime_alarm_is_traceable(tmp_path):
    runtime = MockCoreRuntime()
    config = RuntimeConfig(pressure_upper=0.2)
    runtime.update_runtime_config(config)
    assert runtime.handle_command("connect_robot").ok
    assert runtime.handle_command("power_on").ok
    assert runtime.handle_command("set_auto_mode").ok
    assert runtime.handle_command(
        "lock_session",
        {
            "session_id": "S1",
            "session_dir": str(tmp_path),
            "device_roster": {},
            "config_snapshot": config.to_dict(),
        },
    ).ok
    assert runtime.handle_command(
        "load_scan_plan",
        {
            "scan_plan": {
                "session_id": "S1",
                "plan_id": "P1",
                "approach_pose": {"x": 0, "y": 0, "z": 1, "rx": 180, "ry": 0, "rz": 90},
                "retreat_pose": {"x": 0, "y": 0, "z": 2, "rx": 180, "ry": 0, "rz": 90},
                "segments": [{"segment_id": 1, "waypoints": [{"x": 0, "y": 0, "z": 0, "rx": 180, "ry": 0, "rz": 90}], "target_pressure": 1.5, "scan_direction": "up"}],
            }
        },
    ).ok
    assert runtime.handle_command("seek_contact").ok
    assert runtime.handle_command("start_procedure", {"procedure": "scan"}).ok
    assert runtime.handle_command("inject_fault", {"fault_name": "overpressure"}).ok
    alarms = []
    for _ in range(6):
        alarms.extend(env.data for env in runtime.tick() if env.topic == "alarm_event")
        if alarms:
            break
    assert alarms
    assert alarms[0]["session_id"] == "S1"
    assert "segment_id" in alarms[0]
    assert alarms[0]["event_ts_ns"] > 0



def test_mock_runtime_exposes_authoritative_runtime_envelope_command():
    runtime = MockCoreRuntime()
    reply = runtime.handle_command("get_authoritative_runtime_envelope")
    assert reply.ok is True
    assert reply.data["authority_source"] == "mock_runtime_contract"
    assert "control_authority" in reply.data
    assert "runtime_config_applied" in reply.data
    assert "session_freeze" in reply.data
    assert "final_verdict" in reply.data



def test_stop_scan_before_scanning_does_not_mark_scan_complete() -> None:
    runtime = MockCoreRuntime()
    assert runtime.handle_command("connect_robot").ok
    assert runtime.handle_command("power_on").ok
    assert runtime.handle_command("set_auto_mode").ok
    assert runtime.handle_command("lock_session", {"session_id": "S1"}).ok
    assert runtime.handle_command("load_scan_plan", {"scan_plan": {"session_id": "S1", "plan_id": "P1", "approach_pose": {"x": 0, "y": 0, "z": 1, "rx": 180, "ry": 0, "rz": 90}, "retreat_pose": {"x": 0, "y": 0, "z": 2, "rx": 180, "ry": 0, "rz": 90}, "segments": [{"segment_id": 1, "waypoints": [{"x": 0, "y": 0, "z": 0, "rx": 180, "ry": 0, "rz": 90}], "target_pressure": 1.5, "scan_direction": "up"}]}}).ok
    assert runtime.handle_command("start_procedure", {"procedure": "scan"}).ok
    assert runtime.execution_state in {SystemState.APPROACHING, SystemState.CONTACT_SEEKING}
    reply = runtime.handle_command("stop_scan")
    assert reply.ok
    assert runtime.retreat_completion_state == SystemState.PATH_VALIDATED
    assert runtime.recommended_action == "WAIT_RETREAT_COMPLETE"


def test_stop_scan_during_scanning_marks_scan_complete() -> None:
    runtime = MockCoreRuntime()
    assert runtime.handle_command("connect_robot").ok
    assert runtime.handle_command("power_on").ok
    assert runtime.handle_command("set_auto_mode").ok
    assert runtime.handle_command("lock_session", {"session_id": "S1"}).ok
    assert runtime.handle_command("load_scan_plan", {"scan_plan": {"session_id": "S1", "plan_id": "P1", "approach_pose": {"x": 0, "y": 0, "z": 1, "rx": 180, "ry": 0, "rz": 90}, "retreat_pose": {"x": 0, "y": 0, "z": 2, "rx": 180, "ry": 0, "rz": 90}, "segments": [{"segment_id": 1, "waypoints": [{"x": 0, "y": 0, "z": 0, "rx": 180, "ry": 0, "rz": 90}], "target_pressure": 1.5, "scan_direction": "up"}]}}).ok
    runtime.execution_state = SystemState.SCANNING
    reply = runtime.handle_command("stop_scan")
    assert reply.ok
    assert runtime.retreat_completion_state == SystemState.SCAN_COMPLETE
    assert runtime.recommended_action == "WAIT_SCAN_COMPLETE"
