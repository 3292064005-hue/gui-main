from __future__ import annotations

from typing import Any, Protocol

from spine_ultrasound_ui.models import WorkflowArtifacts
from spine_ultrasound_ui.services.force_control_config import load_force_control_config
from spine_ultrasound_ui.services.scan_plan_contract import runtime_scan_plan_payload


class AppWorkflowHost(Protocol):
    config: Any
    telemetry: Any
    workflow_artifacts: WorkflowArtifacts
    experiments: list[Any]
    localization_result: Any
    preview_scan_plan: Any
    execution_scan_plan: Any
    model_report: dict[str, Any]
    config_report: dict[str, Any]
    backend_link_snapshot: dict[str, Any]
    sdk_runtime_snapshot: dict[str, Any]
    session_service: Any
    session_facade: Any
    plan_service: Any
    postprocess_service: Any
    config_profile_service: Any
    runtime_verdict_service: Any
    control_plane_reader: Any
    experiments_updated: Any

    def _send_command(self, command: str, payload: dict[str, Any] | None = None, *, workflow_step: str, auto_action: str = "") -> Any: ...
    def _run_scan_start_step(self, command: str) -> bool: ...
    def _run_guarded_command(
        self,
        command: str,
        payload: dict[str, Any] | None = None,
        *,
        success_message: str | None = None,
        fallback_to_safe_retreat: bool = False,
    ) -> bool: ...
    def _raise_local_alarm(
        self,
        severity: str,
        source: str,
        message: str,
        *,
        workflow_step: str,
        request_id: str = "",
        auto_action: str = "",
    ) -> None: ...
    def _refresh_governance(self, *, force_sdk_assets: bool = False) -> None: ...
    def _refresh_session_governance(self) -> None: ...
    def _refresh_session_products(self) -> None: ...
    def _refresh_sdk_assets(self, *, force: bool = False) -> None: ...
    def _build_summary_payload(self) -> dict[str, Any]: ...
    def _log(self, level: str, message: str) -> None: ...
    def _emit_status(self) -> None: ...


def create_experiment(host: AppWorkflowHost) -> None:
    reply = host._send_command("validate_setup", workflow_step="create_experiment")
    if not reply.ok:
        host._log("WARN", f"系统自检未通过：{reply.message}")
        return
    record = host.session_facade.create_experiment(host.config, note="AppController experiment")
    host.experiments.append(record)
    host.experiments_updated.emit(host.experiments)
    host.localization_result = None
    host.preview_scan_plan = None
    host.execution_scan_plan = None
    host.model_report = {}
    host.workflow_artifacts = WorkflowArtifacts(has_experiment=True, experiment_id=record.exp_id)
    host._refresh_governance(force_sdk_assets=False)
    host._log("INFO", f"实验 {record.exp_id} 已创建。当前流程停留在预览阶段，session 尚未锁定。")
    host._emit_status()


def run_localization(host: AppWorkflowHost) -> None:
    if host.session_service.current_experiment is None:
        host._log("WARN", "请先创建实验，再执行视觉定位。")
        return
    host.localization_result = host.plan_service.run_localization(host.session_service.current_experiment, host.config)
    host.workflow_artifacts.localization = host.localization_result.status
    host._log(
        "INFO",
        f"[{host.localization_result.status.implementation}] 视觉定位完成：{host.localization_result.status.detail}",
    )
    host._emit_status()


