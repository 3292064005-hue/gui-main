from pathlib import Path


def test_cpp_lock_session_rolls_back_runtime_state_on_failure() -> None:
    source = Path('cpp_robot_core/src/core_runtime_session_commands.cpp').read_text(encoding='utf-8')
    assert 'auto rollback_lock_session = [this' in source
    assert 'state_store_.config = previous_config;' in source
    assert 'state_store_.session_id = previous_session_id;' in source
    assert 'state_store_.session_dir = previous_session_dir;' in source
    assert 'authority_kernel_.lease = previous_authority_lease;' in source
    assert 'procedure_executor_.sdk_robot.rtControlPort().configureMainline(previous_runtime_cfg);' in source
    assert 'evidence_projector_.recording_service.closeSession();' in source
    assert 'catch (const std::exception& exc)' in source
    assert 'lock_session failed:' in source
