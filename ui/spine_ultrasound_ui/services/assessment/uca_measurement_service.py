from __future__ import annotations

from math import atan, degrees
from typing import Any

import numpy as np

from spine_ultrasound_ui.utils import now_text


class UCAMeasurementService:
    """Compute an auxiliary ultrasound curvature angle (UCA) measurement."""

    def __init__(self, *, min_pixels: int = 6, method_version: str = 'uca_measurement_v1') -> None:
        self.min_pixels = int(min_pixels)
        self.method_version = method_version

    def measure(self, assessment_input: dict[str, Any], ranked_slices: dict[str, Any], bone_feature_mask: dict[str, Any]) -> dict[str, Any]:
        """Measure an auxiliary-UCA value from ranked VPI slices.

        Args:
            assessment_input: Normalized assessment input payload.
            ranked_slices: Ranked slice payload.
            bone_feature_mask: Bone-feature segmentation payload.

        Returns:
            Auxiliary-UCA measurement payload.

        Raises:
            ValueError: Raised when the bone-feature mask is malformed.

        Boundary behaviour:
            Sparse masks return zero-angle measurements with
            ``requires_manual_review=True``.
        """
        mask = np.asarray(bone_feature_mask.get('mask'))
        if mask.ndim != 2:
            raise ValueError('bone_feature_mask.mask must be 2D')
        ys, xs = np.nonzero(mask > 0)
        if xs.size < self.min_pixels:
            return {
                'generated_at': now_text(),
                'session_id': str(assessment_input.get('session_id', '') or ''),
                'method_version': self.method_version,
                'angle_deg': 0.0,
                'confidence': 0.0,
                'requires_manual_review': True,
                'manual_review_reasons': ['insufficient_bone_feature_pixels'],
                'best_slice': dict(ranked_slices.get('best_slice', {})),
                'measurement_source': 'uca_auxiliary',
                'runtime_model': dict(ranked_slices.get('runtime_model', {})),
            }
        midpoint = len(xs) // 2
        x_upper = xs[:midpoint] if midpoint > 0 else xs
        y_upper = ys[:midpoint] if midpoint > 0 else ys
        x_lower = xs[midpoint:] if midpoint > 0 else xs
        y_lower = ys[midpoint:] if midpoint > 0 else ys
        slope_upper = self._fit_slope(x_upper, y_upper)
        slope_lower = self._fit_slope(x_lower, y_lower)
        angle = abs(degrees(atan(slope_lower)) - degrees(atan(slope_upper)))
        if angle > 90.0:
            angle = 180.0 - angle
        coverage = float(bone_feature_mask.get('summary', {}).get('coverage_ratio', 0.0) or 0.0)
        confidence = round(min(1.0, 0.5 + coverage), 4)
        return {
            'generated_at': now_text(),
            'session_id': str(assessment_input.get('session_id', '') or ''),
            'method_version': self.method_version,
            'angle_deg': round(max(0.0, angle), 4),
            'confidence': confidence,
            'requires_manual_review': confidence < 0.75,
            'manual_review_reasons': [] if confidence >= 0.75 else ['uca_confidence_below_threshold'],
            'best_slice': dict(ranked_slices.get('best_slice', {})),
            'measurement_source': 'uca_auxiliary',
            'runtime_model': dict(ranked_slices.get('runtime_model', {})),
        }

    @staticmethod
    def _fit_slope(xs: np.ndarray, ys: np.ndarray) -> float:
        if xs.size < 2:
            return 0.0
        x_mean = float(xs.mean())
        y_mean = float(ys.mean())
        denominator = float(((xs - x_mean) ** 2).sum())
        if denominator <= 1e-9:
            return 0.0
        numerator = float(((xs - x_mean) * (ys - y_mean)).sum())
        return numerator / denominator
