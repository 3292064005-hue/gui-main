from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.services.assessment.assessment_artifact_writer import AssessmentArtifactWriter
from spine_ultrasound_ui.services.assessment.assessment_input_builder import AssessmentInputBuilder
from spine_ultrasound_ui.services.benchmark.assessment_benchmark_service import AssessmentBenchmarkService
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.qa_pack_service import QAPackService
from spine_ultrasound_ui.services.reconstruction.closure_profile import load_reconstruction_profile
from spine_ultrasound_ui.services.reconstruction.reconstruction_artifact_writer import ReconstructionArtifactWriter
from spine_ultrasound_ui.services.datasets.session_export_service import SessionExportService


class _FakeExpManager:
    def save_json_artifact(self, session_dir: Path, relative_path: str, payload: dict) -> Path:
        target = session_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return target


class _BrokenSignal:
    def disconnect(self, _callback) -> None:
        raise RuntimeError('disconnect failed')


class _BrokenTimer:
    def __init__(self) -> None:
        self.timeout = _BrokenSignal()
        self.stopped = False

    def isActive(self) -> bool:
        return True

    def stop(self) -> None:
        self.stopped = True


def test_invalid_profile_config_surfaces_load_error(tmp_path: Path) -> None:
    invalid = tmp_path / 'broken.json'
    invalid.write_text('{"profile_name": ', encoding='utf-8')
    profile = load_reconstruction_profile(str(invalid))
    assert profile['profile_name'] == 'weighted_runtime'
    assert profile['closure_mode'] == 'runtime_optional'
    assert profile['profile_config_path'].endswith('broken.json')
    assert profile['profile_load_error']


