from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_mock_mainline_e2e_workflow(tmp_path):
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)

    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()
    controller.pause_scan()
    controller.resume_scan()
    controller.safe_retreat()
    controller.save_results()
    controller.export_summary()
    controller.run_preprocess()
    controller.run_reconstruction()
    controller.run_assessment()

    session_dir = controller.session_service.current_session_dir
    assert session_dir is not None
    assert (session_dir / "meta" / "manifest.json").exists()
    assert (session_dir / "export" / "summary.json").exists()
    assert (session_dir / "export" / "summary.txt").exists()
    assert (session_dir / "export" / "session_report.json").exists()
    assert (session_dir / "derived" / "quality" / "quality_timeline.json").exists()
    assert (session_dir / "replay" / "replay_index.json").exists()
    assert (session_dir / "raw" / "ui" / "command_journal.jsonl").exists()
