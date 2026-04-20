from pathlib import Path

from spine_ultrasound_ui.utils.runtime_config_contract import (
    cpp_apply_snapshot_output_path,
    cpp_field_decls_output_path,
    render_cpp_apply_snapshot_macro,
    render_cpp_field_decl_macros,
)


def test_generated_runtime_config_includes_are_materialized_and_consumed() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    field_target = cpp_field_decls_output_path(repo_root)
    apply_target = cpp_apply_snapshot_output_path(repo_root)
    runtime_types = (repo_root / 'cpp_robot_core/include/robot_core/runtime_types.h').read_text(encoding='utf-8')
    session_runtime = (repo_root / 'cpp_robot_core/src/session_runtime.cpp').read_text(encoding='utf-8')

    assert field_target.exists()
    assert apply_target.exists()
    assert field_target.read_text(encoding='utf-8') == render_cpp_field_decl_macros()
    assert apply_target.read_text(encoding='utf-8') == render_cpp_apply_snapshot_macro()
    assert '#include "robot_core/generated_runtime_config_field_decls.inc"' in runtime_types
    assert '#include "robot_core/generated_runtime_config_apply_snapshot.inc"' in session_runtime
    assert 'ROBOT_CORE_RUNTIME_CONFIG_FIELDS' in runtime_types
    assert 'ROBOT_CORE_APPLY_RUNTIME_CONFIG_SNAPSHOT(config_, source);' in session_runtime
    assert 'config_.robot_model = ROBOT_CORE_DEFAULT_ROBOT_MODEL;' not in session_runtime
