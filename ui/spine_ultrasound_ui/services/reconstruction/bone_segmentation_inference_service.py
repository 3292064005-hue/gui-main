from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.training.runtime_adapters.segmentation_runtime_adapter import SegmentationRuntimeAdapter
from spine_ultrasound_ui.utils import now_text


class BoneSegmentationInferenceService:
    """Infer bone-like regions from a VPI projection bundle.

    The service now defaults to a packaged deterministic runtime model so the
    runtime no longer hides its execution identity behind an implicit fallback.
    When the package cannot be loaded, the service still returns a deterministic
    fallback result but marks the runtime model as degraded.
    """

    def __init__(
        self,
        *,
        threshold_percentile: float = 72.0,
        method_version: str = 'bone_segmentation_v3',
        runtime_adapter: SegmentationRuntimeAdapter | None = None,
        runtime_model_config: str | Path | None = None,
    ) -> None:
        self.threshold_percentile = float(threshold_percentile)
        self.method_version = method_version
        self.runtime_adapter = runtime_adapter
        self.runtime_model_config = runtime_model_config or os.environ.get(
            'SPINE_LAMINA_SEG_RUNTIME_CONFIG',
            Path(__file__).resolve().parents[3] / 'configs' / 'models' / 'lamina_seg_runtime.yaml',
        )
        self.runtime_load_error = ''
        self._try_load_runtime_adapter()

    def infer(self, projection_bundle: dict[str, Any]) -> dict[str, Any]:
        """Infer a bone-feature segmentation mask.

        Args:
            projection_bundle: VPI bundle from :class:`VPIProjectionBuilder`.

        Returns:
            Dictionary containing the float mask, binary mask, statistics, and
            runtime-model identity.

        Raises:
            ValueError: Raised when the bundle does not contain a valid image.

        Boundary behaviour:
            Zero-valued images return empty masks with zero confidence, allowing
            downstream reconstruction to degrade deterministically.
        """
        image = np.asarray(projection_bundle.get('image'))
        if image.ndim != 2:
            raise ValueError('projection_bundle.image must be a 2D array')
        if self.runtime_adapter is not None and self.runtime_adapter.is_loaded:
            payload = self.runtime_adapter.infer({'image': image})
            return {
                'generated_at': now_text(),
                'session_id': str(projection_bundle.get('session_id', '') or ''),
                'method_version': self.method_version,
                'mask': np.asarray(payload.get('mask', np.zeros_like(image, dtype=np.float32)), dtype=np.float32),
                'binary_mask': np.asarray(payload.get('binary_mask', np.zeros_like(image, dtype=np.uint8)), dtype=np.uint8),
                'summary': dict(payload.get('summary', {})),
                'runtime_model': dict(payload.get('runtime_model', {})),
            }
        if image.size == 0 or float(image.max(initial=0.0)) <= 0.0:
            mask = np.zeros_like(image, dtype=np.float32)
            binary = np.zeros_like(image, dtype=np.uint8)
        else:
            threshold = float(np.percentile(image, self.threshold_percentile))
            mask = np.clip((image - threshold) / max(1e-6, 1.0 - threshold), 0.0, 1.0).astype(np.float32)
            binary = (mask > 0.15).astype(np.uint8)
        return {
            'generated_at': now_text(),
            'session_id': str(projection_bundle.get('session_id', '') or ''),
            'method_version': self.method_version,
            'mask': mask,
            'binary_mask': binary,
            'summary': {
                'coverage_ratio': round(float(binary.mean()) if binary.size else 0.0, 6),
                'peak_score': round(float(mask.max()) if mask.size else 0.0, 6),
            },
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
            'package_name': 'bone_segmentation_inline_fallback',
            'backend': 'inline_fallback',
            'runtime_kind': 'deterministic_fallback',
            'release_state': 'degraded',
            'load_error': self.runtime_load_error,
        }
