from __future__ import annotations

from typing import Any, Optional, Protocol

from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.core.command_journal import summarize_command_payload
from spine_ultrasound_ui.models import WorkflowArtifacts
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope, TelemetryEnvelope
from spine_ultrasound_ui.utils import now_ns, now_text


class AppRuntimeHost(Protocol):
    backend: Any
    telemetry: Any
    workflow_artifacts: WorkflowArtifacts
    config: Any
    execution_scan_plan: Any
    preview_scan_plan: Any
    localization_result: Any
    session_service: Any
    session_facade: Any
    postprocess_service: Any
    control_plane_reader: Any
    alarm_manager: Any
    log_generated: Any
    alarm_raised: Any
    camera_pixmap_ready: Any
    ultrasound_pixmap_ready: Any
    reconstruction_pixmap_ready: Any
    status_updated: Any
    system_state_changed: Any
    experiments_updated: Any
    sdk_runtime_snapshot: dict[str, Any]
    model_report: dict[str, Any]
    config_report: dict[str, Any]
    session_governance_snapshot: dict[str, Any]
    backend_link_snapshot: dict[str, Any]
    bridge_observability_snapshot: dict[str, Any]
    deployment_profile_snapshot: dict[str, Any]
    control_plane_snapshot: dict[str, Any]

    def _send_command(
        self,
        command: str,
        payload: Optional[dict] = None,
        *,
        workflow_step: str,
        auto_action: str = "",
    ) -> ReplyEnvelope: ...
    def _sync_control_plane_snapshots(self, snapshots: dict[str, dict]) -> None: ...
    def _log(self, level: str, message: str) -> None: ...
    def _emit_status(self) -> None: ...


