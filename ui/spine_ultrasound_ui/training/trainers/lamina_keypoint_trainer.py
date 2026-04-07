from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.training.datasets.lamina_center_dataset import LaminaCenterDataset
from spine_ultrasound_ui.training.specs.lamina_center_training_spec import LaminaCenterTrainingSpec
from spine_ultrasound_ui.training.trainers.backend_adapters import build_monai_keypoint_request
from spine_ultrasound_ui.utils import ensure_dir, now_text


class LaminaKeypointTrainer:
    """Train or stage a lamina-keypoint backend."""

    def train(self, spec: LaminaCenterTrainingSpec) -> dict[str, Any]:
        """Train or stage the requested keypoint backend.

        Args:
            spec: Lamina-center training specification.

        Returns:
            Learned keypoint parameters or a MONAI training request.

        Raises:
            ValueError: Raised when the dataset lacks paired annotations.

        Boundary behaviour:
            Only MONAI-backed requests are exposed for the heavyweight path. When
            the backend is ``numpy_baseline`` a deterministic package is learned.
        """
        spec.validate()
        dataset = LaminaCenterDataset(spec.dataset_root, spec.split_file, spec.split_name, require_annotations=True)
        if len(dataset) == 0:
            raise ValueError('lamina keypoint training requires at least one annotated case')
        if spec.trainer_backend == 'monai':
            return build_monai_keypoint_request(spec, dataset)
        if spec.trainer_backend != 'numpy_baseline':
            raise ValueError(f'lamina keypoint trainer does not support backend {spec.trainer_backend!r}')
        separations_mm: list[float] = []
        visibility_scores: list[float] = []
        for sample in dataset:
            by_vertebra: dict[str, dict[str, dict[str, Any]]] = {}
            for point in sample['lamina_points'].get('points', []):
                if not isinstance(point, dict):
                    continue
                by_vertebra.setdefault(str(point.get('vertebra_instance_id', 'unknown')), {})[str(point.get('side', ''))] = point
                visibility = str(point.get('visibility', 'clear') or 'clear')
                visibility_scores.append(1.0 if visibility == 'clear' else 0.6 if visibility == 'partial' else 0.25)
            for points in by_vertebra.values():
                if 'left' in points and 'right' in points:
                    separations_mm.append(abs(float(points['right'].get('x_mm', 0.0) or 0.0) - float(points['left'].get('x_mm', 0.0) or 0.0)))
        if not separations_mm:
            raise ValueError('lamina keypoint training requires left/right lamina pairs')
        learned = {
            'avg_lamina_separation_mm': round(float(np.mean(separations_mm)), 6),
            'min_confidence': round(float(np.mean(visibility_scores) if visibility_scores else 0.5), 6),
            'candidate_window_px': 12,
        }
        metrics = {
            'sample_count': len(dataset),
            'pair_count': len(separations_mm),
            'avg_visibility_score': round(float(np.mean(visibility_scores) if visibility_scores else 0.0), 6),
        }
        ensure_dir(spec.output_dir)
        target = spec.output_dir / f'{spec.task_name}_keypoint_training_result.json'
        payload = {
            'generated_at': now_text(),
            'task_name': spec.task_name,
            'trainer_backend': spec.trainer_backend,
            'learned_parameters': learned,
            'metrics': metrics,
            'spec': spec.to_dict(),
        }
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        return payload

    def validate(self, spec: LaminaCenterTrainingSpec) -> dict[str, Any]:
        spec.validate()
        dataset = LaminaCenterDataset(spec.dataset_root, spec.split_file, spec.split_name, require_annotations=True)
        if len(dataset) == 0:
            raise ValueError('lamina keypoint validation requires annotated cases')
        counts = [len(sample['lamina_points'].get('points', [])) for sample in dataset]
        return {
            'case_count': len(dataset),
            'min_point_count': min(counts),
            'max_point_count': max(counts),
        }
