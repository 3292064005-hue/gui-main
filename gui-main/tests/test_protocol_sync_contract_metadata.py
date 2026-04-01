from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_protocol_sync_checks_command_write_flags_and_state_preconditions() -> None:
    script = _read("scripts/check_protocol_sync.py")
    assert "command write flag mismatch" in script
    assert "command state preconditions mismatch" in script


def test_cpp_command_registry_carries_state_precondition_metadata() -> None:
    header = _read("cpp_robot_core/include/robot_core/command_registry.h")
    source = _read("cpp_robot_core/src/command_registry.cpp")
    assert "state_preconditions_signature" in header
    assert "commandStatePreconditions" in header
    assert '"CONTACT_STABLE|PAUSED_HOLD"' in source
