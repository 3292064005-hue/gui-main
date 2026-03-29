from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.core.alarm_manager import AlarmManager
from spine_ultrasound_ui.core.command_journal import summarize_command_payload
from spine_ultrasound_ui.core.exception_handler import global_exception_handler, AppException, ErrorCategory, ErrorSeverity
from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.plan_service import LocalizationResult, PlanService
from spine_ultrasound_ui.core.postprocess_service import PostprocessService
from spine_ultrasound_ui.core.session_service import SessionService
from spine_ultrasound_ui.core.telemetry_store import TelemetryStore
from spine_ultrasound_ui.core.view_state_factory import ViewStateFactory
from spine_ultrasound_ui.models import ExperimentRecord, RuntimeConfig, ScanPlan, SystemState, WorkflowArtifacts
from spine_ultrasound_ui.services.backend_base import BackendBase
from spine_ultrasound_ui.services.force_control_config import load_force_control_config
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope, TelemetryEnvelope
from spine_ultrasound_ui.utils import ensure_dir, now_ns, now_text


class AppController(QObject):
    status_updated = Signal(dict)
    log_generated = Signal(str, str)
    camera_pixmap_ready = Signal(QPixmap)
    ultrasound_pixmap_ready = Signal(QPixmap)
    reconstruction_pixmap_ready = Signal(QPixmap)
    experiments_updated = Signal(list)
    system_state_changed = Signal(str)
    alarm_raised = Signal(str)

    def __init__(self, root_dir: Path, backend: BackendBase):
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.exp_root = ensure_dir(self.root_dir / "experiments")
        self.backend = backend
        self.config = RuntimeConfig()
        self.telemetry = TelemetryStore()
        self.telemetry.metrics.pressure_target = self.config.pressure_target
        self.workflow_artifacts = WorkflowArtifacts()
        self.exp_manager = ExperimentManager(self.exp_root)
        self.session_service = SessionService(self.exp_manager)
        self.plan_service = PlanService()
        self.postprocess_service = PostprocessService(self.exp_manager)
        self.view_factory = ViewStateFactory()
        self.alarm_manager = AlarmManager()
        self.experiments: list[ExperimentRecord] = []
        self.localization_result: Optional[LocalizationResult] = None
        self.preview_scan_plan: Optional[ScanPlan] = None
        self._connect_backend()
        self._connect_exception_handler()

    def _connect_exception_handler(self) -> None:
        """Connect to global exception handler"""
        global_exception_handler.error_occurred.connect(self._on_error_occurred)

    def _on_error_occurred(self, message: str, severity: str, recovery_action: str) -> None:
        """Handle errors from exception handler"""
        self._log(severity.upper(), f"错误: {message}")
        if recovery_action:
            self._log("INFO", f"建议: {recovery_action}")
        self.alarm_raised.emit(message)

    @global_exception_handler.wrap_function
    def start(self) -> None:
        self.backend.update_runtime_config(self.config)
        self.backend.start()
        self._emit_status()

    @global_exception_handler.wrap_function
    def update_config(self, config: RuntimeConfig) -> None:
        if self.workflow_artifacts.session_locked:
            raise AppException(
                "Session is locked, cannot modify runtime config",
                ErrorCategory.LOGIC,
                ErrorSeverity.WARNING,
                "当前会话已锁定，无法修改运行参数",
                "请先解锁会话或创建新实验"
            )
        self.config = config
        self.telemetry.metrics.pressure_target = config.pressure_target
        self.backend.update_runtime_config(config)
        self._log("INFO", "运行时参数已同步。")
        self._emit_status()

    @global_exception_handler.wrap_function
    def connect_robot(self) -> None:
        self._send_or_warn("connect_robot")

    @global_exception_handler.wrap_function
    def disconnect_robot(self) -> None:
        self._send_or_warn("disconnect_robot")
        self.session_service.reset()
        self.localization_result = None
        self.preview_scan_plan = None
        self.workflow_artifacts = WorkflowArtifacts()
        self._emit_status()

    def power_on(self) -> None:
        self._send_or_warn("power_on")

    def power_off(self) -> None:
        self._send_or_warn("power_off")

    def set_auto_mode(self) -> None:
        self._send_or_warn("set_auto_mode")

    def set_manual_mode(self) -> None:
        self._send_or_warn("set_manual_mode")

    def create_experiment(self) -> None:
        reply = self._send_command("validate_setup", workflow_step="create_experiment")
        if not reply.ok:
            self._log("WARN", f"系统自检未通过：{reply.message}")
            return
        record = self.session_service.create_experiment(self.config, note="AppController experiment")
        self.experiments.append(record)
        self.experiments_updated.emit(self.experiments)
        self.localization_result = None
        self.preview_scan_plan = None
        self.workflow_artifacts = WorkflowArtifacts(has_experiment=True, experiment_id=record.exp_id)
        self._log("INFO", f"实验 {record.exp_id} 已创建。当前流程停留在预览阶段，session 尚未锁定。")
        self._emit_status()

    def run_localization(self) -> None:
        if self.session_service.current_experiment is None:
            self._log("WARN", "请先创建实验，再执行视觉定位。")
            return
        self.localization_result = self.plan_service.run_localization(self.session_service.current_experiment, self.config)
        self.workflow_artifacts.localization = self.localization_result.status
        self._log(
            "INFO",
            f"[{self.localization_result.status.implementation}] 视觉定位完成：{self.localization_result.status.detail}",
        )
        self._emit_status()

    def generate_path(self) -> None:
        if self.session_service.current_experiment is None:
            self._log("WARN", "请先创建实验。")
            return
        if self.localization_result is None or not self.localization_result.status.ready:
            self._log("WARN", "请先完成视觉定位。")
            return
        self.preview_scan_plan, status = self.plan_service.build_preview_plan(
            self.session_service.current_experiment,
            self.localization_result,
            self.config,
        )
        preview_path = self.session_service.save_preview_plan(self.preview_scan_plan)
        self.workflow_artifacts.preview_plan_ready = True
        self.workflow_artifacts.preview_plan_id = self.preview_scan_plan.plan_id
        self.workflow_artifacts.preview_plan_hash = self.preview_scan_plan.template_hash()
        self.workflow_artifacts.scan_plan = status
        self.experiments_updated.emit(self.experiments)
        validation = dict(self.preview_scan_plan.validation_summary)
        self._log(
            "INFO",
            f"[{status.implementation}] 扫查路径预览已生成：{status.detail} 预览文件 {preview_path}；segments={validation.get('segment_count', 0)} waypoints={validation.get('total_waypoints', 0)} duration_ms={validation.get('estimated_duration_ms', 0)}",
        )
        self._emit_status()

    def start_scan(self) -> None:
        if self.preview_scan_plan is None:
            self._log("WARN", "请先完成路径生成与预览。")
            return
        try:
            was_locked = self.workflow_artifacts.session_locked
            locked = self.session_service.ensure_locked(
                self.config,
                self.telemetry.device_roster(),
                self.preview_scan_plan,
                protocol_version=1,
                safety_thresholds=load_force_control_config(),
                device_health_snapshot=self.telemetry.device_roster(),
                patient_registration=self.localization_result.patient_registration if self.localization_result else None,
            )
        except RuntimeError as exc:
            self._log("ERROR", str(exc))
            return
        if not was_locked:
            reply = self._send_command(
                "lock_session",
                {
                    "experiment_id": self.session_service.current_experiment.exp_id,
                    "session_id": locked.session_id,
                    "session_dir": str(locked.session_dir),
                    "config_snapshot": self.config.to_dict(),
                    "device_roster": self.telemetry.device_roster(),
                    "software_version": self.config.software_version,
                    "build_id": self.config.build_id,
                    "scan_plan_hash": locked.scan_plan.plan_hash(),
                    "force_sensor_provider": self.config.force_sensor_provider,
                    "protocol_version": 1,
                    "safety_thresholds": load_force_control_config(),
                    "device_health_snapshot": self.telemetry.device_roster(),
                },
                workflow_step="lock_session",
            )
            if not reply.ok:
                self.session_service.rollback_pending_lock(self.preview_scan_plan)
                self._raise_local_alarm(
                    "ERROR",
                    "session",
                    f"锁定会话失败：{reply.message}",
                    workflow_step="lock_session",
                    request_id=reply.request_id,
                    auto_action="rollback_pending_lock",
                )
                self._log("ERROR", f"锁定会话失败：{reply.message}")
                self._emit_status()
                return
            self.workflow_artifacts.session_locked = True
            self.workflow_artifacts.session_id = locked.session_id
            self.workflow_artifacts.session_dir = str(locked.session_dir)
            self._log("INFO", f"会话 {locked.session_id} 已锁定，manifest 不再允许改写语义字段。")
        reply = self._send_command(
            "load_scan_plan",
            {"scan_plan": locked.scan_plan.to_dict()},
            workflow_step="load_scan_plan",
        )
        if not reply.ok:
            self._raise_local_alarm(
                "WARN",
                "planning",
                f"加载扫查路径失败：{reply.message}",
                workflow_step="load_scan_plan",
                request_id=reply.request_id,
            )
            self._log("ERROR", f"加载扫查路径失败：{reply.message}。会话保持锁定以便排查，不执行扫查启动链。")
            self._emit_status()
            return
        for command in ["approach_prescan", "seek_contact", "start_scan"]:
            if not self._run_scan_start_step(command):
                return
        self._log("INFO", "扫查启动链路已完成，系统进入自动扫查流程。")
        self.experiments_updated.emit(self.experiments)
        self._emit_status()

    def pause_scan(self) -> None:
        self._run_guarded_command(
            "pause_scan",
            success_message="扫查已暂停，系统进入保持状态。",
            fallback_to_safe_retreat=True,
        )

    def resume_scan(self) -> None:
        self._run_guarded_command("resume_scan", success_message="扫查已恢复。")

    def stop_scan(self) -> None:
        self._log("INFO", "停止扫查请求已转换为安全退让。")
        self.safe_retreat()

    def safe_retreat(self) -> None:
        self._run_guarded_command("safe_retreat", success_message="安全退让已请求。")

    def go_home(self) -> None:
        self._run_guarded_command("go_home", success_message="回零位请求已发送。")

    def run_preprocess(self) -> None:
        self.workflow_artifacts.preprocess = self.postprocess_service.preprocess(self.session_service.current_session_dir)
        self._log("INFO", f"[{self.workflow_artifacts.preprocess.implementation}] {self.workflow_artifacts.preprocess.detail}")
        self._emit_status()

    def run_reconstruction(self) -> None:
        self.workflow_artifacts.reconstruction = self.postprocess_service.reconstruct(self.session_service.current_session_dir)
        self._log("INFO", f"[{self.workflow_artifacts.reconstruction.implementation}] {self.workflow_artifacts.reconstruction.detail}")
        self._emit_status()

    def run_assessment(self) -> None:
        self.workflow_artifacts.assessment = self.postprocess_service.assess(self.session_service.current_session_dir)
        self._log("INFO", f"[{self.workflow_artifacts.assessment.implementation}] {self.workflow_artifacts.assessment.detail}")
        self._emit_status()

    def save_results(self) -> None:
        try:
            path = self.session_service.save_summary(self._build_summary_payload())
        except RuntimeError as exc:
            self._log("WARN", str(exc))
            return
        self._refresh_session_products()
        self._log("INFO", f"会话摘要已保存到 {path}")

    def export_summary(self) -> None:
        if self.session_service.current_experiment is None:
            self._log("WARN", "当前没有可导出的实验摘要。")
            return
        try:
            path = self.session_service.export_summary(
                "Spine Ultrasound Session Summary",
                [
                    f"Experiment: {self.session_service.current_experiment.exp_id}",
                    f"Session: {self.session_service.current_experiment.session_id or '-'}",
                    f"Core state: {self.telemetry.core_state.execution_state}",
                    f"Pressure: {self.telemetry.metrics.pressure_current:.2f} / {self.telemetry.metrics.pressure_target:.2f} N",
                    f"Contact: {self.telemetry.metrics.contact_mode} ({self.telemetry.metrics.contact_confidence:.2f})",
                    f"Progress: {self.telemetry.metrics.scan_progress:.1f}%",
                    f"Quality: {self.telemetry.metrics.quality_score:.2f}",
                    f"Safety: safe_to_scan={self.telemetry.safety_status.safe_to_scan}",
                ],
            )
        except RuntimeError as exc:
            self._log("WARN", str(exc))
            return
        self._refresh_session_products()
        self._log("INFO", f"文本摘要已导出到 {path}")

    def emergency_stop(self) -> None:
        self._run_guarded_command("emergency_stop", success_message="急停请求已发送。")

    def shutdown(self) -> None:
        self.backend.close()

    def _connect_backend(self) -> None:
        self.backend.telemetry_received.connect(self._handle_telemetry)
        if hasattr(self.backend, "log_generated"):
            self.backend.log_generated.connect(self._forward_log)
        if hasattr(self.backend, "camera_pixmap_ready"):
            self.backend.camera_pixmap_ready.connect(self._on_camera_pixmap)
        if hasattr(self.backend, "ultrasound_pixmap_ready"):
            self.backend.ultrasound_pixmap_ready.connect(self._on_ultrasound_pixmap)
        if hasattr(self.backend, "reconstruction_pixmap_ready"):
            self.backend.reconstruction_pixmap_ready.connect(self.reconstruction_pixmap_ready.emit)

    def _handle_telemetry(self, env: TelemetryEnvelope) -> None:
        alarm = self.telemetry.apply(env)
        if env.topic == "quality_feedback":
            self.session_service.record_quality_feedback(env.data, env.ts_ns)
            if float(env.data.get("quality_score", 1.0)) < 0.75:
                self.session_service.record_annotation(
                    kind="quality_issue",
                    message=f"quality_score={float(env.data.get('quality_score', 0.0)):.2f}",
                    ts_ns=env.ts_ns,
                    segment_id=self.telemetry.core_state.active_segment,
                    severity="WARN",
                    tags=["quality", "review"],
                )
        if alarm is not None:
            self.alarm_manager.push(
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
            self.alarm_raised.emit(f"{alarm['severity']}/{alarm['source']}: {alarm['message']} ({trace})")
            self.session_service.record_annotation(
                kind="alarm",
                message=alarm["message"],
                ts_ns=alarm["event_ts_ns"],
                segment_id=alarm.get("segment_id", 0),
                severity=alarm["severity"],
                tags=[alarm["source"], alarm.get("workflow_step", "")],
            )
            self.log_generated.emit(
                alarm["severity"],
                f"[{now_text()}] [{alarm['source']}] {alarm['message']} ({trace})",
            )
        if self.session_service.current_experiment is not None:
            self.session_service.current_experiment.state = self.telemetry.core_state.execution_state
        self._emit_status()

    def _on_camera_pixmap(self, pixmap: QPixmap) -> None:
        self.session_service.record_camera_pixmap(pixmap)
        self.camera_pixmap_ready.emit(pixmap)

    def _on_ultrasound_pixmap(self, pixmap: QPixmap) -> None:
        self.session_service.record_ultrasound_pixmap(pixmap)
        self.ultrasound_pixmap_ready.emit(pixmap)

    def _forward_log(self, level: str, message: str) -> None:
        self.log_generated.emit(level, message)

    def _send_or_warn(self, command: str, payload: Optional[dict] = None) -> ReplyEnvelope:
        reply = self._send_command(command, payload, workflow_step=command)
        if not reply.ok:
            self._log("WARN", f"{command} 失败：{reply.message}")
        return reply

    def _run_guarded_command(
        self,
        command: str,
        payload: Optional[dict] = None,
        *,
        success_message: Optional[str] = None,
        fallback_to_safe_retreat: bool = False,
    ) -> bool:
        reply = self._send_command(command, payload, workflow_step=command)
        if reply.ok:
            self.session_service.record_annotation(
                kind="workflow",
                message=f"{command} ok",
                segment_id=self.telemetry.core_state.active_segment,
                severity="INFO",
                tags=[command],
            )
            if success_message:
                self._log("INFO", success_message)
            self._emit_status()
            return True
        self.session_service.record_annotation(
            kind="workflow_failure",
            message=f"{command} failed: {reply.message}",
            segment_id=self.telemetry.core_state.active_segment,
            severity="ERROR",
            tags=[command, "retry" if fallback_to_safe_retreat else "manual"],
        )
        self._log("ERROR", f"{command} 失败：{reply.message}")
        self._raise_local_alarm("ERROR", "workflow", f"{command} 失败：{reply.message}", workflow_step=command, request_id=reply.request_id)
        if fallback_to_safe_retreat:
            self._request_safe_retreat_after_failure(command)
        self._emit_status()
        return False

    def _run_scan_start_step(self, command: str) -> bool:
        return self._run_guarded_command(command, fallback_to_safe_retreat=True)

    def _request_safe_retreat_after_failure(self, failed_command: str) -> None:
        retreat = self._send_command("safe_retreat", workflow_step=failed_command, auto_action="safe_retreat")
        if retreat.ok:
            self._log("WARN", f"{failed_command} 失败后已自动请求安全退让。")
            self._raise_local_alarm(
                "WARN",
                "workflow",
                f"{failed_command} 失败后已自动请求安全退让。",
                workflow_step=failed_command,
                request_id=retreat.request_id,
                auto_action="safe_retreat",
            )
        else:
            self._log("ERROR", f"{failed_command} 失败后安全退让也失败：{retreat.message}")
            self._raise_local_alarm(
                "ERROR",
                "workflow",
                f"{failed_command} 失败后安全退让也失败：{retreat.message}",
                workflow_step=failed_command,
                request_id=retreat.request_id,
                auto_action="safe_retreat_failed",
            )

    def _build_summary_payload(self) -> dict:
        return {
            "saved_at": now_text(),
            "core_state": self.telemetry.core_state.execution_state,
            "experiment": asdict(self.session_service.current_experiment) if self.session_service.current_experiment else None,
            "metrics": {
                "pressure_current": self.telemetry.metrics.pressure_current,
                "pressure_target": self.telemetry.metrics.pressure_target,
                "pressure_error": self.telemetry.metrics.pressure_error,
                "frame_id": self.telemetry.metrics.frame_id,
                "path_index": self.telemetry.metrics.path_index,
                "segment_id": self.telemetry.metrics.segment_id,
                "image_quality": self.telemetry.metrics.image_quality,
                "feature_confidence": self.telemetry.metrics.feature_confidence,
                "quality_score": self.telemetry.metrics.quality_score,
                "scan_progress": self.telemetry.metrics.scan_progress,
                "contact_mode": self.telemetry.metrics.contact_mode,
                "contact_confidence": self.telemetry.metrics.contact_confidence,
                "recommended_action": self.telemetry.metrics.recommended_action,
                "tcp_pose": asdict(self.telemetry.metrics.tcp_pose),
                "joint_pos": self.telemetry.metrics.joint_pos,
                "joint_vel": self.telemetry.metrics.joint_vel,
                "joint_torque": self.telemetry.metrics.joint_torque,
                "cart_force": self.telemetry.metrics.cart_force,
            },
            "robot": {
                **dict(self.telemetry.robot),
                "robot_model": self.config.robot_model,
                "axis_count": self.config.axis_count,
                "sdk_robot_class": self.config.sdk_robot_class,
            },
            "safety": asdict(self.telemetry.safety_status),
            "recording": asdict(self.telemetry.recorder_status),
            "workflow": self.workflow_artifacts.to_dict(),
            "planning": self.preview_scan_plan.to_dict() if self.preview_scan_plan is not None else {},
            "localization": {
                "registration_hash": self.localization_result.registration_hash() if self.localization_result is not None else "",
                "confidence": self.localization_result.confidence if self.localization_result is not None else 0.0,
                "registration_version": self.localization_result.registration_version if self.localization_result is not None else "",
            },
        }

    def _emit_status(self) -> None:
        payload = self.view_factory.build(
            self.telemetry,
            self.config,
            self.workflow_artifacts,
            self.session_service.current_experiment,
        ).to_dict()
        self.status_updated.emit(payload)
        self.system_state_changed.emit(self.telemetry.core_state.execution_state)

    def _log(self, level: str, message: str) -> None:
        self.log_generated.emit(level, f"[{now_text()}] {message}")

    def _send_command(
        self,
        command: str,
        payload: Optional[dict] = None,
        *,
        workflow_step: str,
        auto_action: str = "",
    ) -> ReplyEnvelope:
        reply = self.backend.send_command(command, payload)
        self.session_service.record_command_journal(
            source="desktop",
            command=command,
            payload=payload or {},
            reply={
                "ok": reply.ok,
                "message": reply.message,
                "request_id": reply.request_id,
                "data": dict(reply.data),
                "ts_ns": now_ns(),
            },
            workflow_step=workflow_step,
            auto_action=auto_action,
        )
        return reply

    def _raise_local_alarm(
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
        self.alarm_manager.push(
            severity,
            source,
            message,
            auto_action_taken=auto_action,
            workflow_step=workflow_step,
            request_id=request_id,
            event_ts_ns=event_ts_ns,
        )
        trace = f"step={workflow_step or '-'} request={request_id or '-'} auto={auto_action or '-'} ts={event_ts_ns}"
        self.alarm_raised.emit(f"{severity}/{source}: {message} ({trace})")
        self.log_generated.emit(severity, f"[{now_text()}] [{source}] {message} ({trace})")

    def _refresh_session_products(self) -> None:
        statuses = self.postprocess_service.refresh_all(self.session_service.current_session_dir)
        self.workflow_artifacts.preprocess = statuses["preprocess"]
        self.workflow_artifacts.reconstruction = statuses["reconstruction"]
        self.workflow_artifacts.assessment = statuses["assessment"]
        self.session_service.refresh_session_intelligence()
