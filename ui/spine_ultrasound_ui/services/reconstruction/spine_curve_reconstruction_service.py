from __future__ import annotations

from typing import Any

import numpy as np

from spine_ultrasound_ui.services.reconstruction.bone_segmentation_inference_service import BoneSegmentationInferenceService
from spine_ultrasound_ui.services.reconstruction.closure_profile import load_reconstruction_profile, profile_name
from spine_ultrasound_ui.services.reconstruction.frame_anatomy_point_inference_service import FrameAnatomyPointInferenceService
from spine_ultrasound_ui.services.reconstruction.lamina_center_inference_service import LaminaCenterInferenceService
from spine_ultrasound_ui.services.reconstruction.spine_curve_aggregation_service import SpineCurveAggregationService
from spine_ultrasound_ui.services.reconstruction.vpi_projection_builder import VPIProjectionBuilder
from spine_ultrasound_ui.utils import now_text


class SpineCurveReconstructionService:
    """Orchestrate authoritative lamina-aware reconstruction for a session."""

    def __init__(
        self,
        *,
        review_confidence_threshold: float = 0.82,
        min_selected_points: int = 4,
        method_version: str = 'spine_curve_reconstruction_v3',
        vpi_builder: VPIProjectionBuilder | None = None,
        bone_segmentation_service: BoneSegmentationInferenceService | None = None,
        lamina_center_service: LaminaCenterInferenceService | None = None,
        frame_anatomy_point_service: FrameAnatomyPointInferenceService | None = None,
        curve_aggregation_service: SpineCurveAggregationService | None = None,
    ) -> None:
        self.review_confidence_threshold = float(review_confidence_threshold)
        self.min_selected_points = int(min_selected_points)
        self.method_version = method_version
        self.vpi_builder = vpi_builder or VPIProjectionBuilder()
        self.bone_segmentation_service = bone_segmentation_service or BoneSegmentationInferenceService()
        self.frame_anatomy_point_service = frame_anatomy_point_service or FrameAnatomyPointInferenceService()
        self.lamina_center_service = lamina_center_service or LaminaCenterInferenceService()
        self.curve_aggregation_service = curve_aggregation_service or SpineCurveAggregationService()
        self.profile = load_reconstruction_profile()
        thresholds = dict(self.profile.get('thresholds', {}) or {})
        self.min_selected_points = int(thresholds.get('min_reconstruction_points', self.min_selected_points) or self.min_selected_points)

    def reconstruct(self, input_index: dict[str, Any]) -> dict[str, Any]:
        """Build authoritative reconstruction artifacts.

        Args:
            input_index: Payload produced by :class:`ReconstructionInputBuilder`.

        Returns:
            Dictionary containing VPI artifacts, bone masks, lamina candidates,
            spine curve, landmark track, and reconstruction summary.

        Raises:
            ValueError: Raised when required session identifiers are missing.

        Boundary behaviour:
            Sparse or partially invalid sessions remain serializable. The
            summary surface makes any degraded inputs explicit through
            ``manual_review_reasons`` and ``reconstruction_status``.
        """
        session_id = str(input_index.get('session_id', '') or '')
        if not session_id:
            raise ValueError('input_index.session_id is required')
        projection_bundle = self.vpi_builder.build(input_index)
        bone_mask_bundle = self.bone_segmentation_service.infer(projection_bundle)
        frame_anatomy_points = self.frame_anatomy_point_service.infer(input_index)
        lamina_candidates = self.lamina_center_service.infer(projection_bundle, bone_mask_bundle, input_index, frame_anatomy_points=frame_anatomy_points)
        aggregated = self.curve_aggregation_service.aggregate(lamina_candidates, dict(input_index.get('patient_registration', {})))
        spine_curve = dict(aggregated['spine_curve'])
        landmark_track = dict(aggregated['landmark_track'])
        summary = dict(aggregated['reconstruction_summary'])
        point_count = int(summary.get('point_count', 0) or 0)
        prior_assisted_curve = dict(aggregated.get('prior_assisted_curve', {})) if isinstance(aggregated.get('prior_assisted_curve', {}), dict) else {}
        runtime_models = {
            'bone_segmentation': dict(bone_mask_bundle.get('runtime_model', {})),
            'frame_anatomy_keypoint': dict(frame_anatomy_points.get('runtime_model', {})),
            'lamina_keypoint': dict(lamina_candidates.get('runtime_model', {})),
        }
        upstream_reasons = [str(item) for item in list(input_index.get('manual_review_reasons', [])) if str(item)]
        curve_reasons = [str(item) for item in list(summary.get('manual_review_reasons', [])) if str(item)]
        if point_count < self.min_selected_points:
            curve_reasons.append('insufficient_reconstruction_points')
        if float(summary.get('confidence', 0.0) or 0.0) < self.review_confidence_threshold:
            curve_reasons.append('reconstruction_confidence_below_threshold')
        if str(summary.get('measurement_source', '')) == 'registration_prior_curve':
            curve_reasons.append('registration_prior_curve_used')
        manual_review_reasons = self._unique_reasons(upstream_reasons + curve_reasons)
        contamination_flags = self._contamination_flags(manual_review_reasons, str(summary.get('measurement_source', '')))
        hard_blockers = self._hard_blockers(input_index, manual_review_reasons, contamination_flags, point_count)
        if hard_blockers:
            closure_verdict = 'blocked'
            provenance_purity = 'blocked'
        elif contamination_flags:
            closure_verdict = 'prior_assisted'
            provenance_purity = 'prior_assisted'
        elif manual_review_reasons:
            closure_verdict = 'degraded_measured'
            provenance_purity = 'degraded_measured'
        else:
            closure_verdict = 'authoritative_measured'
            provenance_purity = 'authoritative_measured'
        reconstruction_status = 'blocked' if hard_blockers else ('authoritative' if not manual_review_reasons else 'degraded')
        summary.update({
            'generated_at': now_text(),
            'session_id': session_id,
            'experiment_id': str(input_index.get('experiment_id', '') or ''),
            'method_version': self.method_version,
            'runtime_profile': profile_name(self.profile),
            'profile_release_state': str(self.profile.get('profile_release_state', 'research_validated') or 'research_validated'),
            'closure_mode': str(self.profile.get('closure_mode', 'runtime_optional') or 'runtime_optional'),
            'profile_config_path': str(self.profile.get('profile_config_path', '') or ''),
            'profile_load_error': str(self.profile.get('profile_load_error', '') or ''),
            'requires_manual_review': bool(manual_review_reasons),
            'manual_review_reasons': manual_review_reasons,
            'hard_blockers': hard_blockers,
            'soft_review_reasons': [reason for reason in manual_review_reasons if reason not in hard_blockers],
            'closure_verdict': closure_verdict,
            'provenance_purity': provenance_purity,
            'source_contamination_flags': contamination_flags,
            'reconstruction_status': reconstruction_status,
            'coordinate_frame': str(spine_curve.get('coordinate_frame', 'patient_surface') or 'patient_surface'),
            'selected_row_count': int(input_index.get('source_counts', {}).get('selected_rows', 0) or 0),
            'authoritative_row_count': int(input_index.get('source_counts', {}).get('authoritative_rows', 0) or 0),
            'vpi_peak_intensity': float(projection_bundle.get('stats', {}).get('peak_intensity', 0.0) or 0.0),
            'bone_coverage_ratio': float(bone_mask_bundle.get('summary', {}).get('coverage_ratio', 0.0) or 0.0),
            'lamina_candidate_count': int(lamina_candidates.get('summary', {}).get('candidate_count', 0) or 0),
            'frame_anatomy_point_count': int(frame_anatomy_points.get('summary', {}).get('point_count', 0) or 0),
            'frame_anatomy_stable_frame_count': int(frame_anatomy_points.get('summary', {}).get('stable_frame_count', 0) or 0),
            'lamina_candidate_source': str(lamina_candidates.get('summary', {}).get('primary_source', 'projection_fallback') or 'projection_fallback'),
            'runtime_models': runtime_models,
            'input_gates': dict(input_index.get('gates', {})),
        })
        reconstruction_evidence = {
            'generated_at': now_text(),
            'session_id': session_id,
            'method_version': self.method_version,
            'vpi_stats': dict(projection_bundle.get('stats', {})),
            'bone_mask_summary': dict(bone_mask_bundle.get('summary', {})),
            'frame_anatomy_summary': dict(frame_anatomy_points.get('summary', {})),
            'lamina_summary': dict(lamina_candidates.get('summary', {})),
            'row_geometry': list(projection_bundle.get('row_geometry', [])),
            'contributing_frames': list(projection_bundle.get('contributing_frames', [])),
            'runtime_models': runtime_models,
            'evidence_refs': list(summary.get('evidence_refs', [])),
        }
        pose_series = {
            'generated_at': now_text(),
            'session_id': session_id,
            'coordinate_frame': 'patient_surface',
            'poses': [dict(item) for item in input_index.get('probe_pose_series', []) if isinstance(item, dict)],
        }
        return {
            'coronal_vpi': {
                'generated_at': now_text(),
                'session_id': session_id,
                'method_version': projection_bundle.get('method_version', ''),
                'stats': dict(projection_bundle.get('stats', {})),
                'slices': list(projection_bundle.get('slices', [])),
                'row_geometry': list(projection_bundle.get('row_geometry', [])),
                'contributing_frames': list(projection_bundle.get('contributing_frames', [])),
                'contribution_map': np.asarray(projection_bundle.get('contribution_map', np.zeros((1, 1), dtype=np.float32))),
                'image': np.asarray(projection_bundle.get('image', np.zeros((1, 1), dtype=np.float32))),
                'preview_rgb': np.asarray(projection_bundle.get('preview_rgb', np.zeros((1, 1, 3), dtype=np.uint8))),
            },
            'frame_anatomy_points': frame_anatomy_points,
            'bone_mask': {
                'generated_at': now_text(),
                'session_id': session_id,
                'method_version': bone_mask_bundle.get('method_version', ''),
                'summary': dict(bone_mask_bundle.get('summary', {})),
                'runtime_model': dict(bone_mask_bundle.get('runtime_model', {})),
                'mask': np.asarray(bone_mask_bundle.get('mask', np.zeros((1, 1), dtype=np.float32))),
                'binary_mask': np.asarray(bone_mask_bundle.get('binary_mask', np.zeros((1, 1), dtype=np.uint8))),
            },
            'lamina_candidates': lamina_candidates,
            'pose_series': pose_series,
            'reconstruction_evidence': reconstruction_evidence,
            'spine_curve': spine_curve,
            'landmark_track': landmark_track,
            'reconstruction_summary': summary,
            'prior_assisted_curve': prior_assisted_curve,
        }


    def _contamination_flags(self, manual_review_reasons: list[str], measurement_source: str) -> list[str]:
        flags: list[str] = []
        for reason in manual_review_reasons:
            if reason in {'registration_prior_curve_used', 'curve_window_fallback_used'} and reason not in flags:
                flags.append(reason)
        if str(measurement_source or '') == 'registration_prior_curve' and 'registration_prior_curve_used' not in flags:
            flags.append('registration_prior_curve_used')
        return flags

    def _hard_blockers(self, input_index: dict[str, Any], manual_review_reasons: list[str], contamination_flags: list[str], point_count: int) -> list[str]:
        closure_policy = dict(self.profile.get('closure_policy', {}) or {})
        configured = {str(item) for item in list(closure_policy.get('hard_blockers', [])) if str(item)}
        blockers = [reason for reason in self._unique_reasons(list(input_index.get('hard_blockers', [])) + manual_review_reasons + contamination_flags) if reason in configured]
        if point_count < self.min_selected_points and 'insufficient_reconstruction_points' in configured and 'insufficient_reconstruction_points' not in blockers:
            blockers.append('insufficient_reconstruction_points')
        return self._unique_reasons(blockers)

    @staticmethod
    def _unique_reasons(values: list[str]) -> list[str]:
        ordered: list[str] = []
        for value in values:
            item = str(value or '').strip()
            if item and item not in ordered:
                ordered.append(item)
        return ordered
