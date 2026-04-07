import json
from pathlib import Path

import numpy as np

from spine_ultrasound_ui.training.datasets.lamina_center_dataset import LaminaCenterDataset
from spine_ultrasound_ui.training.datasets.uca_dataset import UCADataset
from spine_ultrasound_ui.training.specs.lamina_center_training_spec import LaminaCenterTrainingSpec
from spine_ultrasound_ui.training.specs.uca_training_spec import UCATrainingSpec
from spine_ultrasound_ui.training.trainers.lamina_seg_trainer import LaminaSegTrainer
from spine_ultrasound_ui.training.trainers.lamina_keypoint_trainer import LaminaKeypointTrainer
from spine_ultrasound_ui.training.trainers.uca_slice_rank_trainer import UCASliceRankTrainer
from spine_ultrasound_ui.training.backends.monai_runner import build_monai_launch_plan
from spine_ultrasound_ui.training.backends.nnunet_runner import build_nnunet_launch_plan


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def _make_lamina_dataset(root: Path) -> None:
    case_dir = root / 'raw_cases' / 'patient001' / 'session001'
    case_dir.mkdir(parents=True, exist_ok=True)
    image = np.linspace(0.0, 1.0, 64, dtype=np.float32).reshape(8, 8)
    np.savez_compressed(case_dir / 'coronal_vpi.npz', image=image)
    np.savez_compressed(case_dir / 'bone_mask.npz', mask=(image > 0.6).astype(np.float32))
    _write_json(case_dir / 'meta.json', {'patient_id': 'patient001', 'session_id': 'session001', 'dataset_role': 'lamina_center'})
    _write_json(root / 'annotations' / 'lamina_centers' / 'patient001__session001.json', {
        'points': [
            {'point_id': 'p1', 'vertebra_instance_id': 'v1', 'side': 'left', 'x_mm': -40.0, 'y_mm': 20.0, 'z_mm': 0.0, 'visibility': 'clear'},
            {'point_id': 'p2', 'vertebra_instance_id': 'v1', 'side': 'right', 'x_mm': 40.0, 'y_mm': 20.0, 'z_mm': 0.0, 'visibility': 'clear'},
        ],
    })
    _write_json(root / 'annotations' / 'vertebra_pairs' / 'patient001__session001.json', {'pairs': [{'vertebra_instance_id': 'v1'}]})
    _write_json(root / 'splits' / 'split_v1.json', {'train': ['patient001/session001']})


def _make_uca_dataset(root: Path) -> None:
    case_dir = root / 'raw_cases' / 'patient002' / 'session002'
    case_dir.mkdir(parents=True, exist_ok=True)
    image = np.tile(np.linspace(0.1, 0.9, 16, dtype=np.float32), (12, 1))
    np.savez_compressed(case_dir / 'coronal_vpi.npz', image=image)
    _write_json(case_dir / 'meta.json', {'patient_id': 'patient002', 'session_id': 'session002', 'dataset_role': 'uca'})
    _write_json(root / 'annotations' / 'uca_labels' / 'patient002__session002.json', {'best_slice_index': 5, 'uca_angle_deg': 18.2})
    _write_json(root / 'annotations' / 'slice_ranking' / 'patient002__session002.json', {'ranked_slices': [{'slice_index': 5, 'score': 0.9}], 'best_slice': {'slice_index': 5, 'score': 0.9}})
    (root / 'annotations' / 'bone_feature_masks').mkdir(parents=True, exist_ok=True)
    np.savez_compressed(root / 'annotations' / 'bone_feature_masks' / 'patient002__session002.npz', mask=(image > 0.5).astype(np.float32))
    _write_json(root / 'splits' / 'split_v1.json', {'train': ['patient002/session002']})


def test_monai_and_nnunet_backend_requests_are_emitted(tmp_path: Path) -> None:
    lamina_root = tmp_path / 'lamina_center'
    _make_lamina_dataset(lamina_root)
    dataset = LaminaCenterDataset(lamina_root, lamina_root / 'splits' / 'split_v1.json', 'train')
    assert len(dataset) == 1

    monai_spec = LaminaCenterTrainingSpec(
        dataset_root=lamina_root,
        split_file=lamina_root / 'splits' / 'split_v1.json',
        output_dir=tmp_path / 'outputs' / 'lamina_monai',
        trainer_backend='monai',
    )
    monai_seg = LaminaSegTrainer().train(monai_spec)
    assert monai_seg['trainer_backend'] == 'monai'
    assert Path(monai_seg['training_request_path']).exists()
    monai_plan = build_monai_launch_plan(Path(monai_seg['training_request_path']))
    assert monai_plan['trainer_backend'] == 'monai'

    monai_keypoint = LaminaKeypointTrainer().train(monai_spec)
    assert monai_keypoint['trainer_backend'] == 'monai'
    assert Path(monai_keypoint['training_request_path']).exists()

    nnunet_spec = LaminaCenterTrainingSpec(
        dataset_root=lamina_root,
        split_file=lamina_root / 'splits' / 'split_v1.json',
        output_dir=tmp_path / 'outputs' / 'lamina_nnunet',
        trainer_backend='nnunetv2',
        backend_options={'configuration': '2d', 'fold': '0', 'plans': 'nnUNetPlans'},
    )
    nnunet_seg = LaminaSegTrainer().train(nnunet_spec)
    assert nnunet_seg['trainer_backend'] == 'nnunetv2'
    nnunet_plan = build_nnunet_launch_plan(Path(nnunet_seg['training_request_path']))
    assert nnunet_plan['command'][0] == 'nnUNetv2_train'

    uca_root = tmp_path / 'uca'
    _make_uca_dataset(uca_root)
    uca_spec = UCATrainingSpec(
        dataset_root=uca_root,
        split_file=uca_root / 'splits' / 'split_v1.json',
        output_dir=tmp_path / 'outputs' / 'uca_monai',
        trainer_backend='monai',
    )
    uca_request = UCASliceRankTrainer().train(uca_spec)
    assert uca_request['trainer_backend'] == 'monai'
    assert Path(uca_request['training_request_path']).exists()
