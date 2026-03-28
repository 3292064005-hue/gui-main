from spine_ultrasound_ui.services import ipc_messages_pb2
from spine_ultrasound_ui.services.core_transport import parse_reply_payload, parse_telemetry_payload
from spine_ultrasound_ui.services.ipc_protocol import (
    CommandEnvelope,
    COMMAND_SPECS,
    PROTOCOL_VERSION,
    ProtocolVersionError,
    ReplyEnvelope,
    TelemetryEnvelope,
    ensure_protocol_version,
    protocol_schema,
    validate_command_payload,
)


def test_command_envelope_json_roundtrip():
    env = CommandEnvelope(command="connect_robot", payload={"a": 1}, request_id="r1")
    parsed = CommandEnvelope.from_json(env.to_json())
    assert parsed.command == "connect_robot"
    assert parsed.request_id == "r1"
    assert parsed.protocol_version == PROTOCOL_VERSION


def test_command_envelope_protobuf_roundtrip():
    env = CommandEnvelope(command="lock_session", payload={"session_id": "S1"}, request_id="r1")
    proto = env.to_protobuf()
    parsed = CommandEnvelope.from_protobuf(proto)
    assert parsed.command == "lock_session"
    assert parsed.payload["session_id"] == "S1"
    assert parsed.request_id == "r1"


def test_reply_from_json():
    rep = ReplyEnvelope.from_json('{"ok": true, "message": "ok", "request_id": "1", "data": {"x": 1}, "protocol_version": 1}')
    assert rep.ok is True
    assert rep.data["x"] == 1
    assert rep.protocol_version == PROTOCOL_VERSION


def test_reply_envelope_protobuf_roundtrip():
    rep = ReplyEnvelope(ok=True, message="ok", request_id="r1", data={"safe_to_arm": True})
    proto = rep.to_protobuf()
    parsed = ReplyEnvelope.from_protobuf(proto)
    assert parsed.ok is True
    assert parsed.data["safe_to_arm"] is True


def test_telemetry_from_json():
    tel = TelemetryEnvelope.from_json('{"topic": "core_state", "ts_ns": 10, "data": {"execution_state": "AUTO_READY"}, "protocol_version": 1}')
    assert tel.topic == "core_state"
    assert tel.data["execution_state"] == "AUTO_READY"


def test_telemetry_envelope_protobuf_roundtrip():
    proto = ipc_messages_pb2.TelemetryEnvelope(
        protocol_version=1,
        topic="robot_state",
        ts_ns=42,
        data_json='{"powered": true}',
    )
    tel = TelemetryEnvelope.from_protobuf(proto)
    assert tel.topic == "robot_state"
    assert tel.data["powered"] is True
    assert tel.ts_ns == 42


def test_protocol_version_guard_accepts_canonical_version():
    ensure_protocol_version(PROTOCOL_VERSION, "Reply")


def test_protocol_version_guard_rejects_mismatch():
    try:
        ensure_protocol_version(PROTOCOL_VERSION + 1, "Reply")
    except ProtocolVersionError as exc:
        assert "expected 1" in str(exc)
    else:
        raise AssertionError("protocol version mismatch should be rejected")


def test_parse_reply_payload_rejects_mismatched_protocol_version():
    proto = ipc_messages_pb2.Reply(
        protocol_version=PROTOCOL_VERSION + 1,
        ok=False,
        message="bad version",
        request_id="req-1",
        data_json="{}",
    )
    try:
        parse_reply_payload(proto.SerializeToString())
    except ProtocolVersionError as exc:
        assert "Reply protocol_version mismatch" in str(exc)
    else:
        raise AssertionError("reply payload with wrong protocol version should be rejected")


def test_parse_telemetry_payload_rejects_mismatched_protocol_version():
    proto = ipc_messages_pb2.TelemetryEnvelope(
        protocol_version=PROTOCOL_VERSION + 1,
        topic="core_state",
        ts_ns=1,
        data_json='{"execution_state": "BOOT"}',
    )
    try:
        parse_telemetry_payload(proto.SerializeToString())
    except ProtocolVersionError as exc:
        assert "TelemetryEnvelope protocol_version mismatch" in str(exc)
    else:
        raise AssertionError("telemetry payload with wrong protocol version should be rejected")


def test_protocol_schema_exposes_canonical_contract():
    schema = protocol_schema()
    assert schema["protocol_version"] == PROTOCOL_VERSION
    assert schema["commands"]["lock_session"]["required_payload_fields"] == COMMAND_SPECS["lock_session"]["required_payload_fields"]
    assert "desired_contact_force_n" in schema["force_control"]
    assert "sensor_timeout_ms" in schema["force_control"]
    assert "core_state" in schema["telemetry_topics"]
    assert "workflow_step" in schema["telemetry_topics"]["alarm_event"]["core_fields"]


def test_validate_command_payload_rejects_missing_required_fields():
    try:
        validate_command_payload("lock_session", {"session_id": "S1"})
    except ValueError as exc:
        assert "missing required fields" in str(exc)
    else:
        raise AssertionError("lock_session without mandatory fields should be rejected")


def test_validate_command_payload_accepts_scan_plan_contract():
    validate_command_payload(
        "load_scan_plan",
        {
            "scan_plan": {
                "plan_id": "plan-1",
                "segments": [{"segment_id": 1, "points": [{"x": 0.0, "y": 0.0, "z": 0.0}]}],
            }
        },
    )
