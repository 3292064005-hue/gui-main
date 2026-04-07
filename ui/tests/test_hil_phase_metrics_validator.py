from __future__ import annotations

from scripts.validate_hil_phase_metrics import validate_metrics


def _runtime_cfg() -> dict:
    return {
        "rt_phase_contract": {
            "common": {
                "rt_max_pose_trim_deg": 1.5,
            },
            "seek_contact": {
                "contact_force_tolerance_n": 1.0,
                "seek_contact_max_travel_mm": 6.0,
            },
            "scan_follow": {
                "scan_force_tolerance_n": 1.0,
                "scan_tangent_speed_max_mm_s": 10.0,
            },
            "pause_hold": {
                "pause_hold_position_guard_mm": 0.4,
            },
            "controlled_retract": {
                "retract_timeout_ms": 1200.0,
            },
        }
    }


def _evidence() -> dict:
    return {
        "seek_contact": {
            "contact_establish_time_ms": 200.0,
            "peak_force_overshoot_n": 1.5,
            "max_seek_travel_mm": 5.0,
        },
        "scan_follow": {
            "normal_force_rms_error_n": 0.8,
            "tangent_speed_rms_mm_s": 8.0,
            "pose_trim_rms_deg": 0.9,
        },
        "pause_hold": {
            "drift_mm_30s": 0.3,
            "drift_mm_60s": 0.5,
        },
        "controlled_retract": {
            "release_detection_time_ms": 400.0,
            "total_retract_time_ms": 900.0,
            "timeout_faulted": False,
        },
    }


def test_validate_hil_phase_metrics_passes_for_nominal_evidence() -> None:
    failures = validate_metrics(_runtime_cfg(), _evidence())
    assert failures == []


def test_validate_hil_phase_metrics_fails_on_exceeded_seek_travel() -> None:
    evidence = _evidence()
    evidence["seek_contact"]["max_seek_travel_mm"] = 9.0
    failures = validate_metrics(_runtime_cfg(), evidence)
    assert any("seek_contact.max_seek_travel_mm" in item for item in failures)
