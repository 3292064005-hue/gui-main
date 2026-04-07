from __future__ import annotations

from math import atan2, degrees
from typing import Any

from spine_ultrasound_ui.utils import now_text


class VertebraTiltService:
    """Estimate coronal vertebra tilt from paired lamina observations."""

    def __init__(self, *, method_version: str = 'vertebra_tilt_v1') -> None:
        self.method_version = method_version

    def estimate(self, vertebra_pairs: dict[str, Any]) -> dict[str, Any]:
        """Estimate tilt candidates from vertebra pairs.

        Args:
            vertebra_pairs: Pair payload emitted by :class:`LaminaPairingService`.

        Returns:
            Tilt-candidate payload suitable for Cobb-style end-vertebra
            selection.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Empty pair payloads produce empty candidate lists and zero summary
            values so measurement services can explicitly select fallback paths.
        """
        pairs = [dict(item) for item in vertebra_pairs.get('pairs', []) if isinstance(item, dict)]
        candidates = []
        for pair in pairs:
            left = dict(pair.get('left', {}))
            right = dict(pair.get('right', {}))
            dx = float(right.get('x_mm', 0.0) or 0.0) - float(left.get('x_mm', 0.0) or 0.0)
            dy = float(right.get('y_mm', 0.0) or 0.0) - float(left.get('y_mm', 0.0) or 0.0)
            angle_deg = round(float(degrees(atan2(dy, dx if abs(dx) > 1e-6 else 1e-6))), 4)
            candidates.append({
                'pair_id': str(pair.get('pair_id', '')),
                'vertebra_id': str(pair.get('vertebra_id', '')),
                'frame_id': str(pair.get('frame_id', '')),
                'segment_id': int(pair.get('segment_id', 0) or 0),
                'tilt_angle_deg': angle_deg,
                'tilt_strength_deg': round(abs(angle_deg), 4),
                'confidence': float(pair.get('pair_confidence', 0.0) or 0.0),
                'center_y_mm': float(pair.get('center_y_mm', 0.0) or 0.0),
            })
        strengths = [float(item.get('tilt_strength_deg', 0.0) or 0.0) for item in candidates]
        return {
            'generated_at': now_text(),
            'method_version': self.method_version,
            'candidates': candidates,
            'summary': {
                'candidate_count': len(candidates),
                'max_tilt_deg': round(max(strengths), 4) if strengths else 0.0,
            },
        }
