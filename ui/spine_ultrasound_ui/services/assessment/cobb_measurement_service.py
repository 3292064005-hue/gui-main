from __future__ import annotations

from math import atan, degrees
from typing import Any

from spine_ultrasound_ui.services.assessment.lamina_pairing_service import LaminaPairingService
from spine_ultrasound_ui.services.reconstruction.closure_profile import is_preweight_profile, load_reconstruction_profile, profile_name
from spine_ultrasound_ui.services.assessment.vertebra_tilt_service import VertebraTiltService
from spine_ultrasound_ui.utils import now_text


class CobbMeasurementService:
    """Measure an authoritative Cobb-style angle from reconstructed evidence."""

    def __init__(
        self,
        *,
        fit_fraction: float = 0.35,
        min_points: int = 4,
        review_confidence_threshold: float = 0.82,
        method_version: str = 'cobb_measurement_v3',
        lamina_pairing_service: LaminaPairingService | None = None,
        vertebra_tilt_service: VertebraTiltService | None = None,
    ) -> None:
        self.fit_fraction = float(fit_fraction)
        self.min_points = int(min_points)
        self.review_confidence_threshold = float(review_confidence_threshold)
        self.method_version = method_version
        self.lamina_pairing_service = lamina_pairing_service or LaminaPairingService()
        self.vertebra_tilt_service = vertebra_tilt_service or VertebraTiltService()
        self.profile = load_reconstruction_profile()
        thresholds = dict(self.profile.get('thresholds', {}) or {})
        self.min_points = int(thresholds.get('min_cobb_curve_points', self.min_points) or self.min_points)

    def measure(self, assessment_input: dict[str, Any]) -> dict[str, Any]:
        """Measure a Cobb-angle candidate from authoritative reconstruction data.

        Args:
            assessment_input: Payload produced by :class:`AssessmentInputBuilder`.

        Returns:
            Structured measurement payload containing the angle, selected
            vertebrae, fit lines, evidence anchors, and failure semantics.

        Raises:
            ValueError: Raised when the session identifier is missing.

        Boundary behaviour:
            If lamina-based measurement is unavailable, the method falls back to
            a curve-window geometric fit and marks the source accordingly so the
            assessment path remains deterministic.
        """
        session_id = str(assessment_input.get('session_id', '') or '')
        if not session_id:
            raise ValueError('assessment_input.session_id is required')
        if self._preweight_blocked(dict(assessment_input.get('reconstruction_summary', {}))):
            return self._blocked_measurement(assessment_input, reason='preweight_closure_blocked')
        vertebra_pairs = self.lamina_pairing_service.pair(dict(assessment_input.get('lamina_candidates', {})))
        tilt_candidates = self.vertebra_tilt_service.estimate(vertebra_pairs)
        lamina_measurement = self._measure_from_lamina(assessment_input, vertebra_pairs, tilt_candidates)
        if lamina_measurement is not None:
            return self._finalize_measurement(lamina_measurement)
        curve_measurement = self._measure_from_curve_window(assessment_input)
        if is_preweight_profile(self.profile):
            return self._blocked_measurement(assessment_input, reason='insufficient_lamina_measurement')
        return self._finalize_measurement(curve_measurement)

    def _measure_from_lamina(
        self,
        assessment_input: dict[str, Any],
        vertebra_pairs: dict[str, Any],
        tilt_candidates: dict[str, Any],
    ) -> dict[str, Any] | None:
        candidates = [dict(item) for item in tilt_candidates.get('candidates', []) if isinstance(item, dict)]
        if len(candidates) < 2:
            return None
        ordered = sorted(candidates, key=lambda item: float(item.get('center_y_mm', 0.0) or 0.0))
        split_index = max(1, len(ordered) // 2)
        upper_pool = ordered[:split_index]
        lower_pool = ordered[split_index:]
        if not upper_pool or not lower_pool:
            return None
        upper = max(upper_pool, key=lambda item: float(item.get('tilt_strength_deg', 0.0) or 0.0))
        lower = max(lower_pool, key=lambda item: float(item.get('tilt_strength_deg', 0.0) or 0.0))
        angle = abs(float(lower.get('tilt_angle_deg', 0.0) or 0.0) - float(upper.get('tilt_angle_deg', 0.0) or 0.0))
        if angle > 90.0:
            angle = 180.0 - angle
        reconstruction_summary = dict(assessment_input.get('reconstruction_summary', {}))
        pair_summary = dict(vertebra_pairs.get('summary', {}))
        confidence = min(
            1.0,
            0.55 * float(reconstruction_summary.get('confidence', 0.0) or 0.0)
            + 0.25 * float(pair_summary.get('avg_pair_confidence', 0.0) or 0.0)
            + 0.20 * min(1.0, len(candidates) / 6.0),
        )
        selected_pairs = {str(upper.get('pair_id', '')), str(lower.get('pair_id', ''))}
        evidence_refs = []
        for pair in vertebra_pairs.get('pairs', []):
            if str(pair.get('pair_id', '')) in selected_pairs:
                evidence_refs.append({
                    'pair_id': str(pair.get('pair_id', '')),
                    'frame_id': str(pair.get('frame_id', '')),
                    'segment_id': int(pair.get('segment_id', 0) or 0),
                })
        manual_review_reasons = list(reconstruction_summary.get('manual_review_reasons', []))
        if confidence < self.review_confidence_threshold:
            manual_review_reasons.append('lamina_measurement_confidence_below_threshold')
        result = {
            'generated_at': now_text(),
            'session_id': str(assessment_input.get('session_id', '') or ''),
            'experiment_id': str(assessment_input.get('experiment_id', '') or ''),
            'method_version': self.method_version,
            'measurement_source': 'lamina_center_cobb',
            'measurement_status': 'authoritative' if not manual_review_reasons else 'degraded',
            'runtime_profile': profile_name(self.profile),
            'profile_release_state': str(self.profile.get('profile_release_state', 'research_validated') or 'research_validated'),
            'closure_mode': str(self.profile.get('closure_mode', 'runtime_optional') or 'runtime_optional'),
            'profile_config_path': str(self.profile.get('profile_config_path', '') or ''),
            'profile_load_error': str(self.profile.get('profile_load_error', '') or ''),
            'coordinate_frame': str(reconstruction_summary.get('coordinate_frame', 'patient_surface') or 'patient_surface'),
            'angle_deg': round(max(0.0, angle), 4),
            'confidence': round(max(0.0, min(1.0, confidence)), 4),
            'requires_manual_review': bool(manual_review_reasons),
            'manual_review_reasons': self._unique_reasons(manual_review_reasons),
            'upper_end_vertebra_candidate': self._candidate_from_tilt('upper', upper),
            'lower_end_vertebra_candidate': self._candidate_from_tilt('lower', lower),
            'upper_line': {'angle_deg': round(float(upper.get('tilt_angle_deg', 0.0) or 0.0), 4)},
            'lower_line': {'angle_deg': round(float(lower.get('tilt_angle_deg', 0.0) or 0.0), 4)},
            'vertebra_pairs': vertebra_pairs.get('pairs', []),
            'tilt_candidates': tilt_candidates.get('candidates', []),
            'evidence_refs': evidence_refs,
            'fit_diagnostics': {
                'pair_count': int(pair_summary.get('pair_count', 0) or 0),
                'candidate_count': len(candidates),
                'reconstruction_confidence': float(reconstruction_summary.get('confidence', 0.0) or 0.0),
                'reconstruction_status': str(reconstruction_summary.get('reconstruction_status', 'unknown') or 'unknown'),
            },
        }
        return result

    def _measure_from_curve_window(self, assessment_input: dict[str, Any]) -> dict[str, Any]:
        spine_curve = dict(assessment_input.get('spine_curve', {}))
        points = [dict(item) for item in spine_curve.get('points', []) if isinstance(item, dict)]
        reconstruction_summary = dict(assessment_input.get('reconstruction_summary', {}))
        evidence_refs = list(reconstruction_summary.get('evidence_refs', spine_curve.get('evidence_refs', [])))
        manual_review_reasons = list(reconstruction_summary.get('manual_review_reasons', []))
        if len(points) < self.min_points:
            manual_review_reasons.append('insufficient_curve_points_for_cobb')
            return {
                'generated_at': now_text(),
                'session_id': str(assessment_input.get('session_id', '') or ''),
                'experiment_id': str(assessment_input.get('experiment_id', '') or ''),
                'method_version': self.method_version,
                'measurement_source': 'curve_window_fallback',
                'measurement_status': 'degraded',
                'runtime_profile': profile_name(self.profile),
                'profile_release_state': str(self.profile.get('profile_release_state', 'research_validated') or 'research_validated'),
                'closure_mode': str(self.profile.get('closure_mode', 'runtime_optional') or 'runtime_optional'),
                'profile_config_path': str(self.profile.get('profile_config_path', '') or ''),
                'profile_load_error': str(self.profile.get('profile_load_error', '') or ''),
                'coordinate_frame': str(spine_curve.get('coordinate_frame', 'patient_surface') or 'patient_surface'),
                'angle_deg': 0.0,
                'confidence': 0.0,
                'requires_manual_review': True,
                'manual_review_reasons': self._unique_reasons(manual_review_reasons),
                'upper_end_vertebra_candidate': {},
                'lower_end_vertebra_candidate': {},
                'upper_line': {},
                'lower_line': {},
                'vertebra_pairs': [],
                'tilt_candidates': [],
                'evidence_refs': evidence_refs,
                'fit_diagnostics': {'point_count': len(points), 'reason': 'insufficient_points'},
            }
        fit_count = max(2, min(len(points) - 1, int(round(len(points) * self.fit_fraction))))
        upper_points = points[:fit_count]
        lower_points = points[-fit_count:]
        upper_line = self._fit_line(upper_points)
        lower_line = self._fit_line(lower_points)
        upper_angle = degrees(atan(upper_line['slope']))
        lower_angle = degrees(atan(lower_line['slope']))
        raw_angle = abs(lower_angle - upper_angle)
        if raw_angle > 90.0:
            raw_angle = 180.0 - raw_angle
        angle_deg = round(max(0.0, raw_angle), 4)
        confidence = self._confidence(
            reconstruction_summary=reconstruction_summary,
            upper_line=upper_line,
            lower_line=lower_line,
            point_count=len(points),
        )
        if confidence < self.review_confidence_threshold:
            manual_review_reasons.append('curve_window_confidence_below_threshold')
        manual_review_reasons.append('curve_window_fallback_used')
        return {
            'generated_at': now_text(),
            'session_id': str(assessment_input.get('session_id', '') or ''),
            'experiment_id': str(assessment_input.get('experiment_id', '') or ''),
            'method_version': self.method_version,
            'measurement_source': 'curve_window_fallback',
            'measurement_status': 'degraded',
            'runtime_profile': profile_name(self.profile),
            'profile_release_state': str(self.profile.get('profile_release_state', 'research_validated') or 'research_validated'),
            'closure_mode': str(self.profile.get('closure_mode', 'runtime_optional') or 'runtime_optional'),
            'profile_config_path': str(self.profile.get('profile_config_path', '') or ''),
            'profile_load_error': str(self.profile.get('profile_load_error', '') or ''),
            'coordinate_frame': str(spine_curve.get('coordinate_frame', 'patient_surface') or 'patient_surface'),
            'angle_deg': angle_deg,
            'confidence': confidence,
            'requires_manual_review': True,
            'manual_review_reasons': self._unique_reasons(manual_review_reasons),
            'upper_end_vertebra_candidate': self._candidate_from_points('upper', upper_points),
            'lower_end_vertebra_candidate': self._candidate_from_points('lower', lower_points),
            'upper_line': upper_line,
            'lower_line': lower_line,
            'vertebra_pairs': [],
            'tilt_candidates': [],
            'evidence_refs': evidence_refs,
            'fit_diagnostics': {
                'point_count': len(points),
                'fit_count': fit_count,
                'upper_rmse_mm': upper_line['rmse_mm'],
                'lower_rmse_mm': lower_line['rmse_mm'],
                'reconstruction_confidence': float(reconstruction_summary.get('confidence', 0.0) or 0.0),
                'reconstruction_status': str(reconstruction_summary.get('reconstruction_status', 'unknown') or 'unknown'),
            },
        }


    def _preweight_blocked(self, reconstruction_summary: dict[str, Any]) -> bool:
        if not is_preweight_profile(self.profile):
            return False
        if str(reconstruction_summary.get('closure_verdict', '')) == 'blocked':
            return True
        if str(reconstruction_summary.get('measurement_source', '')) == 'registration_prior_curve':
            return True
        return bool(reconstruction_summary.get('hard_blockers', []))

    def _blocked_measurement(self, assessment_input: dict[str, Any], *, reason: str) -> dict[str, Any]:
        """Build an explicit blocked measurement for preweight fail-closed runs."""
        reconstruction_summary = dict(assessment_input.get('reconstruction_summary', {}))
        spine_curve = dict(assessment_input.get('spine_curve', {}))
        manual_review_reasons = self._unique_reasons(list(reconstruction_summary.get('manual_review_reasons', [])) + [reason])
        return self._finalize_measurement({
            'generated_at': now_text(),
            'session_id': str(assessment_input.get('session_id', '') or ''),
            'experiment_id': str(assessment_input.get('experiment_id', '') or ''),
            'method_version': self.method_version,
            'measurement_source': 'blocked_preweight_contract',
            'measurement_status': 'blocked',
            'runtime_profile': profile_name(self.profile),
            'profile_release_state': str(self.profile.get('profile_release_state', 'research_preweight') or 'research_preweight'),
            'closure_mode': str(self.profile.get('closure_mode', 'measured_only') or 'measured_only'),
            'coordinate_frame': str(spine_curve.get('coordinate_frame', 'patient_surface') or 'patient_surface'),
            'angle_deg': 0.0,
            'confidence': 0.0,
            'requires_manual_review': True,
            'manual_review_reasons': manual_review_reasons,
            'upper_end_vertebra_candidate': {},
            'lower_end_vertebra_candidate': {},
            'upper_line': {},
            'lower_line': {},
            'vertebra_pairs': [],
            'tilt_candidates': [],
            'evidence_refs': list(reconstruction_summary.get('evidence_refs', spine_curve.get('evidence_refs', []))),
            'fit_diagnostics': {'reason': reason},
        })

    def _finalize_measurement(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize measurement verdicts, blockers, and provenance metadata."""
        measurement = dict(payload)
        reconstruction_status = str(dict(payload.get('fit_diagnostics', {})).get('reconstruction_status', '') or '')
        hard_blockers = self._unique_reasons(list(measurement.get('hard_blockers', [])))
        if measurement.get('measurement_status') == 'blocked':
            closure_verdict = 'blocked'
        elif measurement.get('measurement_source') == 'curve_window_fallback':
            closure_verdict = 'prior_assisted'
        elif measurement.get('requires_manual_review', False):
            closure_verdict = 'degraded_measured'
        else:
            closure_verdict = 'authoritative_measured'
        contamination_flags = []
        if measurement.get('measurement_source') == 'curve_window_fallback':
            contamination_flags.append('curve_window_fallback_used')
        if reconstruction_status == 'prior_assisted':
            contamination_flags.append('registration_prior_curve_used')
        if closure_verdict == 'blocked' and not hard_blockers:
            hard_blockers = self._unique_reasons(list(measurement.get('manual_review_reasons', [])))
        measurement['runtime_profile'] = measurement.get('runtime_profile', profile_name(self.profile))
        measurement['profile_release_state'] = measurement.get('profile_release_state', str(self.profile.get('profile_release_state', 'research_validated') or 'research_validated'))
        measurement['closure_mode'] = measurement.get('closure_mode', str(self.profile.get('closure_mode', 'runtime_optional') or 'runtime_optional'))
        measurement['closure_verdict'] = closure_verdict
        measurement['provenance_purity'] = 'prior_assisted' if contamination_flags else ('blocked' if closure_verdict == 'blocked' else ('degraded_measured' if closure_verdict == 'degraded_measured' else 'authoritative_measured'))
        measurement['source_contamination_flags'] = self._unique_reasons(contamination_flags)
        measurement['hard_blockers'] = hard_blockers
        measurement['soft_review_reasons'] = [reason for reason in self._unique_reasons(list(measurement.get('manual_review_reasons', []))) if reason not in hard_blockers]
        return measurement

    @staticmethod
    def _fit_line(points: list[dict[str, Any]]) -> dict[str, Any]:
        x_values = [float(point.get('x_mm', 0.0)) for point in points]
        y_values = [float(point.get('y_mm', 0.0)) for point in points]
        x_mean = sum(x_values) / len(x_values)
        y_mean = sum(y_values) / len(y_values)
        denominator = sum((value - x_mean) ** 2 for value in x_values)
        slope = 0.0 if denominator <= 1e-9 else sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values)) / denominator
        intercept = y_mean - (slope * x_mean)
        residuals = [y - ((slope * x) + intercept) for x, y in zip(x_values, y_values)]
        rmse = (sum(residual * residual for residual in residuals) / len(residuals)) ** 0.5
        return {
            'slope': round(float(slope), 6),
            'intercept': round(float(intercept), 6),
            'angle_deg': round(float(degrees(atan(slope))), 4),
            'rmse_mm': round(float(rmse), 4),
            'point_span': [round(min(x_values), 3), round(max(x_values), 3)],
            'point_count': len(points),
        }

    @staticmethod
    def _candidate_from_points(label: str, points: list[dict[str, Any]]) -> dict[str, Any]:
        pivot = points[len(points) // 2]
        return {
            'label': f'{label}_curve_window',
            'frame_id': str(pivot.get('frame_id', '')),
            'segment_id': int(pivot.get('segment_id', 0) or 0),
            'position_mm': {
                'x': float(pivot.get('x_mm', 0.0)),
                'y': float(pivot.get('y_mm', 0.0)),
                'z': float(pivot.get('z_mm', 0.0)),
            },
        }

    @staticmethod
    def _candidate_from_tilt(label: str, candidate: dict[str, Any]) -> dict[str, Any]:
        return {
            'label': f'{label}_vertebra',
            'frame_id': str(candidate.get('frame_id', '')),
            'segment_id': int(candidate.get('segment_id', 0) or 0),
            'vertebra_id': str(candidate.get('vertebra_id', '')),
            'position_mm': {
                'x': 0.0,
                'y': float(candidate.get('center_y_mm', 0.0) or 0.0),
                'z': 0.0,
            },
        }

    def _confidence(self, *, reconstruction_summary: dict[str, Any], upper_line: dict[str, Any], lower_line: dict[str, Any], point_count: int) -> float:
        reconstruction_confidence = float(reconstruction_summary.get('confidence', 0.0) or 0.0)
        point_factor = min(1.0, point_count / 12.0)
        rmse_penalty = min(1.0, (float(upper_line.get('rmse_mm', 0.0)) + float(lower_line.get('rmse_mm', 0.0))) / 10.0)
        confidence = (reconstruction_confidence * 0.65) + (point_factor * 0.25) + ((1.0 - rmse_penalty) * 0.10)
        return round(max(0.0, min(1.0, confidence)), 4)

    @staticmethod
    def _unique_reasons(values: list[str]) -> list[str]:
        ordered: list[str] = []
        for value in values:
            item = str(value or '').strip()
            if item and item not in ordered:
                ordered.append(item)
        return ordered
