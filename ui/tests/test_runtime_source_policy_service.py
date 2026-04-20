from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.runtime_source_policy_service import RuntimeSourcePolicyService


def test_research_profile_blocks_synthetic_guidance_and_mock_force():
    cfg = RuntimeConfig(camera_guidance_input_mode='synthetic', force_sensor_provider='mock_force_sensor')
    svc = RuntimeSourcePolicyService({'SPINE_DEPLOYMENT_PROFILE': 'research'})
    snapshot = svc.build_snapshot(config=cfg, guidance_source_type='fallback_simulated')
    assert snapshot.preview_ready is False
    assert snapshot.session_lock_ready is False
    assert snapshot.execution_write_ready is False
    assert snapshot.blockers


def test_dev_profile_warns_but_allows_preview():
    cfg = RuntimeConfig(camera_guidance_input_mode='synthetic', force_sensor_provider='mock_force_sensor')
    snapshot = RuntimeSourcePolicyService({'SPINE_DEPLOYMENT_PROFILE': 'dev'}).build_snapshot(config=cfg)
    assert snapshot.preview_ready is True
    assert snapshot.warnings
