from spine_ultrasound_ui.services.force_control_config import load_force_control_config


def test_force_control_config_is_loaded_from_repo_source():
    config = load_force_control_config()
    assert config["max_z_force_n"] == 35.0
    assert config["warning_z_force_n"] == 25.0
    assert config["max_xy_force_n"] == 20.0
    assert config["desired_contact_force_n"] == 10.0
    assert config["emergency_retract_mm"] == 50.0
    assert config["sensor_timeout_ms"] == 500
    assert config["stale_telemetry_ms"] == 250
    assert config["force_settle_window_ms"] == 150
    assert config["resume_force_band_n"] == 1.5
