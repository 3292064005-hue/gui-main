from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.training.datasets.uca_dataset import UCADataset
from spine_ultrasound_ui.training.specs.uca_training_spec import UCATrainingSpec
from spine_ultrasound_ui.training.trainers.backend_adapters import build_monai_uca_rank_request
from spine_ultrasound_ui.utils import ensure_dir, now_text


class UCASliceRankTrainer:
    """Train or stage a UCA slice-ranking backend."""

    def train(self, spec: UCATrainingSpec) -> dict[str, Any]:
        """Train or stage the requested ranking backend.

        Args:
            spec: Auxiliary-UCA training specification.

        Returns:
            Learned ranking parameters or a MONAI training request.

        Raises:
            ValueError: Raised when the dataset lacks UCA labels.

        Boundary behaviour:
            MONAI-backed requests are emitted as launchable manifests while the
            historical deterministic baseline remains available for offline smoke
            tests.
        """
        spec.validate()
        dataset = UCADataset(spec.dataset_root, spec.split_file, spec.split_name, require_annotations=True)
        if len(dataset) == 0:
            raise ValueError('uca ranking training requires at least one annotated case')
        if spec.trainer_backend == 'monai':
            return build_monai_uca_rank_request(spec, dataset)
        if spec.trainer_backend != 'numpy_baseline':
            raise ValueError(f'uca ranking trainer does not support backend {spec.trainer_backend!r}')
        best_indices: list[int] = []
        angles: list[float] = []
        widths: list[int] = []
        for sample in dataset:
            stack = np.asarray(sample['slice_stack'], dtype=np.float32)
            if stack.ndim != 2 or stack.size == 0:
                continue
            widths.append(int(stack.shape[1]))
            best_indices.append(int(sample['best_slice_index']))
            angles.append(float(sample['uca_angle_deg']))
        if not best_indices:
            raise ValueError('uca ranking training requires slice labels')
        learned = {
            'preferred_index_ratio': round(float(np.mean(best_indices)) / max(1.0, float(np.median(widths) if widths else 1.0)), 6),
            'agreement_smoothing': 0.35,
            'score_weights': {'mean_intensity': 0.6, 'peak_intensity': 0.4},
        }
        metrics = {
            'sample_count': len(dataset),
            'avg_best_slice_index': round(float(np.mean(best_indices)), 6),
            'avg_uca_angle_deg': round(float(np.mean(angles)) if angles else 0.0, 6),
        }
        ensure_dir(spec.output_dir)
        target = spec.output_dir / f'{spec.task_name}_ranking_training_result.json'
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

    def validate(self, spec: UCATrainingSpec) -> dict[str, Any]:
        spec.validate()
        dataset = UCADataset(spec.dataset_root, spec.split_file, spec.split_name, require_annotations=True)
        if len(dataset) == 0:
            raise ValueError('uca ranking validation requires annotated cases')
        counts = [int(sample['best_slice_index']) for sample in dataset]
        return {
            'case_count': len(dataset),
            'min_best_slice_index': min(counts),
            'max_best_slice_index': max(counts),
        }
