from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .common import resolve_model_package


class SegmentationRuntimeAdapter:
    """Runtime adapter for baseline or exported lamina segmentation models."""

    def __init__(self) -> None:
        self._loaded = False
        self._meta: dict[str, Any] = {}
        self._parameters: dict[str, Any] = {}

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, model_dir_or_config: str | Path) -> None:
        payload = resolve_model_package(model_dir_or_config)
        self._meta = dict(payload['meta'])
        self._parameters = dict(payload['parameters'])
        self._loaded = True

    def infer(self, image_bundle: dict[str, Any]) -> dict[str, Any]:
        if not self._loaded:
            raise RuntimeError('segmentation runtime adapter is not loaded')
        image = np.asarray(image_bundle.get('image'), dtype=np.float32)
        if image.ndim != 2:
            raise ValueError('image_bundle.image must be 2D')
        if image.size == 0:
            mask = np.zeros_like(image, dtype=np.float32)
        else:
            low = float(image.min())
            high = float(image.max())
            normalized = np.zeros_like(image, dtype=np.float32) if high <= low else (image - low) / (high - low)
            threshold = float(self._parameters.get('threshold_value', 0.5) or 0.5)
            mask = np.where(normalized >= threshold, normalized, 0.0).astype(np.float32)
        return {
            'mask': mask,
            'binary_mask': (mask > 0.0).astype(np.uint8),
            'summary': {
                'coverage_ratio': round(float(mask.mean()) if mask.size else 0.0, 6),
                'peak_score': round(float(mask.max()) if mask.size else 0.0, 6),
            },
            'runtime_model': dict(self._meta),
        }
