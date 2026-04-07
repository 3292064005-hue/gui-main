from __future__ import annotations

from spine_ultrasound_ui.models import CapabilityStatus, ExperimentRecord, ImplementationState, RuntimeConfig
from spine_ultrasound_ui.services.perception import GuidanceRuntimeService
from spine_ultrasound_ui.services.planning.types import LocalizationResult


class FallbackRegistrationStrategy:
    version = "fallback_simulated_registration_v3"

    def __init__(self) -> None:
        self.runtime = GuidanceRuntimeService()

    def run(self, experiment: ExperimentRecord, config: RuntimeConfig) -> LocalizationResult:
        bundle = self.runtime.build(
            experiment_id=experiment.exp_id,
            config=config,
            device_roster={
                "robot": {"online": True, "fresh": True},
                "camera": {"online": True, "fresh": True},
                "ultrasound": {"online": True, "fresh": True},
                "pressure": {"online": True, "fresh": True},
            },
            source_type="fallback_simulated",
            source_label="fallback_simulated_registration",
        )
        readiness = dict(bundle.localization_readiness)
        if readiness.get("status") == "READY_FOR_FREEZE":
            readiness["status"] = "READY_WITH_REVIEW"
        readiness.setdefault("warnings", []).append("fallback_guidance_requires_manual_review")
        readiness["review_required"] = True
        readiness.setdefault("freeze_gate", {}).update({"freeze_ready": False, "review_required": True, "review_approved": False})
        bundle.patient_registration["status"] = "REVIEW_REQUIRED"
        bundle.patient_registration["freeze_ready"] = False
        bundle.patient_registration.setdefault("warnings", []).append("fallback_guidance_requires_manual_review")
        quality = dict(bundle.patient_registration.get("registration_quality", {}))
        return LocalizationResult(
            status=CapabilityStatus(
                ready=False,
                state="REVIEW_REQUIRED",
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=f"实验 {experiment.exp_id} 使用回退 guidance 合同，必须人工复核后才能锁定。",
            ),
            roi_center_y=float(bundle.patient_registration.get("camera_observations", {}).get("roi_center_y_mm", 0.0) or 0.0),
            segment_count=len(list(bundle.patient_registration.get("usable_segments", []))),
            patient_registration=bundle.patient_registration,
            registration_version=self.version,
            confidence=float(quality.get("overall_confidence", 0.0) or 0.0),
            localization_readiness=readiness,
            calibration_bundle=bundle.calibration_bundle,
            registration_candidate=bundle.registration_candidate,
            manual_adjustment=bundle.manual_adjustment,
            source_frame_set=bundle.source_frame_set,
            localization_replay_index=bundle.localization_replay_index,
            guidance_algorithm_registry=bundle.guidance_algorithm_registry,
            guidance_processing_steps=bundle.guidance_processing_steps,
        )
