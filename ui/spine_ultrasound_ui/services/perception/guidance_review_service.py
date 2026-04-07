from __future__ import annotations

from dataclasses import replace
from typing import Any

from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState
from spine_ultrasound_ui.services.perception.guidance_gate_service import GuidanceGateService
from spine_ultrasound_ui.services.perception.guidance_registration_builder import GuidanceRegistrationBuilder
from spine_ultrasound_ui.services.perception.manual_adjustment_service import ManualAdjustmentService
from spine_ultrasound_ui.services.planning.types import LocalizationResult


class GuidanceReviewService:
    """Approve or amend review-required guidance bundles before session freeze.

    This service closes the operator review loop for guidance bundles that are
    intentionally blocked from direct freeze until a human approves or adjusts
    them.
    """

    def __init__(
        self,
        *,
        gate_service: GuidanceGateService | None = None,
        registration_builder: GuidanceRegistrationBuilder | None = None,
        manual_adjustment_service: ManualAdjustmentService | None = None,
    ) -> None:
        self.gate_service = gate_service or GuidanceGateService()
        self.registration_builder = registration_builder or GuidanceRegistrationBuilder()
        self.manual_adjustment_service = manual_adjustment_service or ManualAdjustmentService()

    def approve(
        self,
        *,
        localization_result: LocalizationResult,
        operator_id: str,
        adjustments: list[dict[str, Any]] | None = None,
        reason: str = 'manual_guidance_review',
    ) -> LocalizationResult:
        """Approve a review-required localization bundle.

        Args:
            localization_result: Existing localization result requiring review.
            operator_id: Operator identity recorded in the approval artifact.
            adjustments: Optional additional manual deltas to record.
            reason: Review reason stored in the manual adjustment log.

        Returns:
            Updated localization result with review approval applied.

        Raises:
            RuntimeError: If the localization bundle is blocked or incomplete.
            ValueError: If the adjustment payload is malformed.
        """
        readiness = dict(localization_result.localization_readiness)
        if not readiness:
            raise RuntimeError('localization readiness payload is required for review approval')
        if str(readiness.get('status', 'BLOCKED')) == 'BLOCKED':
            raise RuntimeError('blocked localization bundle cannot be approved')
        existing_adjustments = list(dict(localization_result.manual_adjustment).get('adjustments', []))
        review_marker = {
            'adjustment_id': f'review::{localization_result.registration_hash()[:8]}',
            'operator_id': operator_id,
            'reason': reason,
            'target': 'guidance_review',
            'delta': {'approved': True},
            'pre_hash': localization_result.registration_hash(),
            'post_hash': '',
        }
        normalized_adjustment = self.manual_adjustment_service.normalize(existing_adjustments + list(adjustments or []) + [review_marker])
        approved_readiness = self.gate_service.evaluate(
            device_roster=self._device_roster_from_readiness(readiness),
            calibration_bundle=dict(localization_result.calibration_bundle),
            registration_candidate=dict(localization_result.registration_candidate),
            source_frame_set=dict(localization_result.source_frame_set),
            source_type=str(localization_result.patient_registration.get('source_type', 'camera_only')),
            manual_adjustment=normalized_adjustment,
            review_context={'approved': True, 'operator_id': operator_id, 'reason': reason},
        )
        updated_registration = self.registration_builder.build(
            experiment_id=str(localization_result.patient_registration.get('registration_id', 'reg::unknown')).split('::', 1)[-1],
            source_type=str(localization_result.patient_registration.get('source_type', 'camera_only')),
            source_label=str(localization_result.patient_registration.get('source', 'camera_backed_registration')),
            patient_frame=dict(localization_result.patient_registration.get('patient_frame', {})),
            scan_corridor=dict(localization_result.patient_registration.get('scan_corridor', {})),
            landmarks=list(localization_result.patient_registration.get('landmarks', [])),
            body_surface=dict(localization_result.patient_registration.get('body_surface', {})),
            camera_observations=dict(localization_result.patient_registration.get('camera_observations', {})),
            registration_quality=dict(localization_result.patient_registration.get('registration_quality', {})),
            guidance_targets=dict(localization_result.patient_registration.get('guidance_targets', {})),
            usable_segments=list(localization_result.patient_registration.get('usable_segments', [])),
            notes=list(localization_result.patient_registration.get('notes', [])) + [f'Guidance review approved by {operator_id}.'],
            calibration_bundle=dict(localization_result.calibration_bundle),
            localization_readiness=approved_readiness,
            source_frame_set=dict(localization_result.source_frame_set),
            algorithm_bundle_hash=str(localization_result.patient_registration.get('algorithm_bundle_hash', '')),
            manual_adjustment=normalized_adjustment,
            processing_step_refs=list(localization_result.patient_registration.get('processing_step_refs', [])),
        )
        status = CapabilityStatus(
            ready=True,
            state='READY',
            implementation=ImplementationState.IMPLEMENTED.value,
            detail=f'Guidance review approved by {operator_id}; session freeze is now permitted.',
        )
        return replace(
            localization_result,
            status=status,
            patient_registration=updated_registration,
            localization_readiness=approved_readiness,
            manual_adjustment=normalized_adjustment,
        )

    @staticmethod
    def _device_roster_from_readiness(readiness: dict[str, Any]) -> dict[str, Any]:
        device_gate = dict(readiness.get('device_gate', {}))
        frame_fresh = bool(device_gate.get('frame_fresh', True))
        return {
            'camera': {'online': bool(device_gate.get('camera_online', True)), 'fresh': frame_fresh},
            'robot': {'online': bool(device_gate.get('robot_online', True)), 'fresh': True},
            'ultrasound': {'online': bool(device_gate.get('ultrasound_online', True)), 'fresh': True},
            'pressure': {'online': bool(device_gate.get('pressure_online', True)), 'fresh': True},
        }
