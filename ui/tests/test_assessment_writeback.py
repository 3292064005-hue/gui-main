import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_assessment_writeback_updates_runtime_and_experiment(tmp_path: Path) -> None:
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
    controller.safe_retreat()
    controller.save_results()
    controller.export_summary()
    controller.run_preprocess()
    controller.run_reconstruction()
    controller.run_assessment()

    assert controller.session_service.current_experiment is not None
    assert controller.telemetry.metrics.cobb_angle == controller.session_service.current_experiment.cobb_angle
    assert controller.telemetry.metrics.cobb_angle >= 0.0
    assert controller.telemetry.metrics.measurement_source != ""
    assert controller.session_service.current_experiment.measurement_source != ""
