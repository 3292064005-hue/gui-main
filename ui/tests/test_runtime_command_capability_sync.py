from spine_ultrasound_ui.services.runtime_command_catalog import (
    capability_claims,
    canonical_aliases,
    canonical_command_name,
    command_alias_kind,
    command_capability_claim,
    command_handler_group,
)


def test_runtime_command_capability_claims_cover_rt_motion_mainline() -> None:
    claims = capability_claims()
    assert 'rt_motion_write' in claims
    assert {'approach_prescan', 'seek_contact', 'start_procedure', 'start_scan', 'pause_scan', 'resume_scan', 'safe_retreat'} <= set(claims['rt_motion_write'])
    assert command_capability_claim('validate_scan_plan') == 'plan_compile'
    assert command_capability_claim('compile_scan_plan') == 'plan_compile'


def test_runtime_command_alias_metadata_is_manifest_backed() -> None:
    assert canonical_command_name('compile_scan_plan') == 'validate_scan_plan'
    assert command_alias_kind('compile_scan_plan') == 'deprecated_alias'
    assert canonical_aliases('validate_scan_plan') == ('compile_scan_plan',)
    assert command_handler_group('start_procedure') == 'handleExecutionCommand'
