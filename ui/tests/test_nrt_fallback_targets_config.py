from __future__ import annotations

from spine_ultrasound_ui.models import RuntimeConfig


def test_runtime_config_exposes_emergency_fallback_targets() -> None:
    config = RuntimeConfig()
    payload = config.to_dict()
    for key in (
        'emergency_home_joint_rad',
        'emergency_approach_pose_xyzabc',
        'emergency_entry_pose_xyzabc',
        'emergency_retreat_pose_xyzabc',
    ):
        assert key in payload
        assert payload[key]
