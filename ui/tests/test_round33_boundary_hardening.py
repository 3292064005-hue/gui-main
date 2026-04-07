from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from spine_ultrasound_ui.core.postprocess_service import PostprocessService
from spine_ultrasound_ui.services.assessment.assessment_input_builder import AssessmentInputBuilder
from spine_ultrasound_ui.services.reconstruction.reconstruction_input_builder import ReconstructionInputBuilder


def test_assessment_input_builder_tolerates_malformed_curve_sidecar(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'derived' / 'reconstruction').mkdir(parents=True)
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps({'session_id': 'S1', 'experiment_id': 'E1'}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'reconstruction_summary.json').write_text(json.dumps({'closure_verdict': 'prior_assisted'}), encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'spine_curve.json').write_text('{bad json', encoding='utf-8')
    (session_dir / 'derived' / 'reconstruction' / 'prior_assisted_curve.json').write_text('{bad json', encoding='utf-8')

    payload = AssessmentInputBuilder().build(session_dir)
    assert payload['spine_curve'] == {}
    assert payload['spine_curve_source_path'] == 'derived/reconstruction/spine_curve.json'


def test_reconstruction_input_builder_skips_malformed_json_and_jsonl_rows(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'derived' / 'sync').mkdir(parents=True)
    (session_dir / 'derived' / 'quality').mkdir(parents=True)
    (session_dir / 'raw' / 'ultrasound').mkdir(parents=True)
    (session_dir / 'raw' / 'camera').mkdir(parents=True)
    (session_dir / 'raw' / 'pressure').mkdir(parents=True)

    (session_dir / 'meta' / 'manifest.json').write_text('{broken', encoding='utf-8')
    (session_dir / 'meta' / 'patient_registration.json').write_text('{broken', encoding='utf-8')
    (session_dir / 'meta' / 'calibration_bundle.json').write_text('{broken', encoding='utf-8')
    (session_dir / 'derived' / 'sync' / 'frame_sync_index.json').write_text(json.dumps({'rows': []}), encoding='utf-8')
    (session_dir / 'derived' / 'quality' / 'quality_timeline.json').write_text('{broken', encoding='utf-8')
    (session_dir / 'raw' / 'ultrasound' / 'index.jsonl').write_text('{"frame_id": "f1"}\n{bad json\n', encoding='utf-8')
    (session_dir / 'raw' / 'camera' / 'index.jsonl').write_text('{bad json\n', encoding='utf-8')
    (session_dir / 'raw' / 'pressure' / 'samples.jsonl').write_text('\n', encoding='utf-8')

    payload = ReconstructionInputBuilder().build(session_dir)
    assert payload['session_id'] == 'session'
    assert payload['patient_registration'] == {}
    assert payload['calibration_bundle'] == {}
    assert payload['source_counts']['ultrasound_frames'] == 1
    assert payload['source_counts']['camera_frames'] == 0
    assert payload['selection_mode'] in {'blocked_no_authoritative_rows', 'selection_empty'}


def test_postprocess_helpers_tolerate_malformed_json_jsonl_and_npz(tmp_path: Path) -> None:
    bad_json = tmp_path / 'bad.json'
    bad_json.write_text('{broken', encoding='utf-8')
    bad_jsonl = tmp_path / 'bad.jsonl'
    bad_jsonl.write_text('{"ok": 1}\n{broken\n', encoding='utf-8')
    bad_npz = tmp_path / 'bad.npz'
    bad_npz.write_bytes(b'not-a-valid-npz')

    assert PostprocessService._read_json(bad_json) == {}
    assert PostprocessService._read_jsonl(bad_jsonl) == [{'ok': 1}]

    svc = PostprocessService.__new__(PostprocessService)
    bundle = PostprocessService._read_npz_bundle(svc, bad_npz)
    assert bundle['image'].shape == (1, 1)
    assert bundle['slices'] == []
    assert bundle['stats'] == {}
    assert bundle['contributing_frames'] == []
    assert np.asarray(bundle['contribution_map']).shape == (1, 1)
