from __future__ import annotations

import pytest

from spine_ultrasound_ui.models import RuntimeConfig


def test_runtime_config_removes_emergency_fallback_targets() -> None:
    config = RuntimeConfig()
    payload = config.to_dict()
    for key in (
        'emergency_home_joint_rad',
        'emergency_approach_pose_xyzabc',
        'emergency_entry_pose_xyzabc',
        'emergency_retreat_pose_xyzabc',
    ):
        assert key not in payload


def test_runtime_config_rejects_legacy_fallback_aliases_on_load() -> None:
    with pytest.raises(ValueError, match="forbidden legacy keys"):
        RuntimeConfig.from_dict({
            'fallback_home_joint_rad': [1, 2, 3],
            'fallback_approach_pose_xyzabc': [1, 2, 3, 4, 5, 6],
            'fallback_entry_pose_xyzabc': [1, 2, 3, 4, 5, 6],
            'fallback_retreat_pose_xyzabc': [1, 2, 3, 4, 5, 6],
        })


def test_runtime_config_rejects_legacy_contract_shell_override_on_load() -> None:
    with pytest.raises(ValueError, match="forbidden legacy keys"):
        RuntimeConfig.from_dict({
            "allow_contract_shell_writes": True,
        })
