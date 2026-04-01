from __future__ import annotations

from spine_ultrasound_ui.models import CapabilityStatus, ExperimentRecord, ImplementationState, RuntimeConfig
from spine_ultrasound_ui.services.patient_registration import build_patient_registration
from spine_ultrasound_ui.services.planning.types import LocalizationResult


class FallbackRegistrationStrategy:
    version = "fallback_simulated_registration_v1"

    def run(self, experiment: ExperimentRecord, config: RuntimeConfig) -> LocalizationResult:
        registration = build_patient_registration(
            experiment_id=experiment.exp_id,
            roi_center_y=18.0,
            segment_count=3,
            config=config,
        ).to_dict()
        registration["registration_quality"] = {
            "overall_confidence": 0.68,
            "registration_ready": True,
            "source_breakdown": {"camera": 0.0, "ultrasound": 0.0, "hybrid": 0.0, "fallback": 0.68},
        }
        registration.setdefault("stability", {"surface_fit_rmse_mm": 1.8, "centerline_confidence": 0.7})
        return LocalizationResult(
            status=CapabilityStatus(
                ready=True,
                state="DEGRADED_READY",
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=f"实验 {experiment.exp_id} 使用回退配准结果，建议人工复核。",
            ),
            roi_center_y=18.0,
            segment_count=3,
            patient_registration=registration,
            registration_version=self.version,
            confidence=0.68,
        )
