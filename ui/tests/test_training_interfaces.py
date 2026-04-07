import json
from pathlib import Path

import numpy as np

from spine_ultrasound_ui.services.assessment.vpi_slice_selector_service import VPISliceSelectorService
from spine_ultrasound_ui.services.reconstruction.bone_segmentation_inference_service import BoneSegmentationInferenceService
from spine_ultrasound_ui.services.reconstruction.lamina_center_inference_service import LaminaCenterInferenceService
from spine_ultrasound_ui.training.datasets.lamina_center_dataset import LaminaCenterDataset
from spine_ultrasound_ui.training.datasets.uca_dataset import UCADataset
from spine_ultrasound_ui.training.exporters.model_export_service import ModelExportService
from spine_ultrasound_ui.training.runtime_adapters.keypoint_runtime_adapter import KeypointRuntimeAdapter
from spine_ultrasound_ui.training.runtime_adapters.ranking_runtime_adapter import RankingRuntimeAdapter
from spine_ultrasound_ui.training.runtime_adapters.segmentation_runtime_adapter import SegmentationRuntimeAdapter
from spine_ultrasound_ui.training.specs.lamina_center_training_spec import LaminaCenterTrainingSpec
from spine_ultrasound_ui.training.specs.uca_training_spec import UCATrainingSpec
from spine_ultrasound_ui.training.trainers.lamina_keypoint_trainer import LaminaKeypointTrainer
from spine_ultrasound_ui.training.trainers.lamina_seg_trainer import LaminaSegTrainer
from spine_ultrasound_ui.training.trainers.uca_slice_rank_trainer import UCASliceRankTrainer


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def _make_lamina_dataset(root: Path) -> Path:
    case_dir = root / 'raw_cases' / 'patient001' / 'session001'
    case_dir.mkdir(parents=True, exist_ok=True)
    image = np.linspace(0.0, 1.0, 64, dtype=np.float32).reshape(8, 8)
    np.savez_compressed(case_dir / 'coronal_vpi.npz', image=image)
    np.savez_compressed(case_dir / 'bone_mask.npz', mask=(image > 0.6).astype(np.float32))
    _write_json(case_dir / 'meta.json', {'patient_id': 'patient001', 'session_id': 'session001', 'dataset_role': 'lamina_center'})
    _write_json(root / 'annotations' / 'lamina_centers' / 'patient001__session001.json', {
        'schema_version': '1.0',
        'case_id': 'patient001/session001',
        'patient_id': 'patient001',
        'session_id': 'session001',
        'coordinate_frame': 'coronal_vpi_mm',
        'points': [
            {'point_id': 'p1', 'vertebra_instance_id': 'v1', 'side': 'left', 'x_mm': -40.0, 'y_mm': 20.0, 'z_mm': 0.0, 'visibility': 'clear'},
            {'point_id': 'p2', 'vertebra_instance_id': 'v1', 'side': 'right', 'x_mm': 40.0, 'y_mm': 20.0, 'z_mm': 0.0, 'visibility': 'clear'},
        ],
    })
    _write_json(root / 'annotations' / 'vertebra_pairs' / 'patient001__session001.json', {
        'schema_version': '1.0',
        'case_id': 'patient001/session001',
        'pairs': [{'vertebra_instance_id': 'v1', 'left_point_id': 'p1', 'right_point_id': 'p2', 'pair_confidence': 0.9}],
    })
    _write_json(root / 'splits' / 'split_v1.json', {'train': ['patient001/session001'], 'val': [], 'test': []})
    return case_dir


