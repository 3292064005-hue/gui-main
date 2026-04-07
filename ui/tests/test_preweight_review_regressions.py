from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.core.postprocess_service import PostprocessService
from spine_ultrasound_ui.services.datasets.session_export_service import SessionExportService
from spine_ultrasound_ui.services.headless_session_products_reader import HeadlessSessionProductsReader
from spine_ultrasound_ui.services.headless_telemetry_cache import HeadlessTelemetryCache
from spine_ultrasound_ui.services.qa_pack_service import QAPackService
from spine_ultrasound_ui.services.reconstruction.closure_profile import load_reconstruction_profile
from spine_ultrasound_ui.services.session_evidence_seal_service import SessionEvidenceSealService
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService


def _reader_for_session(session_dir: Path) -> HeadlessSessionProductsReader:
    return HeadlessSessionProductsReader(
        telemetry_cache=HeadlessTelemetryCache(),
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


def test_invalid_profile_config_falls_back_to_defaults(tmp_path: Path) -> None:
    invalid = tmp_path / 'broken.json'
    invalid.write_text('{"profile_name": ', encoding='utf-8')
    profile = load_reconstruction_profile(str(invalid))
    assert profile['profile_name'] == 'weighted_runtime'
    assert profile['closure_mode'] == 'runtime_optional'


def test_prior_assisted_sidecar_decision_accepts_reconstruction_contamination() -> None:
    payload = {
        'measurement_source': 'lamina_center_cobb',
        'closure_verdict': 'prior_assisted',
        'source_contamination_flags': ['registration_prior_curve_used'],
    }
    assert PostprocessService._should_write_prior_assisted_cobb_sidecar(payload) is True


def test_export_and_readers_surface_sidecars_and_training_bridge(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'derived' / 'reconstruction').mkdir(parents=True)
    (session_dir / 'derived' / 'training_bridge').mkdir(parents=True)
    (session_dir / 'derived' / 'assessment').mkdir(parents=True)
    (session_dir / 'export').mkdir(parents=True)
    manifest = {'session_id': 'S1', 'experiment_id': 'E1', 'patient_id': 'P1', 'robot_profile': {'robot_model': 'xmate'}, 'artifact_registry': {}}
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    (session_dir / 'meta' / 'patient_registration.json').write_text(json.dumps({'patient_id': 'P1'}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'reconstruction_input_index.json').write_text(json.dumps({'session_id': 'S1'}), encoding='utf-8')
    (session_dir / 'derived' / 'training_bridge' / 'model_ready_input_index.json').write_text(json.dumps({'session_id': 'S1', 'ready_for_runtime': False}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'spine_curve.json').write_text(json.dumps({'points': []}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'prior_assisted_curve.json').write_text(json.dumps({'measurement_source': 'registration_prior_curve'}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'landmark_track.json').write_text(json.dumps({}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'reconstruction_summary.json').write_text(json.dumps({'closure_verdict': 'prior_assisted', 'measurement_source': 'registration_prior_curve', 'source_contamination_flags': ['registration_prior_curve_used'], 'confidence': 0.1, 'requires_manual_review': True}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'lamina_candidates.json').write_text(json.dumps({}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'pose_series.json').write_text(json.dumps({}), encoding='utf-8')
    (session_dir / 'derived' / 'assessment' / 'cobb_measurement.json').write_text(json.dumps({'angle_deg': 12.0, 'measurement_source': 'lamina_center_cobb', 'closure_verdict': 'prior_assisted', 'source_contamination_flags': ['registration_prior_curve_used'], 'evidence_refs': []}), encoding='utf-8')
    (session_dir / 'derived' / 'assessment' / 'prior_assisted_cobb.json').write_text(json.dumps({'angle_deg': 12.0, 'measurement_source': 'lamina_center_cobb'}), encoding='utf-8')
    (session_dir / 'derived' / 'assessment' / 'assessment_summary.json').write_text(json.dumps({'confidence': 0.1, 'requires_manual_review': True, 'closure_verdict': 'prior_assisted', 'measurement_source': 'lamina_center_cobb', 'source_contamination_flags': ['registration_prior_curve_used']}), encoding='utf-8')
    (session_dir / 'derived' / 'assessment' / 'uca_measurement.json').write_text(json.dumps({'angle_deg': 10.0}), encoding='utf-8')
    (session_dir / 'derived' / 'assessment' / 'assessment_agreement.json').write_text(json.dumps({'agreement_status': 'divergent'}), encoding='utf-8')
    (session_dir / 'export' / 'session_report.json').write_text(json.dumps({'quality_summary': {}, 'open_issues': []}), encoding='utf-8')

    qa_pack = QAPackService().build(session_dir)
    assert qa_pack['training_bridge_model_ready_input_index']['session_id'] == 'S1'
    assert qa_pack['prior_assisted_curve']['measurement_source'] == 'registration_prior_curve'
    assert qa_pack['prior_assisted_cobb']['measurement_source'] == 'lamina_center_cobb'

    reader = _reader_for_session(session_dir)
    assessment = reader.current_assessment()
    assert assessment['curve_candidate']['status'] == 'prior_assisted'
    assert assessment['curve_candidate']['source'] == 'derived/assessment/prior_assisted_cobb.json'

    exporter = SessionExportService()
    payload = exporter.export_lamina_center_case(session_dir, tmp_path / 'dataset')
    case_dir = Path(payload['case_dir'])
    assert (case_dir / 'training_bridge_model_ready_input_index.json').exists()
    assert (case_dir / 'prior_assisted_curve.json').exists()

    payload_uca = exporter.export_uca_case(session_dir, tmp_path / 'dataset')
    case_dir_uca = Path(payload_uca['case_dir'])
    assert (case_dir_uca / 'prior_assisted_cobb.json').exists()
