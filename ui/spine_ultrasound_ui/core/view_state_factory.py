from __future__ import annotations

from dataclasses import asdict
from typing import Any

from spine_ultrasound_ui.core.telemetry_store import TelemetryStore
from spine_ultrasound_ui.core.workflow_state_machine import WorkflowContext, WorkflowStateMachine
from spine_ultrasound_ui.models import RuntimeConfig, SystemState, UiViewState, WorkflowArtifacts
from spine_ultrasound_ui.services.sdk_capability_service import SdkCapabilityService
from spine_ultrasound_ui.services.runtime_governance_query_surface import RuntimeGovernanceQuerySurface


class ViewStateFactory:
    def __init__(self, workflow: WorkflowStateMachine | None = None, sdk_service: SdkCapabilityService | None = None, governance_projection: RuntimeGovernanceQuerySurface | None = None) -> None:
        self.workflow = workflow or WorkflowStateMachine()
        self.sdk_service = sdk_service or SdkCapabilityService()
        self.governance_projection = governance_projection or RuntimeGovernanceQuerySurface()

    def build(
        self,
        telemetry: TelemetryStore,
        config: RuntimeConfig,
        workflow_artifacts: WorkflowArtifacts,
        current_experiment,
        *,
        sdk_runtime: dict | None = None,
        model_report: dict | None = None,
        config_report: dict | None = None,
        backend_link: dict | None = None,
        bridge_observability: dict | None = None,
        control_plane_snapshot: dict | None = None,
    ) -> UiViewState:
        resolved_control_plane_snapshot = self._resolve_control_plane_snapshot(
            control_plane_snapshot=control_plane_snapshot,
            backend_link=backend_link,
            bridge_observability=bridge_observability,
            model_report=model_report,
            config_report=config_report,
            governance_projection=self.governance_projection.build_projection(
                backend_link=backend_link or {},
                control_plane_snapshot=control_plane_snapshot or {},
                model_report=model_report or {},
            ),
        )
        context = WorkflowContext(
            core_state=SystemState(telemetry.core_state.execution_state),
            has_experiment=workflow_artifacts.has_experiment,
            session_locked=workflow_artifacts.session_locked,
            localization_ready=workflow_artifacts.localization.ready,
            localization_review_required=workflow_artifacts.localization_review_required,
            localization_review_approved=workflow_artifacts.localization_review_approved,
            preview_plan_ready=workflow_artifacts.preview_plan_ready,
        )
        actions = self.workflow.permission_matrix(context)
        permissions = {name: bool(rule["enabled"]) for name, rule in actions.items()}
        readiness = self._build_readiness(telemetry, workflow_artifacts, current_experiment, actions, resolved_control_plane_snapshot)
        sdk_alignment = self.sdk_service.build(config, telemetry.robot)
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
            actions=actions,
            readiness=readiness,
            sdk_alignment=sdk_alignment,
            sdk_runtime=dict(sdk_runtime or {}),
            model_report=dict(model_report or {}),
            backend_link=dict(backend_link or {}),
            bridge_observability=dict(bridge_observability or {}),
        )

    @staticmethod
    def _resolve_control_plane_snapshot(
        *,
        control_plane_snapshot: dict | None,
        backend_link: dict | None,
        bridge_observability: dict | None,
        model_report: dict | None,
        config_report: dict | None,
        governance_projection: dict[str, Any],
    ) -> dict[str, Any]:
        if control_plane_snapshot:
            snapshot = dict(control_plane_snapshot)
            snapshot.setdefault("authoritative_projection", dict(governance_projection))
            snapshot.setdefault("ownership_state", dict(governance_projection.get("control_authority", snapshot.get("ownership_state", {}))))
            snapshot.setdefault("model_precheck", dict(governance_projection.get("model_precheck", snapshot.get("model_precheck", {}))))
            return snapshot
        backend_link = dict(backend_link or {})
        bridge_observability = dict(bridge_observability or {})
        model_report = dict(model_report or {})
        config_report = dict(config_report or {})
        if not any((backend_link, bridge_observability, model_report, config_report)):
            return {}
        control_plane = dict(backend_link.get("control_plane", {}))
        return {
            "summary_state": backend_link.get("summary_state", "unknown"),
            "detail": backend_link.get("detail", "控制面状态未提供。"),
            "protocol_version": dict(control_plane.get("protocol_status", {})),
            "config_consistency": dict(control_plane.get("config_sync", {})),
            "ownership_state": dict(governance_projection.get("control_authority", control_plane.get("control_authority", {}))),
            "bridge_observability_state": bridge_observability,
            "model_precheck": dict(governance_projection.get("model_precheck", model_report)),
            "authoritative_projection": dict(governance_projection),
            "config_baseline": config_report,
        }

    def _build_readiness(
        self,
        telemetry: TelemetryStore,
        workflow_artifacts: WorkflowArtifacts,
        current_experiment,
        actions: dict[str, dict[str, str | bool]],
        control_plane_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        control_plane = dict(control_plane_snapshot or {})
        workflow_checks = self._workflow_checks(telemetry, workflow_artifacts, current_experiment)
        governance = dict(control_plane.get("governance_readiness", {}))
        governance_checks = self._governance_checks(control_plane)
        checks = workflow_checks + governance_checks
        passed = sum(1 for item in checks if item["ready"])
        recommended_command = self._pick_recommended_command(actions)
        blockers = [item["name"] for item in workflow_checks if not item["ready"]]
        blockers.extend(item.get("name", item.get("section", "blocker")) for item in governance.get("blockers", []))
        workflow_percent = int(round((sum(1 for item in workflow_checks if item["ready"]) / len(workflow_checks)) * 100)) if workflow_checks else 0
        governance_percent = int(governance.get("percent", 0 if governance_checks else 100))
        combined_percent = int(round(((workflow_percent + governance_percent) / 2))) if governance_checks else workflow_percent
        return {
            "percent": combined_percent,
            "passed": passed,
            "total": len(checks),
            "checks": checks,
            "blockers": blockers,
            "governance_blockers": list(governance.get("blockers", control_plane.get("blockers", []))),
            "governance_warnings": list(governance.get("warnings", control_plane.get("warnings", []))),
            "operator_hints": list(governance.get("operator_hints", control_plane.get("operator_hints", []))),
            "governance_summary_state": governance.get("summary_state", control_plane.get("summary_state", "unknown")),
            "recommended_command": recommended_command,
            "recommended_label": self.workflow.ACTION_LABELS.get(recommended_command, "等待系统满足条件") if recommended_command else "等待系统满足条件",
            "recommended_reason": actions.get(recommended_command, {}).get("reason", "请先排除阻塞项。") if recommended_command else "请先排除阻塞项。",
            "recommended_tab": self._recommended_tab(recommended_command),
        }

    def _workflow_checks(self, telemetry, workflow_artifacts, current_experiment) -> list[dict[str, Any]]:
        return [
            self._check("机器人已连接", telemetry.devices["robot"].connected, telemetry.devices["robot"].detail),
            self._check("系统已上电", bool(telemetry.robot.get("powered", False)), "机器人需要处于上电状态。"),
            self._check("自动模式", str(telemetry.robot.get("operate_mode", "manual")).lower() == "automatic", "切换到自动模式后才能进入正式扫查流程。"),
            self._check("实验已创建", workflow_artifacts.has_experiment and current_experiment is not None, "请先创建实验。"),
            self._check("视觉定位完成", workflow_artifacts.localization.ready, workflow_artifacts.localization.detail or "请先执行视觉定位。"),
            self._check("视觉引导复核已批准", (not workflow_artifacts.localization_review_required) or workflow_artifacts.localization_review_approved, "当前视觉引导结果需要人工复核批准。" if workflow_artifacts.localization_review_required and not workflow_artifacts.localization_review_approved else "当前无需人工复核或已批准。"),
            self._check("路径预览完成", workflow_artifacts.preview_plan_ready, workflow_artifacts.scan_plan.detail or "请先生成并确认路径。"),
            self._check("安全联锁通过", telemetry.safety_status.safe_to_scan, self._safety_detail(telemetry.safety_status.active_interlocks)),
        ]

    def _governance_checks(self, control_plane: dict[str, Any]) -> list[dict[str, Any]]:
        if not control_plane:
            return [self._check("控制面快照可用", False, "尚未建立 control_plane_snapshot。")]
        authoritative_projection = dict(control_plane.get("authoritative_projection", {}))
        sections = {
            "模型前检通过": dict(authoritative_projection.get("model_precheck", control_plane.get("model_precheck", {}))),
            "前后端链路在线": {"summary_state": control_plane.get("summary_state", "unknown"), "detail": control_plane.get("detail", "控制面状态未提供。")},
            "前后端配置一致": dict(control_plane.get("config_consistency", {})),
            "控制面协议一致": dict(control_plane.get("protocol_version", {})),
            "唯一控制权已锁定": dict(authoritative_projection.get("control_authority", control_plane.get("ownership_state", {}))),
            "桥接观测契约正常": dict(control_plane.get("bridge_observability_state", {})),
        }
        checks: list[dict[str, Any]] = []
        for name, summary in sections.items():
            state = str(summary.get("summary_state", "unknown"))
            ready = state == "ready" if name == "唯一控制权已锁定" else state not in {"blocked"}
            checks.append(self._check(name, ready, str(summary.get("detail", "控制面未提供该摘要。"))))
        return checks

    @staticmethod
    def _check(name: str, ready: bool, detail: str) -> dict[str, Any]:
        return {"name": name, "ready": bool(ready), "detail": detail}

    @staticmethod
    def _safety_detail(interlocks: list[str]) -> str:
        if not interlocks:
            return "未检测到活动联锁。"
        return "当前活动联锁：" + ", ".join(interlocks)

    @staticmethod
    def _pick_recommended_command(actions: dict[str, dict[str, str | bool]]) -> str | None:
        preferred_order = [
            "connect_robot", "power_on", "set_auto_mode", "create_experiment", "run_localization", "approve_localization_review", "generate_path",
            "refresh_sdk_assets", "start_scan", "run_preprocess", "run_reconstruction", "run_assessment", "export_summary",
        ]
        for name in preferred_order:
            if actions.get(name, {}).get("enabled"):
                return name
        return None

    @staticmethod
    def _recommended_tab(command: str | None) -> str:
        mapping = {
            "connect_robot": "系统准备", "power_on": "系统准备", "set_auto_mode": "系统准备", "create_experiment": "实验配置",
            "run_localization": "视觉与路径", "approve_localization_review": "视觉与路径", "generate_path": "视觉与路径", "refresh_sdk_assets": "机器人监控",
            "start_scan": "自动扫查", "run_preprocess": "图像与重建", "run_reconstruction": "图像与重建",
            "run_assessment": "量化评估", "export_summary": "系统总览",
        }
        return mapping.get(command, "系统总览")
