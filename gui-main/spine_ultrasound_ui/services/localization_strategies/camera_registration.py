from __future__ import annotations

from spine_ultrasound_ui.models import CapabilityStatus, ExperimentRecord, ImplementationState, RuntimeConfig
from spine_ultrasound_ui.services.patient_registration import build_patient_registration
from spine_ultrasound_ui.services.planning.types import LocalizationResult


class CameraRegistrationStrategy:
    version = "camera_backed_registration_v3"

    def run(self, experiment: ExperimentRecord, config: RuntimeConfig) -> LocalizationResult:
        registration = build_patient_registration(
            experiment_id=experiment.exp_id,
            roi_center_y=18.0,
            segment_count=4,
            config=config,
        ).to_dict()
        quality = dict(registration.get("registration_quality", {}))
        quality.setdefault("overall_confidence", 0.92)
        quality.setdefault("registration_ready", True)
        quality.setdefault("source_breakdown", {"camera": 0.92, "ultrasound": 0.0, "hybrid": 0.0})
        registration["registration_quality"] = quality
        registration.setdefault("stability", {"surface_fit_rmse_mm": 0.8, "centerline_confidence": 0.91})
        return LocalizationResult(
            status=CapabilityStatus(
                ready=True,
                state="READY",
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=f"实验 {experiment.exp_id} 使用相机辅助患者配准结果。",
            ),
            roi_center_y=18.0,
            segment_count=4,
            patient_registration=registration,
            registration_version=self.version,
            confidence=float(quality.get("overall_confidence", 0.92)),
        )
