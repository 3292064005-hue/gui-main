import json
from pathlib import Path

import numpy as np

from spine_ultrasound_ui.training.exporters.nnunet_dataset_export_service import NnUNetDatasetExportService, NnUNetExportConfig
from spine_ultrasound_ui.training.specs.lamina_center_training_spec import LaminaCenterTrainingSpec
from spine_ultrasound_ui.training.trainers.lamina_seg_trainer import LaminaSegTrainer
from spine_ultrasound_ui.training.backends.nnunet_runner import build_nnunet_launch_plan


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def _make_lamina_dataset(root: Path) -> None:
    case_dir = root / 'raw_cases' / 'patient001' / 'session001'
    case_dir.mkdir(parents=True, exist_ok=True)
    image = np.linspace(0.0, 1.0, 64, dtype=np.float32).reshape(8, 8)
    np.savez_compressed(case_dir / 'coronal_vpi.npz', image=image)
    _write_json(case_dir / 'meta.json', {'patient_id': 'patient001', 'session_id': 'session001', 'dataset_role': 'lamina_center'})
    _write_json(root / 'annotations' / 'lamina_centers' / 'patient001__session001.json', {
        'points': [
            {'point_id': 'p1', 'vertebra_instance_id': 'v1', 'side': 'left', 'x_mm': -30.0, 'y_mm': 20.0, 'z_mm': 0.0, 'visibility': 'clear'},
            {'point_id': 'p2', 'vertebra_instance_id': 'v1', 'side': 'right', 'x_mm': 30.0, 'y_mm': 20.0, 'z_mm': 0.0, 'visibility': 'clear'},
        ]
    })
    _write_json(root / 'annotations' / 'vertebra_pairs' / 'patient001__session001.json', {'pairs': [{'vertebra_instance_id': 'v1'}]})
    _write_json(root / 'splits' / 'split_v1.json', {'train': ['patient001/session001'], 'val': [], 'test': []})


def _make_uca_dataset(root: Path) -> None:
    case_dir = root / 'raw_cases' / 'patient002' / 'session002'
    case_dir.mkdir(parents=True, exist_ok=True)
    image = np.tile(np.linspace(0.1, 0.9, 16, dtype=np.float32), (12, 1))
    np.savez_compressed(case_dir / 'coronal_vpi.npz', image=image)
    _write_json(case_dir / 'meta.json', {'patient_id': 'patient002', 'session_id': 'session002', 'dataset_role': 'uca'})
    (root / 'annotations' / 'bone_feature_masks').mkdir(parents=True, exist_ok=True)
    np.savez_compressed(root / 'annotations' / 'bone_feature_masks' / 'patient002__session002.npz', mask=(image > 0.5).astype(np.float32))
    _write_json(root / 'splits' / 'split_v1.json', {'train': ['patient002/session002'], 'val': [], 'test': []})


def test_nnunet_dataset_export_service_exports_lamina_and_uca(tmp_path: Path) -> None:
    export_service = NnUNetDatasetExportService()
    lamina_root = tmp_path / 'lamina_center'
    _make_lamina_dataset(lamina_root)
    lamina_manifest = export_service.export_lamina_center_dataset(
        lamina_root,
        lamina_root / 'splits' / 'split_v1.json',
        tmp_path / 'nnunet_raw',
        config=NnUNetExportConfig(dataset_id=701, dataset_name='SpineUSLaminaCenter'),
    )
    lamina_dir = Path(lamina_manifest['nnunet_dataset_dir'])
    assert (lamina_dir / 'imagesTr' / 'patient001__session001_0000.png').exists()
    assert (lamina_dir / 'labelsTr' / 'patient001__session001.png').exists()
    dataset_json = json.loads((lamina_dir / 'dataset.json').read_text(encoding='utf-8'))
    assert dataset_json['file_ending'] == '.png'
    assert dataset_json['overwrite_image_reader_writer'] == 'NaturalImage2DIO'

    uca_root = tmp_path / 'uca'
    _make_uca_dataset(uca_root)
    uca_manifest = export_service.export_uca_bone_feature_dataset(
        uca_root,
        uca_root / 'splits' / 'split_v1.json',
        tmp_path / 'nnunet_raw',
        config=NnUNetExportConfig(dataset_id=702, dataset_name='SpineUSUCAFeatures'),
    )
    uca_dir = Path(uca_manifest['nnunet_dataset_dir'])
    assert (uca_dir / 'imagesTr' / 'patient002__session002_0000.png').exists()
    assert (uca_dir / 'labelsTr' / 'patient002__session002.png').exists()


def test_nnunet_training_request_contains_conversion_payload(tmp_path: Path) -> None:
    lamina_root = tmp_path / 'lamina_center'
    _make_lamina_dataset(lamina_root)
    spec = LaminaCenterTrainingSpec(
        dataset_root=lamina_root,
        split_file=lamina_root / 'splits' / 'split_v1.json',
        output_dir=tmp_path / 'outputs',
        trainer_backend='nnunetv2',
        backend_options={'dataset_id': 703, 'dataset_name': 'SpineUSLaminaCenter', 'configuration': '2d', 'fold': '0'},
    )
    request = LaminaSegTrainer().train(spec)
    assert request['trainer_backend'] == 'nnunetv2'
    assert Path(request['backend_payload']['conversion_manifest_path']).exists()
    plan = build_nnunet_launch_plan(Path(request['training_request_path']))
    assert plan['environment']['nnUNet_raw'].endswith('nnunet_raw')
