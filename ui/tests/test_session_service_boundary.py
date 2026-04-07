from __future__ import annotations

from pathlib import Path

import pytest

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.session_service import SessionService
from spine_ultrasound_ui.models import RuntimeConfig


def test_session_service_rollback_pending_lock_raises_when_cleanup_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = SessionService(ExperimentManager(tmp_path))
    exp = service.create_experiment(RuntimeConfig())
    locked_dir = Path(exp.save_dir) / "session_locked"
    locked_dir.mkdir(parents=True, exist_ok=True)
    service.current_session_dir = locked_dir

    def _boom(path: Path) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr("spine_ultrasound_ui.core.session_service.shutil.rmtree", _boom)
    with pytest.raises(RuntimeError, match="failed to remove pending session directory"):
        service.rollback_pending_lock()
