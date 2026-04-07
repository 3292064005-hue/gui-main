from __future__ import annotations

from spine_ultrasound_ui.models import CapabilityStatus, ExperimentRecord, ImplementationState, RuntimeConfig
from spine_ultrasound_ui.services.perception import GuidanceRuntimeService
from spine_ultrasound_ui.services.planning.types import LocalizationResult


class HybridRegistrationStrategy:
    version = "hybrid_registration_v3"

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
            source_type="camera_ultrasound_fusion",
            source_label="camera_backed_registration",
        )
        readiness_status = str(bundle.localization_readiness.get("status", "BLOCKED"))
        ready = readiness_status == "READY_FOR_FREEZE"
        state = "READY" if ready else ("REVIEW_REQUIRED" if readiness_status == "READY_WITH_REVIEW" else "BLOCKED")
        registration = dict(bundle.patient_registration)
        quality = dict(registration.get("registration_quality", {}))
        return LocalizationResult(
            status=CapabilityStatus(
                ready=ready,
                state=state,
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=f"实验 {experiment.exp_id} 使用 camera 主引导与 ultrasound 校验联合生成 guidance 合同。",
            ),
            roi_center_y=float(registration.get("camera_observations", {}).get("roi_center_y_mm", 0.0) or 0.0),
            segment_count=len(list(registration.get("usable_segments", []))),
            patient_registration=registration,
            registration_version=self.version,
            confidence=float(quality.get("overall_confidence", 0.0) or 0.0),
            localization_readiness=bundle.localization_readiness,
            calibration_bundle=bundle.calibration_bundle,
            registration_candidate=bundle.registration_candidate,
            manual_adjustment=bundle.manual_adjustment,
            source_frame_set=bundle.source_frame_set,
            localization_replay_index=bundle.localization_replay_index,
            guidance_algorithm_registry=bundle.guidance_algorithm_registry,
            guidance_processing_steps=bundle.guidance_processing_steps,
        )
