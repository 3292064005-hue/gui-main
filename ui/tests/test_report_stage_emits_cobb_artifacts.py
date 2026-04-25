import json
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


def _build_assessed_session(tmp_path: Path) -> Path:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_procedure()
    controller.safe_retreat()
    controller.save_results()
    controller.export_summary()
    controller.run_preprocess()
    controller.run_reconstruction()
    controller.run_assessment()
    assert controller.session_service.current_session_dir is not None
    return controller.session_service.current_session_dir


def test_report_stage_emits_cobb_artifacts(tmp_path: Path) -> None:
    session_dir = _build_assessed_session(tmp_path)
    measurement_path = session_dir / "derived" / "assessment" / "cobb_measurement.json"
    summary_path = session_dir / "derived" / "assessment" / "assessment_summary.json"
    report_path = session_dir / "export" / "session_report.json"
    uca_path = session_dir / "derived" / "assessment" / "uca_measurement.json"
    agreement_path = session_dir / "derived" / "assessment" / "assessment_agreement.json"

    assert measurement_path.exists()
    assert summary_path.exists()
    assert report_path.exists()
    assert uca_path.exists()
    assert agreement_path.exists()

    measurement = json.loads(measurement_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    uca = json.loads(uca_path.read_text(encoding="utf-8"))
    agreement = json.loads(agreement_path.read_text(encoding="utf-8"))

    assert "angle_deg" in measurement
    assert "confidence" in measurement
    assert "requires_manual_review" in measurement
    assert "measurement_source" in measurement
    assert "angle_deg" in uca
    assert "agreement_status" in agreement
    assert report["assessment_summary"]["cobb_angle_deg"] == summary["cobb_angle_deg"]
