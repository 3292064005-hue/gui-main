import json
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


def test_session_products_are_materialized_and_registered(tmp_path):
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

    session_dir = controller.session_service.current_session_dir
    assert session_dir is not None
    manifest = json.loads((session_dir / "meta" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifacts"]["summary_json"] == "export/summary.json"
    assert manifest["artifacts"]["summary_text"] == "export/summary.txt"
    assert manifest["artifacts"]["quality_timeline"] == "derived/quality/quality_timeline.json"
    assert manifest["artifacts"]["replay_index"] == "replay/replay_index.json"
    assert manifest["artifacts"]["session_report"] == "export/session_report.json"
