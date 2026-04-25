from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.core.exception_handler import AppException, ErrorCategory, ErrorSeverity, global_exception_handler
from spine_ultrasound_ui.core import app_workflow_operations as workflow_ops
from spine_ultrasound_ui.models import RuntimeConfig, WorkflowArtifacts
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope, TelemetryEnvelope
from spine_ultrasound_ui.utils import now_text


class AppControllerRuntimeMixin:
    def _connect_exception_handler(self) -> None:
        global_exception_handler.error_occurred.connect(self._on_error_occurred, Qt.QueuedConnection)

    @Slot(str, str, str)
    def _on_error_occurred(self, message: str, severity: str, recovery_action: str) -> None:
        self._log(severity.upper(), f"错误: {message}")
        if recovery_action:
            self._log("INFO", f"建议: {recovery_action}")
        self.alarm_raised.emit(message)

    @global_exception_handler.wrap_function
    def start(self) -> None:
        self.backend.update_runtime_config(self.config)
        self.backend.start()
        self.runtime_bridge.refresh_governance(force_sdk_assets=True)
        if self.runtime_config_path.exists():
            self._log("INFO", f"已加载持久化运行配置：{self.runtime_config_path}")
        self._emit_status()

    @global_exception_handler.wrap_function
    def update_config(self, config: RuntimeConfig) -> None:
        if self.workflow_artifacts.session_locked:
            raise AppException(
                "Session is locked, cannot modify runtime config",
                ErrorCategory.LOGIC,
                ErrorSeverity.WARNING,
                "当前会话已锁定，无法修改运行参数",
                "请先解锁会话或创建新实验",
            )
        self.config = config
        self.telemetry.metrics.pressure_target = config.pressure_target
        self.backend.update_runtime_config(config)
        self.config_service.save(self.runtime_config_path, config)
        self.runtime_bridge.refresh_governance(force_sdk_assets=True)
        self.persistence.write_meta(last_config_save=now_text())
        self._log("INFO", "运行时参数已同步并持久化。")
        self._emit_status()

    @global_exception_handler.wrap_function
    def connect_robot(self) -> None:
        self._send_or_warn("connect_robot")

    @global_exception_handler.wrap_function
    def disconnect_robot(self) -> None:
        self._send_or_warn("disconnect_robot")
        self.session_facade.reset_session()
        self.localization_result = None
        self.preview_scan_plan = None
        self.execution_scan_plan = None
        self.model_report = {}
        self.config_report = self.config_profile_service.build_report(self.config)
        self.workflow_artifacts = WorkflowArtifacts()
        self.runtime_bridge.refresh_sdk_assets(force=True)
        self.runtime_bridge.refresh_session_governance()
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
        workflow_ops.create_experiment(self)

    def run_localization(self) -> None:
        workflow_ops.run_localization(self)

    def generate_path(self) -> None:
        workflow_ops.generate_path(self)

    def approve_localization_review(self, operator_id: str = "operator", adjustments: list[dict] | None = None, reason: str = "manual_guidance_review") -> None:
        workflow_ops.approve_localization_review(self, operator_id=operator_id, adjustments=adjustments, reason=reason)

    def start_procedure(self, procedure: str = "scan") -> None:
        """Start a canonical runtime procedure owned by the execution graph.

        Args:
            procedure: Canonical procedure token. Only ``scan`` is currently
                supported by the desktop workflow surface.

        Returns:
            None. Successful execution delegates to the workflow layer, which
            freezes the session, loads the execution plan, and sends the
            canonical ``start_procedure`` runtime command.

        Raises:
            ValueError: Raised when callers request an unsupported procedure
                token through the desktop controller surface.

        Boundary behavior:
            Active UI/runtime code must enter the workflow through this
            canonical method so permission surfaces and logs resolve to
            ``start_procedure(scan)``. The legacy ``start_scan`` alias is
            retired from the active controller surface.
        """
        normalized_procedure = str(procedure or "").strip().lower()
        if normalized_procedure != "scan":
            raise ValueError(f"unsupported procedure: {procedure}")
        workflow_ops.start_scan_procedure(self)

    def retired_start_scan_alias(self) -> None:
        """Reject the retired legacy start_scan alias.

        Function:
            Provides a deterministic migration failure for accidental legacy
            callers without exposing ``start_scan`` as an active desktop action.
        Args:
            None.
        Returns:
            Never returns normally.
        Raises:
            RuntimeError: Always, with the canonical replacement command.
        Boundary behavior:
            No runtime command is sent and no workflow state is mutated.
        """
        raise RuntimeError("retired command alias: start_scan; use start_procedure(scan)")

    def pause_scan(self) -> None:
        self._run_guarded_command("pause_scan", success_message="扫查已暂停，系统进入保持状态。", fallback_to_safe_retreat=True)

    def resume_scan(self) -> None:
        self._run_guarded_command("resume_scan", success_message="扫查已恢复。")

    def stop_scan(self) -> None:
        """Request an orderly end-of-scan stop owned by the runtime graph.

        Returns:
            None.

        Raises:
            Exceptions raised by the runtime bridge are propagated through the
            normal guarded-command boundary.

        Boundary behavior:
            ``stop_scan`` is not treated as equivalent to ``safe_retreat``.
            The runtime must decide whether an orderly stop can complete the
            active scan chain and transition into a sealed post-scan state.
        """
        self._run_guarded_command("stop_scan", success_message="结束本轮扫查请求已发送。")

    def safe_retreat(self) -> None:
        self._run_guarded_command("safe_retreat", success_message="安全退让已请求。")

    def go_home(self) -> None:
        self._run_guarded_command("go_home", success_message="回零位请求已发送。")

    def run_preprocess(self) -> None:
        workflow_ops.run_postprocess(self, "preprocess")

    def run_reconstruction(self) -> None:
        workflow_ops.run_postprocess(self, "reconstruction")

    def run_assessment(self) -> None:
        workflow_ops.run_postprocess(self, "assessment")

    def save_results(self) -> None:
        workflow_ops.save_results(self)

    def save_summary(self) -> None:
        if self.session_service.current_session_dir is None:
            raise RuntimeError("session is not locked")
        self.session_service.save_summary(self._build_summary_payload())
        self._refresh_session_governance()
        self._emit_status()

    def export_summary(self) -> None:
        workflow_ops.export_summary(self)

    def export_lamina_training_case(self, output_root: str | Path) -> dict:
        return workflow_ops.export_lamina_training_case(self, Path(output_root))

    def export_uca_training_case(self, output_root: str | Path) -> dict:
        return workflow_ops.export_uca_training_case(self, Path(output_root))

    def build_annotation_manifest(self, dataset_root: str | Path) -> dict:
        return workflow_ops.build_annotation_manifest(self, Path(dataset_root))

    def refresh_sdk_assets(self) -> None:
        workflow_ops.refresh_sdk_assets(self)

    def query_controller_log(self) -> None:
        workflow_ops.query_controller_log(self)

    def run_rl_project(self) -> None:
        workflow_ops.run_sdk_command(self, "run_rl_project", {"project": self.config.rl_project_name, "task": self.config.rl_task_name}, "RL 工程运行请求已发送。")

    def pause_rl_project(self) -> None:
        workflow_ops.run_sdk_command(self, "pause_rl_project", None, "RL 工程暂停请求已发送。")

    def enable_drag(self) -> None:
        workflow_ops.run_sdk_command(self, "enable_drag", {"space": "cartesian", "type": "admittance"}, "拖动示教已打开。")

    def disable_drag(self) -> None:
        workflow_ops.run_sdk_command(self, "disable_drag", None, "拖动示教已关闭。")

    def replay_path(self) -> None:
        workflow_ops.run_sdk_command(self, "replay_path", {"name": self.sdk_runtime_snapshot.get("path_library", [{}])[0].get("name", "spine_demo_path"), "rate": 0.5}, "路径回放请求已发送。")

    def emergency_stop(self) -> None:
        self._run_guarded_command("emergency_stop", success_message="急停请求已发送。")

    def shutdown(self) -> None:
        """Release backend-side runtime resources owned by the controller."""
        try:
            self.backend.close()
        except Exception:
            return

    def _connect_backend(self) -> None:
        self.backend.telemetry_received.connect(self._handle_telemetry, Qt.QueuedConnection)
        if hasattr(self.backend, "log_generated"):
            self.backend.log_generated.connect(self._forward_log, Qt.QueuedConnection)
        capabilities = self.backend.media_capabilities() if hasattr(self.backend, "media_capabilities") else {"camera": True, "ultrasound": True, "reconstruction": True}
        if capabilities.get("camera", False) and hasattr(self.backend, "camera_pixmap_ready"):
            self.backend.camera_pixmap_ready.connect(self._on_camera_pixmap, Qt.QueuedConnection)
        if capabilities.get("ultrasound", False) and hasattr(self.backend, "ultrasound_pixmap_ready"):
            self.backend.ultrasound_pixmap_ready.connect(self._on_ultrasound_pixmap, Qt.QueuedConnection)
        if capabilities.get("reconstruction", False) and hasattr(self.backend, "reconstruction_pixmap_ready"):
            self.backend.reconstruction_pixmap_ready.connect(self.reconstruction_pixmap_ready.emit, Qt.QueuedConnection)

    @Slot(object)
    def _handle_telemetry(self, env: TelemetryEnvelope) -> None:
        self.runtime_bridge.handle_telemetry(env)

    @Slot(QPixmap)
    def _on_camera_pixmap(self, pixmap: QPixmap) -> None:
        self.runtime_bridge.on_camera_pixmap(pixmap)

    @Slot(QPixmap)
    def _on_ultrasound_pixmap(self, pixmap: QPixmap) -> None:
        self.runtime_bridge.on_ultrasound_pixmap(pixmap)

    @Slot(str, str)
    def _forward_log(self, level: str, message: str) -> None:
        self.log_generated.emit(level, message)

    def _send_or_warn(self, command: str, payload: Optional[dict] = None) -> ReplyEnvelope:
        return self.runtime_bridge.send_or_warn(command, payload)

    def _run_guarded_command(self, command: str, payload: Optional[dict] = None, *, success_message: Optional[str] = None, fallback_to_safe_retreat: bool = False) -> bool:
        return self.runtime_bridge.run_guarded_command(command, payload, success_message=success_message, fallback_to_safe_retreat=fallback_to_safe_retreat)

    def _run_scan_start_step(self, command: str, payload: Optional[dict] = None) -> bool:
        """Run the canonical procedure entry without desktop-owned recovery injection.

        The runtime owns internal phase execution and any recovery action that
        follows from those phases. Desktop keeps only the observable projection
        and must not synthesize a second ``safe_retreat`` write after
        ``start_procedure(scan)`` has already been handed over.
        """
        return self.runtime_bridge.run_guarded_command(
            command,
            payload,
            fallback_to_safe_retreat=False,
            force_asset_refresh=False,
        )

    def _request_safe_retreat_after_failure(self, failed_command: str) -> None:
        self.runtime_bridge.request_safe_retreat_after_failure(failed_command)

    def _build_summary_payload(self) -> dict:
        return self.runtime_bridge.build_summary_payload()

    def _sync_control_plane_snapshots(self, snapshots: dict[str, dict]) -> None:
        self.sdk_runtime_snapshot = dict(snapshots["sdk_runtime"])
        self.config_report = dict(snapshots["config_report"])
        if self.execution_scan_plan is not None:
            self.model_report = dict(snapshots["model_report"])
        self.backend_link_snapshot = dict(snapshots["backend_link"])
        self.bridge_observability_snapshot = dict(snapshots["bridge_observability"])
        self.session_governance_snapshot = dict(snapshots["session_governance"])
        self.deployment_profile_snapshot = dict(snapshots["deployment_profile"])
        self.control_plane_snapshot = dict(snapshots["control_plane_snapshot"])

    def _refresh_governance(self, *, force_sdk_assets: bool = False) -> None:
        self.runtime_bridge.refresh_governance(force_sdk_assets=force_sdk_assets)

    def _refresh_sdk_assets(self, *, force: bool = False) -> None:
        self.runtime_bridge.refresh_sdk_assets(force=force)

    def _refresh_session_governance(self) -> None:
        self.runtime_bridge.refresh_session_governance()

    def _refresh_backend_link(self) -> None:
        self.runtime_bridge.refresh_backend_link()

    def _refresh_bridge_observability(self) -> None:
        self.runtime_bridge.refresh_bridge_observability()

    def _emit_status(self) -> None:
        """Emit the already-materialized status projection.

        Boundary behaviour:
            - This method must stay side-effect-light.
            - It must not trigger governance recomputation, session artifact IO,
              or runtime verdict compilation.
            - Callers needing fresh governance data must refresh the relevant
              projection explicitly before invoking ``_emit_status``.
        """
        payload = self.control_plane_reader.build_status_payload(
            telemetry=self.telemetry,
            config=self.config,
            workflow_artifacts=self.workflow_artifacts,
            current_experiment=self.session_service.current_experiment,
        )
        self.status_updated.emit(payload)
        self.system_state_changed.emit(self.telemetry.core_state.execution_state)

    def _log(self, level: str, message: str) -> None:
        self.log_generated.emit(level, f"[{now_text()}] {message}")

    def _send_command(self, command: str, payload: Optional[dict] = None, *, workflow_step: str, auto_action: str = "") -> ReplyEnvelope:
        return self.command_orchestrator.execute(command, payload, workflow_step=workflow_step, auto_action=auto_action, intent_reason=workflow_step)

    def _raise_local_alarm(self, severity: str, source: str, message: str, *, workflow_step: str, request_id: str = "", auto_action: str = "") -> None:
        self.runtime_bridge.raise_local_alarm(severity, source, message, workflow_step=workflow_step, request_id=request_id, auto_action=auto_action)

    def _refresh_session_products(self) -> None:
        self.runtime_bridge.refresh_session_products()
