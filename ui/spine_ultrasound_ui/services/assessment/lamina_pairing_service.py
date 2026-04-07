from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.utils import now_text


class LaminaPairingService:
    """Pair left/right lamina candidates into vertebra-level evidence."""

    def __init__(self, *, method_version: str = 'lamina_pairing_v1') -> None:
        self.method_version = method_version

    def pair(self, lamina_candidates: dict[str, Any]) -> dict[str, Any]:
        """Pair lamina candidates by vertebra identifier.

        Args:
            lamina_candidates: Candidate payload from reconstruction.

        Returns:
            Pair payload containing left/right lamina evidence per vertebra.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Candidates lacking either left or right observations are ignored so
            downstream measurement can explicitly fall back instead of operating
            on malformed pairs.
        """
        candidates = [dict(item) for item in lamina_candidates.get('candidates', []) if isinstance(item, dict)]
        grouped: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            grouped.setdefault(str(candidate.get('vertebra_id', '')), {})[str(candidate.get('side', ''))] = candidate
        pairs = []
        for vertebra_id in sorted(grouped):
            pair = grouped[vertebra_id]
            if 'left' not in pair or 'right' not in pair:
                continue
            left = pair['left']
            right = pair['right']
            pairs.append({
                'pair_id': f'{vertebra_id}_pair',
                'vertebra_id': vertebra_id,
                'segment_id': int(left.get('segment_id', right.get('segment_id', 0)) or 0),
                'frame_id': str(left.get('frame_id', right.get('frame_id', ''))),
                'left': left,
                'right': right,
                'center_x_mm': round((float(left.get('x_mm', 0.0)) + float(right.get('x_mm', 0.0))) / 2.0, 3),
                'center_y_mm': round((float(left.get('y_mm', 0.0)) + float(right.get('y_mm', 0.0))) / 2.0, 3),
                'center_z_mm': round((float(left.get('z_mm', 0.0)) + float(right.get('z_mm', 0.0))) / 2.0, 3),
                'pair_confidence': round((float(left.get('confidence', 0.0)) + float(right.get('confidence', 0.0))) / 2.0, 4),
            })
        confidences = [float(item.get('pair_confidence', 0.0) or 0.0) for item in pairs]
        return {
            'generated_at': now_text(),
            'method_version': self.method_version,
            'pairs': pairs,
            'summary': {
                'pair_count': len(pairs),
                'avg_pair_confidence': round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
            },
        }