class AppRuntimeBridge:
    def __init__(self, host: AppRuntimeHost):
        self.host = host

    def handle_telemetry(self, env: TelemetryEnvelope) -> None:
        alarm = self.host.telemetry.apply(env)
        if env.topic == "quality_feedback":
            self.host.session_service.record_quality_feedback(env.data, env.ts_ns)
            if float(env.data.get("quality_score", 1.0)) < 0.75:
                self.host.session_service.record_annotation(
                    kind="quality_issue",
                    message=f"quality_score={float(env.data.get('quality_score', 0.0)):.2f}",
                    ts_ns=env.ts_ns,
                    segment_id=self.host.telemetry.core_state.active_segment,
                    severity="WARN",
                    tags=["quality", "review"],
                )
        if env.topic == "contact_state":
            self.host.session_service.record_pressure_sample(
                {
                    "pressure_current": float(env.data.get("pressure_current", self.host.telemetry.metrics.pressure_current) or 0.0),
                    "desired_force_n": float(self.host.config.pressure_target),
                    "pressure_error": round(float(env.data.get("pressure_current", self.host.telemetry.metrics.pressure_current) or 0.0) - float(self.host.config.pressure_target), 4),
                    "contact_confidence": float(env.data.get("confidence", self.host.telemetry.metrics.contact_confidence) or 0.0),
                    "contact_mode": str(env.data.get("mode", self.host.telemetry.metrics.contact_mode)),
                    "recommended_action": str(env.data.get("recommended_action", self.host.telemetry.metrics.recommended_action)),
                    "contact_stable": bool(env.data.get("contact_stable", False)),
                    "force_status": str(env.data.get("force_status", env.data.get("status", "ok"))),
                    "force_source": str(env.data.get("force_source", env.data.get("source", self.host.config.force_sensor_provider))),
                    "wrench_n": list(env.data.get("wrench_n", self.host.telemetry.metrics.cart_force)),
                    "estimated_normal_force_n": float(env.data.get("estimated_normal_force_n", env.data.get("pressure_current", self.host.telemetry.metrics.pressure_current) or 0.0)),
                    "normal_force_confidence": float(env.data.get("normal_force_confidence", env.data.get("confidence", self.host.telemetry.metrics.contact_confidence) or 0.0)),
                    "admittance_displacement_mm": float(env.data.get("admittance_displacement_mm", 0.0) or 0.0),
                    "admittance_velocity_mm_s": float(env.data.get("admittance_velocity_mm_s", 0.0) or 0.0),
                    "admittance_saturated": bool(env.data.get("admittance_saturated", False)),
                    "orientation_trim_deg": float(env.data.get("orientation_trim_deg", 0.0) or 0.0),
                    "orientation_trim_saturated": bool(env.data.get("orientation_trim_saturated", False)),
                    "contact_control_mode": str(env.data.get("contact_control_mode", "normal_axis_admittance")),
                },
                env.ts_ns,
            )
        if alarm is not None:
            self.host.alarm_manager.push(
                alarm["severity"],
                alarm["source"],
                alarm["message"],
                auto_action_taken=alarm.get("auto_action", ""),
                workflow_step=alarm.get("workflow_step", ""),
                request_id=alarm.get("request_id", ""),
                event_ts_ns=alarm["event_ts_ns"],
            )
            trace = (
                f"session={alarm['session_id'] or '-'} segment={alarm['segment_id']} "
                f"step={alarm.get('workflow_step') or '-'} request={alarm.get('request_id') or '-'} "
                f"auto={alarm.get('auto_action') or '-'} ts={alarm['event_ts_ns']}"
            )
            self.host.alarm_raised.emit(f"{alarm['severity']}/{alarm['source']}: {alarm['message']} ({trace})")
            self.host.session_service.record_annotation(
                kind="alarm",
                message=alarm["message"],
                ts_ns=alarm["event_ts_ns"],
                segment_id=alarm.get("segment_id", 0),
                severity=alarm["severity"],
                tags=[alarm["source"], alarm.get("workflow_step", "")],
            )
            self.host.log_generated.emit(
                alarm["severity"],
                f"[{now_text()}] [{alarm['source']}] {alarm['message']} ({trace})",
            )
        if self.host.session_service.current_experiment is not None:
            self.host.session_service.current_experiment.state = self.host.telemetry.core_state.execution_state
        self.refresh_bridge_observability()
        self.host._emit_status()

    def on_camera_pixmap(self, pixmap: QPixmap) -> None:
        ts_ns = now_ns()
        self.host.session_service.record_camera_pixmap(
            pixmap,
            source_ts_ns=ts_ns,
            metadata={
                "frame_id": int(self.host.telemetry.metrics.frame_id),
                "segment_id": int(self.host.telemetry.metrics.segment_id),
                "scan_progress": float(self.host.telemetry.metrics.scan_progress),
            },
        )
        self.host.camera_pixmap_ready.emit(pixmap)

    def on_ultrasound_pixmap(self, pixmap: QPixmap) -> None:
        ts_ns = now_ns()
        self.host.session_service.record_ultrasound_pixmap(
            pixmap,
            source_ts_ns=ts_ns,
            metadata={
                "frame_id": int(self.host.telemetry.metrics.frame_id),
                "segment_id": int(self.host.telemetry.metrics.segment_id),
                "quality_score": float(self.host.telemetry.metrics.quality_score),
                "pressure_current": float(self.host.telemetry.metrics.pressure_current),
                "contact_mode": str(self.host.telemetry.metrics.contact_mode),
            },
        )
        self.host.ultrasound_pixmap_ready.emit(pixmap)

    def send_or_warn(self, command: str, payload: Optional[dict] = None) -> ReplyEnvelope:
        reply = self.host._send_command(command, payload, workflow_step=command)
        self.refresh_sdk_assets(force=True)
        if not reply.ok:
            self.host._log("WARN", f"{command} 失败：{reply.message}")
        self.host._emit_status()
        return reply

    def run_guarded_command(
        self,
        command: str,
        payload: Optional[dict] = None,
        *,
        success_message: Optional[str] = None,
        fallback_to_safe_retreat: bool = False,
        force_asset_refresh: bool = True,
    ) -> bool:
        reply = self.host._send_command(command, payload, workflow_step=command)
        if reply.ok:
            self.host.session_service.record_annotation(
                kind="workflow",
                message=f"{command} ok",
                segment_id=self.host.telemetry.core_state.active_segment,
                severity="INFO",
                tags=[command],
            )
            if success_message:
                self.host._log("INFO", success_message)
            if force_asset_refresh:
                self.refresh_sdk_assets(force=True)
            self.host._emit_status()
            return True
        self.host.session_service.record_annotation(
            kind="workflow_failure",
            message=f"{command} failed: {reply.message}",
            segment_id=self.host.telemetry.core_state.active_segment,
            severity="ERROR",
            tags=[command, "retry" if fallback_to_safe_retreat else "manual"],
        )
        self.host._log("ERROR", f"{command} 失败：{reply.message}")
        self.raise_local_alarm(
            "ERROR",
            "workflow",
            f"{command} 失败：{reply.message}",
            workflow_step=command,
            request_id=reply.request_id,
        )
        if fallback_to_safe_retreat:
            self.request_safe_retreat_after_failure(command)
        if force_asset_refresh:
            self.refresh_sdk_assets(force=True)
        self.host._emit_status()
        return False

    def request_safe_retreat_after_failure(self, failed_command: str) -> None:
        retreat = self.host._send_command("safe_retreat", workflow_step=failed_command, auto_action="safe_retreat")
        if retreat.ok:
            self.host._log("WARN", f"{failed_command} 失败后已自动请求安全退让。")
            self.raise_local_alarm(
                "WARN",
                "workflow",
                f"{failed_command} 失败后已自动请求安全退让。",
                workflow_step=failed_command,
                request_id=retreat.request_id,
                auto_action="safe_retreat",
            )
            return
        self.host._log("ERROR", f"{failed_command} 失败后安全退让也失败：{retreat.message}")
        self.raise_local_alarm(
            "ERROR",
            "workflow",
            f"{failed_command} 失败后安全退让也失败：{retreat.message}",
            workflow_step=failed_command,
            request_id=retreat.request_id,
            auto_action="safe_retreat_failed",
        )

    def build_summary_payload(self) -> dict[str, Any]:
        return self.host.session_facade.build_summary_payload(
            workflow_artifacts=self.host.workflow_artifacts,
            experiment=self.host.session_service.current_experiment,
            telemetry=self.host.telemetry,
            config=self.host.config,
            preview_scan_plan=self.host.preview_scan_plan,
            execution_scan_plan=self.host.execution_scan_plan,
            model_report=self.host.model_report,
            sdk_runtime=self.host.sdk_runtime_snapshot,
            backend_link=self.host.backend_link_snapshot,
            bridge_observability=self.host.bridge_observability_snapshot,
            localization_result=self.host.localization_result,
            deployment_profile=self.host.deployment_profile_snapshot,
            control_plane_snapshot=self.host.control_plane_snapshot,
        )

    def refresh_governance(self, *, force_sdk_assets: bool = False) -> None:
        """Perform the authoritative full governance refresh.

        This path is intended for command/config/workflow transitions. It may
        refresh SDK assets, query the runtime verdict, and rebuild the full
        control-plane snapshot.
        """
        snapshots = self.host.control_plane_reader.refresh_full(
            backend=self.host.backend,
            config=self.host.config,
            telemetry=self.host.telemetry,
            workflow_artifacts=self.host.workflow_artifacts,
            execution_scan_plan=self.host.execution_scan_plan,
            current_session_dir=self.host.session_service.current_session_dir,
            force_sdk_assets=force_sdk_assets,
        )
        self.host._sync_control_plane_snapshots(snapshots)

    def refresh_sdk_assets(self, *, force: bool = False) -> None:
        self.refresh_governance(force_sdk_assets=force)

    def refresh_session_governance(self) -> None:
        """Refresh only session-governance-derived snapshots."""
        snapshots = self.host.control_plane_reader.refresh_session_governance(
            current_session_dir=self.host.session_service.current_session_dir,
        )
        self.host._sync_control_plane_snapshots(snapshots)

    def refresh_backend_link(self) -> None:
        """Refresh backend-link and bridge projections without recompiling governance-heavy products."""
        snapshots = self.host.control_plane_reader.refresh_backend_projection(
            backend=self.host.backend,
            telemetry=self.host.telemetry,
            workflow_artifacts=self.host.workflow_artifacts,
        )
        self.host._sync_control_plane_snapshots(snapshots)

    def refresh_bridge_observability(self) -> None:
        """Refresh telemetry-facing bridge observability from cached control-plane inputs only."""
        snapshots = self.host.control_plane_reader.refresh_bridge_projection(
            telemetry=self.host.telemetry,
            workflow_artifacts=self.host.workflow_artifacts,
        )
        self.host._sync_control_plane_snapshots(snapshots)

    def raise_local_alarm(
        self,
        severity: str,
        source: str,
        message: str,
        *,
        workflow_step: str,
        request_id: str = "",
        auto_action: str = "",
    ) -> None:
        event_ts_ns = now_ns()
        self.host.alarm_manager.push(
            severity,
            source,
            message,
            auto_action_taken=auto_action,
            workflow_step=workflow_step,
            request_id=request_id,
            event_ts_ns=event_ts_ns,
        )
        trace = f"step={workflow_step or '-'} request={request_id or '-'} auto={auto_action or '-'} ts={event_ts_ns}"
        self.host.alarm_raised.emit(f"{severity}/{source}: {message} ({trace})")
        self.host.log_generated.emit(severity, f"[{now_text()}] [{source}] {message} ({trace})")

    def refresh_session_products(self) -> None:
        statuses = self.host.postprocess_service.refresh_all(self.host.session_service.current_session_dir)
        self.host.workflow_artifacts.preprocess = statuses["preprocess"]
        self.host.workflow_artifacts.reconstruction = statuses["reconstruction"]
        self.host.workflow_artifacts.assessment = statuses["assessment"]
        self.host.session_service.refresh_session_intelligence()
        self.refresh_session_governance()
