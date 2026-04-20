
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.models import CapabilityStatus, ExperimentRecord, ImplementationState, RuntimeConfig
from spine_ultrasound_ui.services.perception import GuidanceRuntimeService
from spine_ultrasound_ui.services.runtime_source_policy_service import RuntimeSourcePolicyService
from spine_ultrasound_ui.services.planning.types import LocalizationResult


@dataclass(frozen=True)
class LocalizationStrategyContract:
    """Immutable configuration for a concrete localization strategy."""

    version: str
    source_type: str
    source_label: str
    detail_template: str
    fallback_requires_review: bool = False


class GuidanceLocalizationStrategy:
    """Base guidance strategy fed by authoritative device facts.

    All callers must supply a pre-freeze authoritative device snapshot. Missing
    devices are normalized to explicit offline/unknown facts rather than legacy
    optimistic defaults.
    """

    contract: LocalizationStrategyContract

    def __init__(self, runtime: GuidanceRuntimeService | None = None) -> None:
        self.runtime = runtime or GuidanceRuntimeService()

    @property
    def version(self) -> str:
        return self.contract.version

    def run(
        self,
        experiment: ExperimentRecord,
        config: RuntimeConfig,
        *,
        device_roster: dict[str, Any] | None = None,
    ) -> LocalizationResult:
        """Execute the concrete localization strategy.

        Args:
            experiment: Active experiment record.
            config: Current runtime configuration.
            device_roster: Authoritative pre-freeze device snapshot captured
                from telemetry or backend state.

        Returns:
            The strategy-specific localization result.

        Raises:
            RuntimeError: Propagated from the guidance runtime when required
                evidence cannot be produced.
            ValueError: Propagated when malformed manual/calibration inputs are
                detected by downstream services.
        """
        normalized_roster = self._normalize_device_roster(device_roster)
        RuntimeSourcePolicyService().validate_guidance_preview(
            config=config,
            source_type=self.contract.source_type,
            provider_mode=str(getattr(config, "camera_guidance_input_mode", "")),
        )
        bundle = self.runtime.build(
            experiment_id=experiment.exp_id,
            config=config,
            device_roster=normalized_roster,
            source_type=self.contract.source_type,
            source_label=self.contract.source_label,
        )
        readiness = dict(bundle.localization_readiness)
        registration = dict(bundle.patient_registration)
        if self.contract.fallback_requires_review:
            readiness = self._force_review(readiness)
            registration = self._force_registration_review(registration)
        return self._build_result(experiment=experiment, registration=registration, readiness=readiness, bundle=bundle)

    def _build_result(
        self,
        *,
        experiment: ExperimentRecord,
        registration: dict[str, Any],
        readiness: dict[str, Any],
        bundle: Any,
    ) -> LocalizationResult:
        readiness_status = str(readiness.get('status', 'BLOCKED'))
        ready = readiness_status == 'READY_FOR_FREEZE'
        state = 'READY' if ready else ('REVIEW_REQUIRED' if readiness_status == 'READY_WITH_REVIEW' else 'BLOCKED')
        quality = dict(registration.get('registration_quality', {}))
        return LocalizationResult(
            status=CapabilityStatus(
                ready=ready,
                state=state,
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=self.contract.detail_template.format(exp_id=experiment.exp_id),
            ),
            roi_center_y=float(registration.get('camera_observations', {}).get('roi_center_y_mm', 0.0) or 0.0),
            segment_count=len(list(registration.get('usable_segments', []))),
            patient_registration=registration,
            registration_version=self.version,
            confidence=float(quality.get('overall_confidence', 0.0) or 0.0),
            localization_readiness=readiness,
            calibration_bundle=bundle.calibration_bundle,
            registration_candidate=bundle.registration_candidate,
            manual_adjustment=bundle.manual_adjustment,
            source_frame_set=bundle.source_frame_set,
            localization_replay_index=bundle.localization_replay_index,
            guidance_algorithm_registry=bundle.guidance_algorithm_registry,
            guidance_processing_steps=bundle.guidance_processing_steps,
        )

    @staticmethod
    def _normalize_device_roster(device_roster: dict[str, Any] | None) -> dict[str, Any]:
        """Normalize a pre-freeze device roster into the guidance contract surface.

        Args:
            device_roster: Authoritative runtime snapshot captured before freeze.

        Returns:
            Normalized device facts for robot/camera/ultrasound/pressure.

        Raises:
            ValueError: When the caller omits the authoritative device snapshot.

        Boundary behavior:
            - Missing snapshot => hard error.
            - Missing individual device entries => explicit offline/unknown.
            - Missing fact metadata => conservative runtime_snapshot defaults.
        """
        if device_roster is None:
            raise ValueError('authoritative device_roster is required before localization')
        roster = dict(device_roster)
        normalized: dict[str, Any] = {}
        for name in ('robot', 'camera', 'ultrasound', 'pressure'):
            raw = dict(roster.get(name, {}))
            online = bool(raw.get('online', raw.get('connected', False)))
            fresh = bool(raw.get('fresh', online)) if online else False
            normalized[name] = {
                **raw,
                'online': online,
                'fresh': fresh,
                'fact_source': str(raw.get('fact_source', 'runtime_snapshot' if raw else 'missing_from_runtime_snapshot')),
                'fact_origin': str(raw.get('fact_origin', raw.get('health', 'unknown' if raw else 'missing'))),
            }
        return normalized

    @staticmethod
    def _force_review(readiness: dict[str, Any]) -> dict[str, Any]:
        payload = dict(readiness)
        if payload.get('status') == 'READY_FOR_FREEZE':
            payload['status'] = 'READY_WITH_REVIEW'
        warnings = list(payload.get('warnings', []))
        if 'fallback_guidance_requires_manual_review' not in warnings:
            warnings.append('fallback_guidance_requires_manual_review')
        payload['warnings'] = warnings
        payload['review_required'] = True
        review = dict(payload.get('review_approval', {}))
        review.setdefault('approved', False)
        payload['review_approval'] = review
        freeze_gate = dict(payload.get('freeze_gate', {}))
        freeze_gate.update({'freeze_ready': False, 'review_required': True, 'review_approved': False})
        payload['freeze_gate'] = freeze_gate
        return payload

    @staticmethod
    def _force_registration_review(registration: dict[str, Any]) -> dict[str, Any]:
        payload = dict(registration)
        payload['status'] = 'REVIEW_REQUIRED'
        payload['freeze_ready'] = False
        warnings = list(payload.get('warnings', []))
        if 'fallback_guidance_requires_manual_review' not in warnings:
            warnings.append('fallback_guidance_requires_manual_review')
        payload['warnings'] = warnings
        return payload
