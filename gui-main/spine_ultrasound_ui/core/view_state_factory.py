from __future__ import annotations

from dataclasses import asdict

from spine_ultrasound_ui.core.telemetry_store import TelemetryStore
from spine_ultrasound_ui.core.workflow_state_machine import WorkflowContext, WorkflowStateMachine
from spine_ultrasound_ui.models import RuntimeConfig, SystemState, UiViewState, WorkflowArtifacts


class ViewStateFactory:
    def __init__(self, workflow: WorkflowStateMachine | None = None) -> None:
        self.workflow = workflow or WorkflowStateMachine()

    def build(
        self,
        telemetry: TelemetryStore,
        config: RuntimeConfig,
        workflow_artifacts: WorkflowArtifacts,
        current_experiment,
    ) -> UiViewState:
        permissions = self.workflow.permissions(
            WorkflowContext(
                core_state=SystemState(telemetry.core_state.execution_state),
                has_experiment=workflow_artifacts.has_experiment,
                session_locked=workflow_artifacts.session_locked,
                localization_ready=workflow_artifacts.localization.ready,
                preview_plan_ready=workflow_artifacts.preview_plan_ready,
            )
        )
        return UiViewState(
            state=telemetry.core_state.execution_state,
            devices={name: asdict(device) for name, device in telemetry.devices.items()},
            metrics={
                "pressure_current": telemetry.metrics.pressure_current,
                "pressure_target": telemetry.metrics.pressure_target,
                "pressure_error": telemetry.metrics.pressure_error,
                "frame_id": telemetry.metrics.frame_id,
                "path_index": telemetry.metrics.path_index,
                "segment_id": telemetry.metrics.segment_id,
                "image_quality": telemetry.metrics.image_quality,
                "feature_confidence": telemetry.metrics.feature_confidence,
                "quality_score": telemetry.metrics.quality_score,
                "cobb_angle": telemetry.metrics.cobb_angle,
                "scan_progress": telemetry.metrics.scan_progress,
                "tcp_pose": asdict(telemetry.metrics.tcp_pose),
                "joint_pos": telemetry.metrics.joint_pos,
                "joint_vel": telemetry.metrics.joint_vel,
                "joint_torque": telemetry.metrics.joint_torque,
                "cart_force": telemetry.metrics.cart_force,
                "contact_mode": telemetry.metrics.contact_mode,
                "contact_confidence": telemetry.metrics.contact_confidence,
                "recommended_action": telemetry.metrics.recommended_action,
            },
            config=config.to_dict(),
            current_experiment=asdict(current_experiment) if current_experiment else None,
            robot=dict(telemetry.robot),
            safety=asdict(telemetry.safety_status),
            recording=asdict(telemetry.recorder_status),
            permissions=permissions,
            workflow=workflow_artifacts.to_dict(),
        )
