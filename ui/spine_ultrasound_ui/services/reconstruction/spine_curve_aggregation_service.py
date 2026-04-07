from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.services.reconstruction.closure_profile import is_preweight_profile, load_reconstruction_profile, profile_name
from spine_ultrasound_ui.utils import now_text


class SpineCurveAggregationService:
    """Aggregate lamina-center candidates into an authoritative spine curve."""

    def __init__(self, *, method_version: str = 'spine_curve_aggregation_v2') -> None:
        self.method_version = method_version
        self.profile = load_reconstruction_profile()

    def aggregate(self, lamina_candidates: dict[str, Any], registration: dict[str, Any]) -> dict[str, Any]:
        """Aggregate paired lamina centers into a centerline curve.

        Args:
            lamina_candidates: Candidate payload produced by the lamina
                inference service.
            registration: Patient registration payload containing optional
                anatomical priors.

        Returns:
            Dictionary containing spine-curve points and landmark track.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            If no paired laminae are available, the method falls back to the
            registration midline polyline when available. The summary marks this
            as a degraded ``registration_prior_curve`` source instead of
            blending the prior into a measured curve.
        """
        candidates = [dict(item) for item in lamina_candidates.get('candidates', []) if isinstance(item, dict)]
        grouped: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            grouped.setdefault(str(candidate.get('vertebra_id', '')), {})[str(candidate.get('side', ''))] = candidate
        points: list[dict[str, Any]] = []
        landmarks: list[dict[str, Any]] = []
        for vertebra_id in sorted(grouped):
            pair = grouped[vertebra_id]
            if 'left' not in pair or 'right' not in pair:
                continue
            left = pair['left']
            right = pair['right']
            midpoint = {
                'curve_id': vertebra_id,
                'frame_id': str(left.get('frame_id', right.get('frame_id', ''))),
                'segment_id': int(left.get('segment_id', right.get('segment_id', 0)) or 0),
                'x_mm': round((float(left.get('x_mm', 0.0)) + float(right.get('x_mm', 0.0))) / 2.0, 3),
                'y_mm': round((float(left.get('y_mm', 0.0)) + float(right.get('y_mm', 0.0))) / 2.0, 3),
                'z_mm': round((float(left.get('z_mm', 0.0)) + float(right.get('z_mm', 0.0))) / 2.0, 3),
                'confidence': round((float(left.get('confidence', 0.0)) + float(right.get('confidence', 0.0))) / 2.0, 4),
            }
            points.append(midpoint)
            landmarks.extend([
                {
                    'name': f'{vertebra_id}_left_lamina',
                    'frame_id': str(left.get('frame_id', '')),
                    'segment_id': int(left.get('segment_id', 0) or 0),
                    'x_mm': float(left.get('x_mm', 0.0) or 0.0),
                    'y_mm': float(left.get('y_mm', 0.0) or 0.0),
                    'z_mm': float(left.get('z_mm', 0.0) or 0.0),
                    'confidence': float(left.get('confidence', 0.0) or 0.0),
                },
                {
                    'name': f'{vertebra_id}_right_lamina',
                    'frame_id': str(right.get('frame_id', '')),
                    'segment_id': int(right.get('segment_id', 0) or 0),
                    'x_mm': float(right.get('x_mm', 0.0) or 0.0),
                    'y_mm': float(right.get('y_mm', 0.0) or 0.0),
                    'z_mm': float(right.get('z_mm', 0.0) or 0.0),
                    'confidence': float(right.get('confidence', 0.0) or 0.0),
                },
            ])
        measurement_source = 'lamina_center_curve'
        manual_review_reasons: list[str] = []
        prior_assisted_curve: dict[str, Any] | None = None
        if not points:
            prior_points = self._registration_prior_points(registration)
            prior_curve_points = [
                {
                    'curve_id': f'prior_{index:04d}',
                    'frame_id': str(point.get('frame_id', f'prior_{index:04d}')),
                    'segment_id': int(point.get('segment_id', index) or index),
                    'x_mm': float(point.get('x_mm', 0.0) or 0.0),
                    'y_mm': float(point.get('y_mm', 0.0) or 0.0),
                    'z_mm': float(point.get('z_mm', 0.0) or 0.0),
                    'confidence': 0.2,
                }
                for index, point in enumerate(prior_points)
            ]
            manual_review_reasons.append('lamina_pairs_unavailable')
            if prior_curve_points:
                manual_review_reasons.append('registration_prior_curve_used')
                prior_assisted_curve = {
                    'generated_at': now_text(),
                    'method_version': self.method_version,
                    'coordinate_frame': 'patient_surface',
                    'measurement_source': 'registration_prior_curve',
                    'runtime_profile': profile_name(self.profile),
                    'points': prior_curve_points,
                    'evidence_refs': [{'frame_id': item.get('frame_id', ''), 'segment_id': item.get('segment_id', 0)} for item in prior_curve_points[:24]],
                }
                if not is_preweight_profile(self.profile):
                    points = list(prior_curve_points)
                    measurement_source = 'registration_prior_curve'
            if not points:
                measurement_source = 'blocked_no_measured_curve'
                manual_review_reasons.append('no_curve_points_available')
        points = sorted(points, key=lambda item: (float(item.get('y_mm', 0.0) or 0.0), float(item.get('x_mm', 0.0) or 0.0)))
        confidence_values = [float(item.get('confidence', 0.0) or 0.0) for item in points]
        spine_curve = {
            'generated_at': now_text(),
            'method_version': self.method_version,
            'coordinate_frame': 'patient_surface',
            'measurement_source': measurement_source,
            'runtime_profile': profile_name(self.profile),
            'points': points,
            'evidence_refs': [{'frame_id': item.get('frame_id', ''), 'segment_id': item.get('segment_id', 0)} for item in points[:24]],
        }
        landmark_track = {
            'generated_at': now_text(),
            'method_version': self.method_version,
            'landmarks': landmarks,
        }
        summary = {
            'generated_at': now_text(),
            'method_version': self.method_version,
            'runtime_profile': profile_name(self.profile),
            'point_count': len(points),
            'segment_count': len({int(point.get('segment_id', 0) or 0) for point in points}),
            'confidence': round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
            'measurement_source': spine_curve['measurement_source'],
            'manual_review_reasons': manual_review_reasons,
            'evidence_refs': list(spine_curve['evidence_refs']),
        }
        result = {
            'spine_curve': spine_curve,
            'landmark_track': landmark_track,
            'reconstruction_summary': summary,
        }
        if prior_assisted_curve is not None:
            result['prior_assisted_curve'] = prior_assisted_curve
        return result

    @staticmethod
    def _registration_prior_points(registration: dict[str, Any]) -> list[dict[str, Any]]:
        midline = registration.get('midline_polyline', {})
        if isinstance(midline, dict):
            source = [dict(item) for item in midline.get('points_mm', []) if isinstance(item, dict)]
        elif isinstance(midline, list):
            source = [dict(item) for item in midline if isinstance(item, dict)]
        else:
            source = []
        points: list[dict[str, Any]] = []
        for point in source:
            x_value = point.get('x_mm', point.get('x', 0.0))
            y_value = point.get('y_mm', point.get('y', 0.0))
            z_value = point.get('z_mm', point.get('z', 0.0))
            points.append({'x_mm': float(x_value or 0.0), 'y_mm': float(y_value or 0.0), 'z_mm': float(z_value or 0.0)})
        return points