def generate_path(host: AppWorkflowHost) -> None:
    if host.session_service.current_experiment is None:
        host._log("WARN", "请先创建实验。")
        return
    if host.localization_result is None or not host.localization_result.status.ready:
        host._log("WARN", "请先完成视觉定位。")
        return
    host.preview_scan_plan, status = host.plan_service.build_preview_plan(
        host.session_service.current_experiment,
        host.localization_result,
        host.config,
    )
    host.execution_scan_plan = host.plan_service.build_execution_plan(
        host.preview_scan_plan,
        config=host.config,
    )
    host.config_report = host.config_profile_service.build_report(host.config)
    host.model_report = host.runtime_verdict_service.resolve(host.backend, host.execution_scan_plan, host.config)
    preview_path = host.session_service.save_preview_plan(host.preview_scan_plan)
    host.workflow_artifacts.preview_plan_ready = True
    host.workflow_artifacts.preview_plan_id = host.preview_scan_plan.plan_id
    host.workflow_artifacts.preview_plan_hash = host.preview_scan_plan.template_hash()
    host.workflow_artifacts.scan_plan = status
    host.experiments_updated.emit(host.experiments)
    validation = dict(host.preview_scan_plan.validation_summary)
    selected_profile = host.execution_scan_plan.validation_summary.get("execution_profile", "-") if host.execution_scan_plan else "-"
    model_state = host.model_report.get("summary_label", "未校验")
    host._log(
        "INFO",
        f"[{status.implementation}] 扫查路径预览已生成：{status.detail} 预览文件 {preview_path}；segments={validation.get('segment_count', 0)} waypoints={validation.get('total_waypoints', 0)} duration_ms={validation.get('estimated_duration_ms', 0)}；execution_profile={selected_profile}；model={model_state}",
    )
    host._refresh_governance(force_sdk_assets=False)
    host._emit_status()


def start_scan(host: AppWorkflowHost) -> None:
    if host.preview_scan_plan is None:
        host._log("WARN", "请先完成路径生成与预览。")
        return
    host._refresh_governance(force_sdk_assets=False)
    blockers = host.control_plane_reader.collect_startup_blockers()
    if blockers:
        host._log("ERROR", "启动前治理检查未通过，禁止启动扫查。")
        for item in blockers:
            host._log("WARN", f"[{str(item.get('section', 'gate')).upper()} BLOCK] {item.get('name')}: {item.get('detail')}")
        host._emit_status()
        return
    try:
        was_locked = host.workflow_artifacts.session_locked
        locked = host.session_service.ensure_locked(
            host.config,
            host.telemetry.device_roster(),
            host.execution_scan_plan or host.preview_scan_plan,
            protocol_version=1,
            safety_thresholds=load_force_control_config(),
            device_health_snapshot=host.telemetry.device_roster(),
            patient_registration=host.localization_result.patient_registration if host.localization_result else None,
            control_authority=dict(host.backend_link_snapshot.get("control_plane", {}).get("control_authority", {})),
        )
    except RuntimeError as exc:
        host._log("ERROR", str(exc))
        return
    if not was_locked:
        reply = host._send_command(
            "lock_session",
            {
                "experiment_id": host.session_service.current_experiment.exp_id,
                "session_id": locked.session_id,
                "session_dir": str(locked.session_dir),
                "config_snapshot": host.config.to_dict(),
                "device_roster": host.telemetry.device_roster(),
                "software_version": host.config.software_version,
                "build_id": host.config.build_id,
                "scan_plan_hash": locked.scan_plan.plan_hash(),
                "force_sensor_provider": host.config.force_sensor_provider,
                "protocol_version": 1,
                "safety_thresholds": load_force_control_config(),
                "device_health_snapshot": host.telemetry.device_roster(),
            },
            workflow_step="lock_session",
        )
        if not reply.ok:
            host.session_service.rollback_pending_lock(host.preview_scan_plan)
            host._raise_local_alarm(
                "ERROR",
                "session",
                f"锁定会话失败：{reply.message}",
                workflow_step="lock_session",
                request_id=reply.request_id,
                auto_action="rollback_pending_lock",
            )
            host._log("ERROR", f"锁定会话失败：{reply.message}")
            host._emit_status()
            return
        host.workflow_artifacts.session_locked = True
        host.workflow_artifacts.session_id = locked.session_id
        host.workflow_artifacts.session_dir = str(locked.session_dir)
        host._log("INFO", f"会话 {locked.session_id} 已锁定，manifest 不再允许改写语义字段。")
    runtime_plan = locked.scan_plan
    host.execution_scan_plan = runtime_plan
    reply = host._send_command(
        "load_scan_plan",
        {"scan_plan": runtime_scan_plan_payload(runtime_plan)},
        workflow_step="load_scan_plan",
    )
    if not reply.ok:
        host._raise_local_alarm(
            "WARN",
            "planning",
            f"加载扫查路径失败：{reply.message}",
            workflow_step="load_scan_plan",
            request_id=reply.request_id,
        )
        host._log("ERROR", f"加载扫查路径失败：{reply.message}。会话保持锁定以便排查，不执行扫查启动链。")
        host._emit_status()
        return
    for command in ["approach_prescan", "seek_contact", "start_scan"]:
        if not host._run_scan_start_step(command):
            return
    host._log("INFO", "扫查启动链路已完成，系统进入自动扫查流程。")
    host._refresh_session_governance()
    host.experiments_updated.emit(host.experiments)
    host._emit_status()


