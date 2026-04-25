import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.headless_session_products_reader import HeadlessSessionProductsReader
from spine_ultrasound_ui.services.headless_telemetry_cache import HeadlessTelemetryCache
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.session_evidence_seal_service import SessionEvidenceSealService
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _reader_for_session(session_dir: Path) -> HeadlessSessionProductsReader:
    telemetry_cache = HeadlessTelemetryCache()
    return HeadlessSessionProductsReader(
        telemetry_cache=telemetry_cache,
        resolve_session_dir=lambda: session_dir,
        current_session_id=lambda: json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8')).get('session_id', session_dir.name),
        manifest_reader=lambda p=None: json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8')),
        json_reader=lambda path: json.loads(path.read_text(encoding='utf-8')),
        json_if_exists_reader=lambda path: json.loads(path.read_text(encoding='utf-8')) if path.exists() else {},
        jsonl_reader=lambda path: [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()] if path.exists() else [],
        status_reader=lambda: {'execution_state': 'AUTO_READY'},
        derive_recovery_state=lambda core: 'IDLE',
        command_policy_catalog=lambda: {'policies': []},
        integrity_service=SessionIntegrityService(),
        session_intelligence=SessionIntelligenceService(),
        evidence_seal_service=SessionEvidenceSealService(),
    )


def test_headless_assessment_reads_authoritative_artifacts(tmp_path: Path) -> None:
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
    reader = _reader_for_session(controller.session_service.current_session_dir)
    assessment = reader.current_assessment()
    assert assessment["curve_candidate"]["status"] in {"authoritative", "degraded", "prior_assisted"}
    assert assessment["curve_candidate"]["source"] in {"derived/assessment/cobb_measurement.json", "derived/assessment/prior_assisted_cobb.json"}
    assert assessment["curve_candidate"]["measurement_source"] in {"lamina_center_cobb", "curve_window_fallback"}
    assert assessment["cobb_candidate_deg"] is not None
    assert "uca_candidate_deg" in assessment
    assert "agreement" in assessment
