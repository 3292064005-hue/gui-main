import json
from pathlib import Path

import numpy as np

from tools.monai_label_app.config import MonaiLabelAppConfig
from tools.monai_label_app.server_app import SpineUltrasoundMonaiLabelServerApp


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def _make_lamina_case(root: Path) -> str:
    case_dir = root / 'raw_cases' / 'patient001' / 'session001'
    case_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(case_dir / 'coronal_vpi.npz', image=np.ones((8, 8), dtype=np.float32))
    _write_json(case_dir / 'lamina_candidates.json', {
        'candidates': [
            {'candidate_id': 'p1', 'vertebra_id': 'v1', 'side': 'left', 'x_mm': -30.0, 'y_mm': 20.0, 'z_mm': 0.0, 'confidence': 0.8},
            {'candidate_id': 'p2', 'vertebra_id': 'v1', 'side': 'right', 'x_mm': 30.0, 'y_mm': 20.0, 'z_mm': 0.0, 'confidence': 0.8},
        ]
    })
    _write_json(case_dir / 'meta.json', {'patient_id': 'patient001', 'session_id': 'session001', 'dataset_role': 'lamina_center'})
    _write_json(root / 'splits' / 'split_v1.json', {'train': ['patient001/session001'], 'val': [], 'test': []})
    return 'patient001/session001'


def _make_uca_case(root: Path) -> str:
    case_dir = root / 'raw_cases' / 'patient002' / 'session002'
    case_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(case_dir / 'coronal_vpi.npz', image=np.ones((12, 16), dtype=np.float32))
    _write_json(case_dir / 'ranked_slice_candidates.json', {
        'best_slice': {'slice_index': 5, 'score': 0.91},
        'ranked_slices': [{'slice_index': 5, 'score': 0.91}, {'slice_index': 4, 'score': 0.82}],
    })
    _write_json(case_dir / 'uca_measurement.json', {'angle_deg': 18.2, 'requires_manual_review': False})
    _write_json(case_dir / 'meta.json', {'patient_id': 'patient002', 'session_id': 'session002', 'dataset_role': 'uca'})
    _write_json(root / 'splits' / 'split_v1.json', {'train': ['patient002/session002'], 'val': [], 'test': []})
    return 'patient002/session002'


def test_monai_label_server_tasks_infer_and_save(tmp_path: Path) -> None:
    lamina_root = tmp_path / 'lamina_center'
    lamina_case = _make_lamina_case(lamina_root)
    app = SpineUltrasoundMonaiLabelServerApp(MonaiLabelAppConfig(dataset_root=lamina_root, task_names=['lamina_center']))
    desc = app.build_server_descriptor()
    assert 'lamina_center' in desc['server_tasks']['infer']

    task = app.registry.infer_tasks['lamina_center']
    inferred = task.infer(lamina_case)
    assert inferred.payload['source'] == 'reconstruction_candidates'
    assert len(inferred.payload['lamina_centers']['points']) == 2

    saved = task.save_annotation(lamina_case, inferred.payload)
    assert saved.payload['saved'] is True
    points_path = Path(saved.payload['lamina_centers_path'])
    assert points_path.exists()

    second = task.infer(lamina_case)
    assert second.payload['source'] == 'existing_annotation'


def test_monai_label_server_tasks_uca_and_train_request(tmp_path: Path) -> None:
    uca_root = tmp_path / 'uca'
    uca_case = _make_uca_case(uca_root)
    app = SpineUltrasoundMonaiLabelServerApp(MonaiLabelAppConfig(dataset_root=uca_root, task_names=['uca_auxiliary']))
    task = app.registry.infer_tasks['uca_auxiliary']
    inferred = task.infer(uca_case)
    assert inferred.payload['uca_labels']['best_slice_index'] == 5
    saved = task.save_annotation(uca_case, inferred.payload)
    assert Path(saved.payload['uca_label_path']).exists()
    train_request = task.train_request(tmp_path / 'train_out', backend='monai')
    assert train_request.payload['trainer_backend'] == 'monai'
    assert Path(train_request.payload['training_request_path']).exists()
