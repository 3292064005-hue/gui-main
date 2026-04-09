from spine_ultrasound_ui.services.runtime_command_catalog import capability_claims, command_capability_claim


def test_runtime_command_capability_claims_cover_rt_motion_mainline() -> None:
    claims = capability_claims()
    assert 'rt_motion_write' in claims
    assert {'approach_prescan', 'seek_contact', 'start_scan', 'pause_scan', 'resume_scan', 'safe_retreat'} <= set(claims['rt_motion_write'])
    assert command_capability_claim('validate_scan_plan') == 'plan_compile'
    assert command_capability_claim('compile_scan_plan') == 'plan_compile'