def _make_uca_dataset(root: Path) -> Path:
    case_dir = root / 'raw_cases' / 'patient002' / 'session002'
    case_dir.mkdir(parents=True, exist_ok=True)
    image = np.tile(np.linspace(0.1, 0.9, 16, dtype=np.float32), (12, 1))
    np.savez_compressed(case_dir / 'coronal_vpi.npz', image=image)
    _write_json(case_dir / 'meta.json', {'patient_id': 'patient002', 'session_id': 'session002', 'dataset_role': 'uca'})
    _write_json(root / 'annotations' / 'uca_labels' / 'patient002__session002.json', {
        'schema_version': '1.0', 'case_id': 'patient002/session002', 'best_slice_index': 5, 'uca_angle_deg': 18.2
    })
    _write_json(root / 'annotations' / 'slice_ranking' / 'patient002__session002.json', {
        'ranked_slices': [{'slice_index': 5, 'score': 0.9}, {'slice_index': 4, 'score': 0.8}], 'best_slice': {'slice_index': 5, 'score': 0.9}
    })
    (root / 'annotations' / 'bone_feature_masks').mkdir(parents=True, exist_ok=True)
    np.savez_compressed(root / 'annotations' / 'bone_feature_masks' / 'patient002__session002.npz', mask=(image > 0.5).astype(np.float32))
    _write_json(root / 'splits' / 'split_v1.json', {'train': ['patient002/session002'], 'val': [], 'test': []})
    return case_dir


def test_training_interfaces_export_packages_and_runtime_adapters(tmp_path: Path) -> None:
    lamina_root = tmp_path / 'datasets' / 'lamina_center'
    _make_lamina_dataset(lamina_root)
    lamina_dataset = LaminaCenterDataset(lamina_root, lamina_root / 'splits' / 'split_v1.json', 'train')
    assert len(lamina_dataset) == 1

    lamina_spec = LaminaCenterTrainingSpec(
        dataset_root=lamina_root,
        split_file=lamina_root / 'splits' / 'split_v1.json',
        output_dir=tmp_path / 'training_outputs' / 'lamina_center',
    )
    seg_result = LaminaSegTrainer().train(lamina_spec)
    keypoint_result = LaminaKeypointTrainer().train(lamina_spec)

    exporter = ModelExportService()
    seg_package = exporter.export_segmentation_model(seg_result, tmp_path / 'models')
    keypoint_package = exporter.export_keypoint_model(keypoint_result, tmp_path / 'models')

    seg_adapter = SegmentationRuntimeAdapter()
    seg_adapter.load(seg_package['package_dir'])
    image = lamina_dataset[0]['image']
    seg_payload = seg_adapter.infer({'image': image})
    assert seg_payload['binary_mask'].shape == image.shape

    keypoint_adapter = KeypointRuntimeAdapter()
    keypoint_adapter.load(keypoint_package['package_dir'])
    keypoint_payload = keypoint_adapter.infer({'image': image}, {'binary_mask': seg_payload['binary_mask']})
    assert keypoint_payload['summary']['row_count'] == image.shape[0]

    seg_service = BoneSegmentationInferenceService(runtime_adapter=seg_adapter)
    seg_service_payload = seg_service.infer({'image': image, 'session_id': 'session001'})
    assert 'runtime_model' in seg_service_payload

    keypoint_service = LaminaCenterInferenceService(runtime_adapter=keypoint_adapter)
    input_index = {'selected_rows': [{'frame_id': 'f1', 'segment_id': 1, 'progress_pct': 10.0, 'pressure_current': 2.0}] * image.shape[0]}
    candidate_payload = keypoint_service.infer({'image': image, 'session_id': 'session001'}, seg_service_payload, input_index)
    assert candidate_payload['summary']['candidate_count'] >= 2

    uca_root = tmp_path / 'datasets' / 'uca'
    _make_uca_dataset(uca_root)
    uca_dataset = UCADataset(uca_root, uca_root / 'splits' / 'split_v1.json', 'train')
    assert len(uca_dataset) == 1
    uca_spec = UCATrainingSpec(
        dataset_root=uca_root,
        split_file=uca_root / 'splits' / 'split_v1.json',
        output_dir=tmp_path / 'training_outputs' / 'uca',
    )
    rank_result = UCASliceRankTrainer().train(uca_spec)
    rank_package = exporter.export_ranking_model(rank_result, tmp_path / 'models')
    rank_adapter = RankingRuntimeAdapter()
    rank_adapter.load(rank_package['package_dir'])
    selector = VPISliceSelectorService(runtime_adapter=rank_adapter)
    ranked = selector.rank({'image': uca_dataset[0]['slice_stack'], 'session_id': 'session002', 'slices': [
        {'slice_index': 0, 'score': 0.1, 'peak_intensity': 0.2},
        {'slice_index': 5, 'score': 0.9, 'peak_intensity': 0.8},
    ]})
    assert ranked['best_slice']['slice_index'] == 5
