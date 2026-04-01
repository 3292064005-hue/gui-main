from __future__ import annotations

from dataclasses import asdict
from typing import Any

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.session_service import SessionService
from spine_ultrasound_ui.models import RuntimeConfig, WorkflowArtifacts
from spine_ultrasound_ui.utils import now_text

class SessionFacade:
    def __init__(self, session_service: SessionService, exp_manager: ExperimentManager) -> None:
        self.session_service = session_service
        self.exp_manager = exp_manager

    def create_experiment(self, config: RuntimeConfig, *, note: str = ""):
        return self.session_service.create_experiment(config, note=note)

    def reset_session(self) -> None:
        self.session_service.reset()

    def build_summary_payload(self, *, workflow_artifacts: WorkflowArtifacts, experiment, telemetry, config: RuntimeConfig, preview_scan_plan, execution_scan_plan, model_report: dict[str, Any], sdk_runtime: dict[str, Any], backend_link: dict[str, Any], bridge_observability: dict[str, Any], localization_result, deployment_profile: dict[str, Any], control_plane_snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "saved_at": now_text(),
            "core_state": telemetry.core_state.execution_state,
            "experiment": asdict(experiment) if experiment else None,
            "metrics": {
                "pressure_current": telemetry.metrics.pressure_current,
                "pressure_target": telemetry.metrics.pressure_target,
                "pressure_error": telemetry.metrics.pressure_error,
                "frame_id": telemetry.metrics.frame_id,
                "path_index": telemetry.metrics.path_index,
                "segment_id": telemetry.metrics.segment_id,
                "image_quality": telemetry.metrics.image_quality,
                "feature_confidence": telemetry.metrics.feature_confidence,
                "quality_score": telemetry.metrics.quality_score,
                "scan_progress": telemetry.metrics.scan_progress,
                "contact_mode": telemetry.metrics.contact_mode,
                "contact_confidence": telemetry.metrics.contact_confidence,
                "recommended_action": telemetry.metrics.recommended_action,
                "tcp_pose": asdict(telemetry.metrics.tcp_pose),
                "joint_pos": telemetry.metrics.joint_pos,
                "joint_vel": telemetry.metrics.joint_vel,
                "joint_torque": telemetry.metrics.joint_torque,
                "cart_force": telemetry.metrics.cart_force,
            },
            "robot": {**dict(telemetry.robot), "robot_model": config.robot_model, "axis_count": config.axis_count, "sdk_robot_class": config.sdk_robot_class},
            "safety": asdict(telemetry.safety_status),
            "recording": asdict(telemetry.recorder_status),
            "workflow": workflow_artifacts.to_dict(),
            "planning": {"preview": preview_scan_plan.to_dict() if preview_scan_plan is not None else {}, "execution": execution_scan_plan.to_dict() if execution_scan_plan is not None else {}, "model_report": dict(model_report)},
            "sdk_runtime": dict(sdk_runtime),
            "backend_link": dict(backend_link),
            "control_authority": dict(backend_link.get("control_plane", {}).get("control_authority", {})),
            "bridge_observability": dict(bridge_observability),
            "deployment_profile": dict(deployment_profile),
            "control_plane_snapshot": dict(control_plane_snapshot),
            "localization": {"registration_hash": localization_result.registration_hash() if localization_result is not None else "", "confidence": localization_result.confidence if localization_result is not None else 0.0, "registration_version": localization_result.registration_version if localization_result is not None else ""},
        }
