from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.contract_consistency_service import ContractConsistencyService
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.release_evidence_pack_service import ReleaseEvidencePackService


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _build_session(tmp_path: Path) -> Path:
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
    controller.pause_scan()
    controller.resume_scan()
    controller.safe_retreat()
    controller.save_results()
    controller.export_summary()
    assert controller.session_service.current_session_dir is not None
    return controller.session_service.current_session_dir


def test_contract_consistency_and_release_evidence_are_materialized(tmp_path: Path):
    session_dir = _build_session(tmp_path)
    contract = json.loads((session_dir / 'derived' / 'session' / 'contract_consistency.json').read_text(encoding='utf-8'))
    evidence = json.loads((session_dir / 'export' / 'release_evidence_pack.json').read_text(encoding='utf-8'))
    resume_attempts = json.loads((session_dir / 'derived' / 'session' / 'resume_attempts.json').read_text(encoding='utf-8'))
    manifest = json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8'))

    assert contract['summary']['mismatch_count'] == 0
    assert contract['summary']['required_artifact_coverage'] > 0.8
    assert evidence['release_candidate'] is True
    assert resume_attempts['summary']['attempt_count'] >= 2
    assert manifest['artifact_registry']['contract_consistency']['path'] == 'derived/session/contract_consistency.json'
    assert manifest['artifact_registry']['release_evidence_pack']['path'] == 'export/release_evidence_pack.json'
    assert manifest['artifact_registry']['resume_attempts']['path'] == 'derived/session/resume_attempts.json'


def test_services_can_recompute_contract_and_release_evidence(tmp_path: Path):
    session_dir = _build_session(tmp_path)
    contract = ContractConsistencyService().build(session_dir)
    release = ReleaseEvidencePackService().build(session_dir)
    assert contract['summary']['consistent'] is True
    assert release['release_candidate'] is True
    assert any(item['artifact'] == 'diagnostics_pack' for item in release['evidence_index'])