def run_postprocess(host: AppWorkflowHost, stage: str) -> None:
    if stage == "preprocess":
        host.workflow_artifacts.preprocess = host.postprocess_service.preprocess(host.session_service.current_session_dir)
        result = host.workflow_artifacts.preprocess
    elif stage == "reconstruction":
        host.workflow_artifacts.reconstruction = host.postprocess_service.reconstruct(host.session_service.current_session_dir)
        result = host.workflow_artifacts.reconstruction
    elif stage == "assessment":
        host.workflow_artifacts.assessment = host.postprocess_service.assess(host.session_service.current_session_dir)
        result = host.workflow_artifacts.assessment
    else:
        raise ValueError(f"Unsupported postprocess stage: {stage}")
    host._refresh_session_governance()
    host._log("INFO", f"[{result.implementation}] {result.detail}")
    host._emit_status()


def save_results(host: AppWorkflowHost) -> None:
    try:
        path = host.session_service.save_summary(host._build_summary_payload())
    except RuntimeError as exc:
        host._log("WARN", str(exc))
        return
    host._refresh_session_products()
    host._refresh_session_governance()
    host._log("INFO", f"会话摘要已保存到 {path}")


def export_summary(host: AppWorkflowHost) -> None:
    if host.session_service.current_experiment is None:
        host._log("WARN", "当前没有可导出的实验摘要。")
        return
    try:
        path = host.session_service.export_summary(
            "Spine Ultrasound Session Summary",
            [
                f"Experiment: {host.session_service.current_experiment.exp_id}",
                f"Session: {host.session_service.current_experiment.session_id or '-'}",
                f"Core state: {host.telemetry.core_state.execution_state}",
                f"Pressure: {host.telemetry.metrics.pressure_current:.2f} / {host.telemetry.metrics.pressure_target:.2f} N",
                f"Contact: {host.telemetry.metrics.contact_mode} ({host.telemetry.metrics.contact_confidence:.2f})",
                f"Progress: {host.telemetry.metrics.scan_progress:.1f}%",
                f"Quality: {host.telemetry.metrics.quality_score:.2f}",
                f"Safety: safe_to_scan={host.telemetry.safety_status.safe_to_scan}",
            ],
        )
    except RuntimeError as exc:
        host._log("WARN", str(exc))
        return
    host._refresh_session_products()
    host._refresh_session_governance()
    host._log("INFO", f"文本摘要已导出到 {path}")


def refresh_sdk_assets(host: AppWorkflowHost) -> None:
    host._refresh_sdk_assets(force=True)
    host._refresh_session_governance()
    host._log("INFO", "SDK 运行资产已刷新。")
    host._emit_status()


def query_controller_log(host: AppWorkflowHost) -> None:
    host._refresh_sdk_assets(force=True)
    logs = host.sdk_runtime_snapshot.get("controller_logs", [])
    if not logs:
        host._log("WARN", "当前没有可显示的控制器日志。")
        return
    latest = logs[0]
    host._log("INFO", f"控制器日志[{latest.get('level', '-')}] {latest.get('message', '-')}")
    host._emit_status()


def run_sdk_command(host: AppWorkflowHost, command: str, payload: dict[str, Any] | None, success_message: str) -> None:
    host._run_guarded_command(command, payload, success_message=success_message)
    host._refresh_sdk_assets(force=True)
