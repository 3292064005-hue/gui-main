from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.training.datasets.lamina_center_dataset import LaminaCenterDataset
from spine_ultrasound_ui.training.specs.lamina_center_training_spec import LaminaCenterTrainingSpec
from spine_ultrasound_ui.training.trainers.backend_adapters import build_monai_seg_request, build_nnunet_seg_request
from spine_ultrasound_ui.utils import ensure_dir, now_text


class LaminaSegTrainer:
    """Train or stage a lamina segmentation backend.

    The trainer supports three backends:

    * ``numpy_baseline`` for a runtime-safe deterministic baseline;
    * ``monai`` for MONAI-based training requests; and
    * ``nnunetv2`` for nnU-Net based training requests.
    """

    def train(self, spec: LaminaCenterTrainingSpec) -> dict[str, Any]:
        """Train the requested segmentation backend.

        Args:
            spec: Lamina-center training specification.

        Returns:
            Training result containing learned parameters or backend requests.

        Raises:
            ValueError: Raised when the specification or dataset is invalid.

        Boundary behaviour:
            When a heavyweight backend is selected the trainer emits a validated
            training request instead of silently falling back to the deterministic
            baseline. This preserves explicit control over research dependencies.
        """
        spec.validate()
        dataset = LaminaCenterDataset(spec.dataset_root, spec.split_file, spec.split_name, require_annotations=True)
        if len(dataset) == 0:
            raise ValueError('lamina segmentation training requires at least one annotated case')
        if spec.trainer_backend == 'monai':
            return build_monai_seg_request(spec, dataset)
        if spec.trainer_backend == 'nnunetv2':
            return build_nnunet_seg_request(spec, dataset)
        positive_scores: list[float] = []
        negative_scores: list[float] = []
        sample_shapes: list[tuple[int, int]] = []
        for sample in dataset:
            image = np.asarray(sample['image'], dtype=np.float32)
            if image.ndim != 2 or image.size == 0:
                continue
            sample_shapes.append((int(image.shape[0]), int(image.shape[1])))
            normalized = self._normalize_image(image)
            points = self._extract_point_indices(sample['lamina_points'], image.shape)
            if points:
                for row, col in points:
                    positive_scores.append(float(normalized[row, col]))
            else:
                positive_scores.append(float(np.max(normalized)))
            negative_scores.append(float(np.median(normalized)))
        if not positive_scores:
            raise ValueError('lamina segmentation training could not derive positive scores from annotations')
        threshold_value = float(np.clip((np.mean(positive_scores) + np.mean(negative_scores)) / 2.0, 0.05, 0.95))
        learned = {
            'threshold_value': round(threshold_value, 6),
            'post_blur_kernel': 0,
            'normalization_mode': 'per_image_minmax',
        }
        metrics = {
            'sample_count': len(dataset),
            'positive_score_mean': round(float(np.mean(positive_scores)), 6),
            'negative_score_mean': round(float(np.mean(negative_scores)), 6),
            'median_shape': [
                int(np.median([shape[0] for shape in sample_shapes])) if sample_shapes else 0,
                int(np.median([shape[1] for shape in sample_shapes])) if sample_shapes else 0,
            ],
        }
        ensure_dir(spec.output_dir)
        target = spec.output_dir / f'{spec.task_name}_seg_training_result.json'
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
        """Validate dataset readability for segmentation training."""
        spec.validate()
        dataset = LaminaCenterDataset(spec.dataset_root, spec.split_file, spec.split_name, require_annotations=True)
        if len(dataset) == 0:
            raise ValueError('lamina segmentation validation requires annotated cases')
        shapes = [tuple(np.asarray(sample['image']).shape) for sample in dataset]
        return {
            'case_count': len(dataset),
            'min_shape': [min(shape[0] for shape in shapes), min(shape[1] for shape in shapes)],
            'max_shape': [max(shape[0] for shape in shapes), max(shape[1] for shape in shapes)],
        }

    @staticmethod
    def _normalize_image(image: np.ndarray) -> np.ndarray:
        image = np.asarray(image, dtype=np.float32)
        if image.size == 0:
            return image
        low = float(image.min())
        high = float(image.max())
        if high <= low:
            return np.zeros_like(image, dtype=np.float32)
        return (image - low) / (high - low)

    @staticmethod
    def _extract_point_indices(annotation: dict[str, Any], shape: tuple[int, int]) -> list[tuple[int, int]]:
        rows, cols = shape
        result: list[tuple[int, int]] = []
        for point in annotation.get('points', []):
            if not isinstance(point, dict):
                continue
            x_mm = float(point.get('x_mm', 0.0) or 0.0)
            y_mm = float(point.get('y_mm', 0.0) or 0.0)
            col = int(np.clip(round((x_mm + 120.0) / 240.0 * max(1, cols - 1)), 0, cols - 1))
            row = int(np.clip(round((y_mm / 100.0) * max(1, rows - 1)), 0, rows - 1))
            result.append((row, col))
        return result
