from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_removed_shim_files_are_absent() -> None:
    removed = [
        ROOT / "spine_ultrasound_ui/compat.py",
        ROOT / "spine_ultrasound_ui/core/event_bus.py",
        ROOT / "spine_ultrasound_ui/services/runtime_event_platform.py",
        ROOT / "spine_ultrasound_ui/services/sdk_unit_contract.py",
        ROOT / "spine_ultrasound_ui/core_pipeline/shm_client.py",
    ]
    assert all(not path.exists() for path in removed)


def test_canonical_replacements_exist() -> None:
    required = [
        ROOT / "spine_ultrasound_ui/core/ui_local_bus.py",
        ROOT / "spine_ultrasound_ui/services/event_bus.py",
        ROOT / "spine_ultrasound_ui/services/event_replay_bus.py",
        ROOT / "spine_ultrasound_ui/utils/sdk_unit_contract.py",
        ROOT / "spine_ultrasound_ui/services/transport/shm_client.py",
        ROOT / "tests/runtime_compat.py",
    ]
    assert all(path.exists() for path in required)
