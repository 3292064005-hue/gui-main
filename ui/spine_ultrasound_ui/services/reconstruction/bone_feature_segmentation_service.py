from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.training.runtime_adapters.segmentation_runtime_adapter import SegmentationRuntimeAdapter
from spine_ultrasound_ui.utils import now_text


class BoneFeatureSegmentationService:
    """Segment lateral bone-like features for auxiliary-UCA measurement."""

    def __init__(
        self,
        *,
        method_version: str = 'bone_feature_segmentation_v3',
        runtime_adapter: SegmentationRuntimeAdapter | None = None,
        runtime_model_config: str | Path | None = None,
    ) -> None:
        self.method_version = method_version
        self.runtime_adapter = runtime_adapter
        self.runtime_model_config = runtime_model_config or os.environ.get(
            'SPINE_UCA_FEATURE_SEG_RUNTIME_CONFIG',
            Path(__file__).resolve().parents[3] / 'configs' / 'models' / 'lamina_seg_runtime.yaml',
        )
        self.runtime_load_error = ''
        self._try_load_runtime_adapter()

    def infer(self, vpi_bundle: dict[str, Any], ranked_slices: dict[str, Any]) -> dict[str, Any]:
        image = np.asarray(vpi_bundle.get('image'))
        if image.ndim != 2:
            raise ValueError('vpi_bundle.image must be 2D')
        if self.runtime_adapter is not None and self.runtime_adapter.is_loaded:
            payload = self.runtime_adapter.infer({'image': image})
            mask = np.asarray(payload.get('binary_mask', np.zeros_like(image, dtype=np.uint8)), dtype=np.uint8)
            return {
                'generated_at': now_text(),
                'session_id': str(vpi_bundle.get('session_id', '') or ''),
                'method_version': self.method_version,
                'mask': mask,
                'summary': dict(payload.get('summary', {})),
                'runtime_model': dict(payload.get('runtime_model', {})),
            }
        mask = np.zeros_like(image, dtype=np.uint8)
        for item in ranked_slices.get('top_k', []):
            start, end = [int(value) for value in item.get('x_range_px', [0, 0])]
            start = max(0, min(start, image.shape[1] - 1))
            end = max(start + 1, min(end + 1, image.shape[1]))
            window = image[:, start:end]
            threshold = float(window.mean() + window.std()) if window.size else 1.0
            mask[:, start:end] = np.where(window >= threshold, 1, mask[:, start:end])
        return {
            'generated_at': now_text(),
            'session_id': str(vpi_bundle.get('session_id', '') or ''),
            'method_version': self.method_version,
            'mask': mask,
            'summary': {'coverage_ratio': round(float(mask.mean()) if mask.size else 0.0, 6)},
            'runtime_model': self._fallback_runtime_model(),
        }

    def _try_load_runtime_adapter(self) -> None:
        if self.runtime_adapter is None and self.runtime_model_config:
            self.runtime_adapter = SegmentationRuntimeAdapter()
        if self.runtime_adapter is None or not self.runtime_model_config:
            return
        config_path = Path(str(self.runtime_model_config))
        if not config_path.exists():
            self.runtime_load_error = f'missing_runtime_model_config:{config_path}'
            return
        try:
            self.runtime_adapter.load(config_path)
        except Exception as exc:  # pragma: no cover - exercised by runtime failures
            self.runtime_load_error = f'{type(exc).__name__}:{exc}'

    def _fallback_runtime_model(self) -> dict[str, Any]:
        return {
            'package_name': 'bone_feature_inline_fallback',
            'backend': 'inline_fallback',
            'runtime_kind': 'deterministic_fallback',
            'release_state': 'degraded',
            'load_error': self.runtime_load_error,
        }
