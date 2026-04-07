from spine_ultrasound_ui.models.config_model import RuntimeConfig
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile


def test_runtime_config_phase_policy_defaults_exposed():
    config = RuntimeConfig()
    assert config.seek_contact_max_travel_mm > 0.0
    assert config.retract_travel_mm > 0.0
    assert config.scan_follow_lateral_amplitude_mm >= 0.0
    assert config.scan_follow_frequency_hz > 0.0
    assert config.contact_force_target_n > 0.0
    assert config.scan_force_target_n > 0.0
    assert config.retract_timeout_ms > 0.0
    assert config.scan_tangent_speed_max_mm_s >= config.scan_tangent_speed_min_mm_s


def test_xmate_profile_phase_policy_roundtrip():
    profile = load_xmate_profile()
    payload = profile.to_dict()
    assert payload["seek_contact_max_travel_mm"] > 0.0
    assert payload["retract_travel_mm"] > 0.0
    assert payload["scan_follow_lateral_amplitude_mm"] >= 0.0
    assert payload["scan_follow_frequency_hz"] > 0.0
    contract = payload["rt_phase_contract"]
    assert contract["common"]["rt_max_cart_step_mm"] > 0.0
    assert contract["seek_contact"]["contact_force_target_n"] > 0.0
    assert contract["scan_follow"]["scan_tangent_speed_max_mm_s"] >= contract["scan_follow"]["scan_tangent_speed_min_mm_s"]
    assert contract["controlled_retract"]["retract_timeout_ms"] > 0.0