def test_reconstruction_writer_sanitizes_canonical_curve_and_assessment_reads_sidecar(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    session_dir.mkdir(parents=True)
    writer = ReconstructionArtifactWriter(_FakeExpManager())
    writer.write(
        session_dir,
        input_index={'model_ready_input_index': {}, 'session_id': 'S1'},
        coronal_vpi={'image': [[0.0]], 'stats': {}, 'slices': [], 'row_geometry': [], 'contributing_frames': [], 'contribution_map': [[0.0]], 'preview_rgb': __import__('numpy').zeros((8, 8, 3), dtype=__import__('numpy').uint8)},
        frame_anatomy_points={},
        bone_mask={'mask': [[0.0]], 'binary_mask': [[0]], 'summary': {}, 'runtime_model': {}},
        lamina_candidates={},
        pose_series={},
        reconstruction_evidence={},
        spine_curve={'generated_at': 'now', 'session_id': 'S1', 'method_version': 'm', 'coordinate_frame': 'patient_surface', 'points': [{'x_mm': 1.0}], 'fit': {}, 'evidence_refs': [{'frame_id': 'f1'}], 'measurement_source': 'registration_prior_curve'},
        landmark_track={},
        summary={'generated_at': 'now', 'session_id': 'S1', 'method_version': 'm', 'coordinate_frame': 'patient_surface', 'closure_verdict': 'prior_assisted', 'source_contamination_flags': ['registration_prior_curve_used'], 'runtime_profile': 'weighted_runtime'},
        prior_assisted_curve={'generated_at': 'now', 'session_id': 'S1', 'method_version': 'm', 'coordinate_frame': 'patient_surface', 'points': [{'x_mm': 1.0}], 'fit': {}, 'evidence_refs': [{'frame_id': 'f1'}], 'measurement_source': 'registration_prior_curve'},
    )
    (session_dir / 'meta').mkdir(exist_ok=True)
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps({'session_id': 'S1', 'experiment_id': 'E1'}), encoding='utf-8')
    (session_dir / 'meta' / 'patient_registration.json').write_text(json.dumps({}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'lamina_candidates.json').write_text(json.dumps({}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'landmark_track.json').write_text(json.dumps({}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'reconstruction_evidence.json').write_text(json.dumps({}), encoding='utf-8')

    bundle_path = session_dir / 'derived' / 'reconstruction' / 'reconstruction_volume_bundle.npz'
    assert bundle_path.exists()
    model_ready = json.loads((session_dir / 'derived' / 'reconstruction' / 'model_ready_input_index.json').read_text(encoding='utf-8'))
    assert model_ready['reconstruction_volume_bundle_ref'].endswith('reconstruction_volume_bundle.npz')
    assert model_ready['volume_reconstruction_ref'].endswith('reconstruction_volume_bundle.npz')

    canonical = json.loads((session_dir / 'derived' / 'reconstruction' / 'spine_curve.json').read_text(encoding='utf-8'))
    assert canonical['measurement_source'] == 'authoritative_curve_unavailable'
    assert canonical['authoritative_available'] is False
    assert canonical['sidecar_ref'] == 'derived/reconstruction/prior_assisted_curve.json'

    built = AssessmentInputBuilder().build(session_dir)
    assert built['spine_curve_source_path'] == 'derived/reconstruction/prior_assisted_curve.json'
    assert built['spine_curve']['measurement_source'] == 'registration_prior_curve'


def test_assessment_writer_sanitizes_canonical_measurement_and_benchmark_uses_sidecar(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'derived' / 'assessment').mkdir(parents=True)
    writer = AssessmentArtifactWriter(_FakeExpManager())
    writer.write(
        session_dir,
        cobb_measurement={'generated_at': 'now', 'session_id': 'S1', 'experiment_id': 'E1', 'method_version': 'm', 'coordinate_frame': 'patient_surface', 'angle_deg': 18.0, 'confidence': 0.3, 'requires_manual_review': True, 'upper_line': {}, 'lower_line': {}, 'evidence_refs': [], 'measurement_source': 'curve_window_fallback', 'closure_verdict': 'prior_assisted'},
        assessment_summary={'generated_at': 'now', 'session_id': 'S1', 'experiment_id': 'E1', 'method_version': 'm', 'coordinate_frame': 'patient_surface', 'cobb_angle_deg': 18.0, 'confidence': 0.3, 'requires_manual_review': True, 'measurement_source': 'curve_window_fallback', 'closure_verdict': 'prior_assisted', 'source_contamination_flags': ['curve_window_fallback_used']},
        prior_assisted_cobb={'generated_at': 'now', 'session_id': 'S1', 'experiment_id': 'E1', 'method_version': 'm', 'coordinate_frame': 'patient_surface', 'angle_deg': 18.0, 'confidence': 0.3, 'requires_manual_review': True, 'upper_line': {}, 'lower_line': {}, 'evidence_refs': [], 'measurement_source': 'curve_window_fallback'},
    )
    (session_dir / 'derived' / 'assessment' / 'ground_truth_cobb.json').write_text(json.dumps({'angle_deg': 20.0}), encoding='utf-8')
    canonical = json.loads((session_dir / 'derived' / 'assessment' / 'cobb_measurement.json').read_text(encoding='utf-8'))
    assert canonical['measurement_source'] == 'authoritative_measurement_unavailable'
    assert canonical['authoritative_available'] is False
    bench = AssessmentBenchmarkService().evaluate_case(session_dir=session_dir)
    assert bench['measurement_source'] == 'curve_window_fallback'
    assert bench['measured_angle_deg'] == 18.0
    assert bench['absolute_error_deg'] == 2.0


def test_mock_backend_close_tolerates_disconnect_failure() -> None:
    dummy = type('DummyBackend', (), {'_tick': staticmethod(lambda: None)})()
    dummy.timer = _BrokenTimer()
    MockBackend.close(dummy)  # type: ignore[misc]
    assert dummy.timer.stopped is True


def test_qa_pack_and_export_tolerate_malformed_optional_artifacts(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'derived' / 'reconstruction').mkdir(parents=True)
    (session_dir / 'export').mkdir(parents=True)
    (session_dir / 'meta' / 'manifest.json').write_text('{bad json', encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'reconstruction_input_index.json').write_text('{bad json', encoding='utf-8')
    qa = QAPackService().build(session_dir)
    assert qa['manifest'] == {}
    assert qa['reconstruction_input_index'] == {}

    exporter = SessionExportService()
    (session_dir / 'meta' / 'patient_registration.json').write_text(json.dumps({'patient_id': 'P1'}), encoding='utf-8')
    payload = exporter.export_lamina_center_case(session_dir, tmp_path / 'dataset')
    case_dir = Path(payload['case_dir'])
    exported_meta = json.loads((case_dir / 'meta.json').read_text(encoding='utf-8'))
    assert exported_meta['dataset_role'] == 'lamina_center'
