from pathlib import Path


def test_cpp_lock_session_rolls_back_runtime_state_on_failure() -> None:
    source = Path('cpp_robot_core/src/core_runtime_session_execution.cpp').read_text(encoding='utf-8')
    assert 'auto rollback_lock_session = [this' in source
    assert 'config_ = previous_config;' in source
    assert 'session_id_ = previous_session_id;' in source
    assert 'session_dir_ = previous_session_dir;' in source
    assert 'authority_lease_ = previous_authority_lease;' in source
    assert 'sdk_robot_.rtControlPort().configureMainline(previous_runtime_cfg);' in source
    assert 'recording_service_.closeSession();' in source
    assert 'catch (const std::exception& exc)' in source
    assert 'lock_session failed:' in source
