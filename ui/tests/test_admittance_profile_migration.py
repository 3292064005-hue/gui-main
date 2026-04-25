from __future__ import annotations

from pathlib import Path

import yaml

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile


def test_runtime_config_to_dict_omits_legacy_projection_metadata():
    payload = RuntimeConfig().to_dict()
    assert "legacy_compatibility" not in payload


def test_xmate_profile_prefers_nested_contact_control_defaults():
    profile = load_xmate_profile()
    contact_control = profile.build_contact_control_profile()
    assert contact_control["max_normal_velocity_mm_s"] == 2.0
    assert contact_control["max_normal_acc_mm_s2"] == 30.0
    assert contact_control["max_normal_travel_mm"] == profile.seek_contact_max_travel_mm


def test_xmate_profile_derives_nested_contact_control_from_flat_fields(tmp_path: Path):
    payload = {
        "robot_model": "xmate3",
        "sdk_robot_class": "xMateRobot",
        "axis_count": 6,
        "normal_admittance_gain": 0.0002,
        "normal_damping_gain": 0.00005,
        "seek_contact_max_step_mm": 0.1,
        "pause_hold_integrator_leak": 0.03,
        "scan_pose_trim_gain": 0.11,
        "rt_max_pose_trim_deg": 1.8,
    }
    path = tmp_path / "robot.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    profile = load_xmate_profile(path)
    assert profile.build_contact_control_profile()["max_normal_step_mm"] == 0.1
    assert profile.build_orientation_trim_profile()["gain"] == 0.11


def test_runtime_config_from_legacy_flat_fields_synthesizes_nested_contracts():
    cfg = RuntimeConfig.from_dict({
        "normal_admittance_gain": 0.0002,
        "normal_damping_gain": 0.00005,
        "seek_contact_max_step_mm": 0.12,
        "seek_contact_max_travel_mm": 6.5,
        "pause_hold_integrator_leak": 0.03,
        "rt_integrator_limit_n": 11.0,
        "scan_pose_trim_gain": 0.14,
        "rt_max_pose_trim_deg": 2.2,
        "pressure_stale_ms": 140,
        "force_estimator_preferred_source": "wrench",
    })
    assert cfg.contact_control.max_normal_step_mm == 0.12
    assert cfg.contact_control.max_normal_travel_mm == 6.5
    assert cfg.contact_control.integrator_leak == 0.03
    assert cfg.contact_control.anti_windup_limit_n == 11.0
    assert cfg.orientation_trim.gain == 0.14
    assert cfg.orientation_trim.max_trim_deg == 2.2
    assert cfg.force_estimator.stale_timeout_ms == 140
    assert cfg.force_estimator.preferred_source == "wrench"


def test_xmate_profile_derives_force_estimator_from_flat_fields(tmp_path: Path):
    payload = {
        "robot_model": "xmate3",
        "sdk_robot_class": "xMateRobot",
        "axis_count": 6,
        "force_estimator_preferred_source": "pressure",
        "pressure_stale_ms": 135,
        "force_estimator_timeout_ms": 410,
        "force_estimator_min_confidence": 0.77,
    }
    path = tmp_path / "robot.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    profile = load_xmate_profile(path)
    force_estimator = profile.build_force_estimator_profile()
    assert force_estimator["preferred_source"] == "pressure"
    assert force_estimator["stale_timeout_ms"] == 135
    assert force_estimator["timeout_ms"] == 410
    assert force_estimator["min_confidence"] == 0.77
