from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_command_server_uses_deadline_driven_periodic_loop() -> None:
    source = _read('cpp_robot_core/src/command_server.cpp')
    assert 'PeriodicLoopController' in source
    assert 'sleep_until' in source
    assert 'recordRtLoopSample' in source


def test_sdk_robot_facade_reports_contract_shell_vs_live_binding() -> None:
    header = _read('cpp_robot_core/include/robot_core/sdk_robot_facade.h')
    source = _read('cpp_robot_core/src/sdk_robot_facade_state.cpp')
    assert 'liveBindingEstablished' in header
    assert 'liveTakeoverReady' in header
    assert 'vendored_sdk_contract_shell' in source
    assert 'xcore_sdk_contract_shell' in source
