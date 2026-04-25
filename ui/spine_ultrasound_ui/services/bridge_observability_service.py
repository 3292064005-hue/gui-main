from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from spine_ultrasound_ui.core.telemetry_store import TelemetryStore
from spine_ultrasound_ui.models import WorkflowArtifacts
from spine_ultrasound_ui.utils import now_ns


@dataclass(frozen=True)
class TopicRequirement:
    name: str
    threshold_ms: int
    required_when: Callable[[str], bool]
    severity: str = "blocker"


class BridgeObservabilityService:
    """Evaluate whether the frontend is observing a trustworthy backend runtime.

    This service deliberately focuses on *observed* runtime behaviour rather than
    declared capability. It uses local telemetry timestamps plus the most recent
    command window reported by the backend link/control plane.
    """

    _ACTIVE_EXECUTION_STATES = {
        "PATH_VALIDATED",
        "APPROACHING",
        "CONTACT_SEEKING",
        "CONTACT_STABLE",
        "SCANNING",
        "PAUSED_HOLD",
        "RETREATING",
        "RECOVERY_RETRACT",
        "SCAN_COMPLETE",
    }
    _SCAN_ACTIVE_STATES = {"CONTACT_SEEKING", "CONTACT_STABLE", "SCANNING", "PAUSED_HOLD", "RETREATING", "RECOVERY_RETRACT"}
    _CONTACT_REQUIRED_STATES = {"CONTACT_SEEKING", "CONTACT_STABLE", "SCANNING", "PAUSED_HOLD", "RETREATING", "RECOVERY_RETRACT"}
    _PROGRESS_REQUIRED_STATES = {"SCANNING", "PAUSED_HOLD", "RETREATING", "RECOVERY_RETRACT", "SCAN_COMPLETE"}
    _QUALITY_RECOMMENDED_STATES = {"SCANNING", "PAUSED_HOLD", "SCAN_COMPLETE"}

    def __init__(self) -> None:
        self.requirements = [
            TopicRequirement("core_state", 1000, lambda _state: True),
            TopicRequirement("robot_state", 1200, lambda _state: True),
            TopicRequirement("safety_status", 1200, lambda _state: True),
            TopicRequirement("contact_state", 1200, lambda state: state in self._CONTACT_REQUIRED_STATES),
            TopicRequirement("scan_progress", 1800, lambda state: state in self._PROGRESS_REQUIRED_STATES),
            TopicRequirement("quality_feedback", 2500, lambda state: state in self._QUALITY_RECOMMENDED_STATES, severity="warning"),
        ]

    def build(
        self,
        telemetry: TelemetryStore,
        backend_link: dict[str, Any] | None,
        workflow_artifacts: WorkflowArtifacts,
    ) -> dict[str, Any]:
        backend_link = dict(backend_link or {})
        control_plane = dict(backend_link.get("control_plane", {}))
        command_window = dict(control_plane.get("command_window", {}))
        recent_commands = list(command_window.get("recent_commands", []))
        execution_state = str(telemetry.core_state.execution_state or "BOOT")

        freshness = self._build_freshness(telemetry, execution_state)
        consistency = self._build_consistency(telemetry, workflow_artifacts)
        command_observability = self._build_command_observability(telemetry, workflow_artifacts, recent_commands)

        blockers: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []
        blockers.extend(freshness["blockers"])
        blockers.extend(consistency["blockers"])
        blockers.extend(command_observability["blockers"])
        warnings.extend(freshness["warnings"])
        warnings.extend(consistency["warnings"])
        warnings.extend(command_observability["warnings"])

        if blockers:
            summary_state = "blocked"
            summary_label = "桥接观测阻塞"
        elif warnings:
            summary_state = "degraded"
            summary_label = "桥接观测降级"
        else:
            summary_state = "ready"
            summary_label = "桥接观测正常"

        detail_parts = [
            f"fresh={freshness['summary_label']}",
            f"state={consistency['summary_label']}",
            f"cmd={command_observability['summary_label']}",
        ]
        if freshness.get("worst_age_ms") is not None:
            detail_parts.append(f"worst_age={freshness['worst_age_ms']}ms")
        if command_observability.get("latest_checked_command"):
            detail_parts.append(f"latest={command_observability['latest_checked_command']}")

        return {
            "summary_state": summary_state,
            "summary_label": summary_label,
            "detail": " / ".join(detail_parts),
            "freshness": freshness,
            "state_consistency": consistency,
            "command_observability": command_observability,
            "blockers": blockers,
            "warnings": warnings,
        }

    def _build_freshness(self, telemetry: TelemetryStore, execution_state: str) -> dict[str, Any]:
        current_ns = now_ns()
        checks: list[dict[str, Any]] = []
        blockers: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []
        worst_age_ms: int | None = None
        for requirement in self.requirements:
            if not requirement.required_when(execution_state):
                continue
            ts_ns = int(telemetry.topic_timestamps_ns.get(requirement.name, 0) or 0)
            if ts_ns <= 0:
                entry = {
                    "name": requirement.name,
                    "ready": False,
                    "severity": requirement.severity,
                    "detail": "前端尚未观测到该 topic。",
                    "age_ms": None,
                    "threshold_ms": requirement.threshold_ms,
                }
                checks.append(entry)
                target = blockers if requirement.severity == "blocker" else warnings
                target.append({"name": f"{requirement.name} 未观测到", "detail": entry["detail"]})
                continue
            age_ms = max(0, int((current_ns - ts_ns) / 1_000_000))
            worst_age_ms = max(worst_age_ms or 0, age_ms)
            ready = age_ms <= requirement.threshold_ms
            detail = (
                f"age={age_ms}ms，阈值 {requirement.threshold_ms}ms"
                if ready else f"age={age_ms}ms，超过阈值 {requirement.threshold_ms}ms"
            )
            entry = {
                "name": requirement.name,
                "ready": ready,
                "severity": requirement.severity,
                "detail": detail,
                "age_ms": age_ms,
                "threshold_ms": requirement.threshold_ms,
            }
            checks.append(entry)
            if not ready:
                target = blockers if requirement.severity == "blocker" else warnings
                target.append({"name": f"{requirement.name} 数据陈旧", "detail": detail})

        if blockers:
            summary_state = "blocked"
            summary_label = "关键遥测陈旧"
        elif warnings:
            summary_state = "degraded"
            summary_label = "非关键遥测降级"
        else:
            summary_state = "ready"
            summary_label = "遥测新鲜"
        return {
            "summary_state": summary_state,
            "summary_label": summary_label,
            "worst_age_ms": worst_age_ms,
            "checks": checks,
            "blockers": blockers,
            "warnings": warnings,
        }

    def _build_consistency(self, telemetry: TelemetryStore, workflow_artifacts: WorkflowArtifacts) -> dict[str, Any]:
        execution_state = str(telemetry.core_state.execution_state or "BOOT")
        operate_mode = str(telemetry.robot.get("operate_mode", "manual") or "manual").lower()
        powered = bool(telemetry.robot.get("powered", False))
        safe_to_scan = bool(telemetry.safety_status.safe_to_scan)
        blockers: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []
        checks: list[dict[str, Any]] = []

        def add_check(name: str, ok: bool, detail: str, *, severity: str = "blocker") -> None:
            checks.append({"name": name, "ready": ok, "severity": severity, "detail": detail})
            if ok:
                return
            target = blockers if severity == "blocker" else warnings
            target.append({"name": name, "detail": detail})

        add_check(
            "会话锁定与执行态一致",
            not (execution_state in self._ACTIVE_EXECUTION_STATES and not workflow_artifacts.session_locked),
            "执行态已进入正式路径，但会话仍未锁定。",
        )
        add_check(
            "上电状态与执行态一致",
            not (execution_state in self._ACTIVE_EXECUTION_STATES and not powered),
            "执行态已进入正式路径，但 robot_state 仍显示未上电。",
        )
        add_check(
            "自动模式与执行态一致",
            not (execution_state in self._SCAN_ACTIVE_STATES and operate_mode != "automatic"),
            f"当前执行态 {execution_state} 需要自动模式，但 operate_mode={operate_mode}。",
        )
        add_check(
            "安全态与扫查态一致",
            not (execution_state in {"SCANNING", "CONTACT_STABLE", "PAUSED_HOLD"} and not safe_to_scan),
            f"当前执行态 {execution_state} 需要 safe_to_scan=true。",
        )
        if blockers:
            summary_state = "blocked"
            summary_label = "运行态不一致"
        elif warnings:
            summary_state = "degraded"
            summary_label = "运行态轻微偏差"
        else:
            summary_state = "ready"
            summary_label = "运行态一致"
        return {
            "summary_state": summary_state,
            "summary_label": summary_label,
            "checks": checks,
            "blockers": blockers,
            "warnings": warnings,
        }

    def _build_command_observability(
        self,
        telemetry: TelemetryStore,
        workflow_artifacts: WorkflowArtifacts,
        recent_commands: list[dict[str, Any]],
    ) -> dict[str, Any]:
        execution_state = str(telemetry.core_state.execution_state or "BOOT")
        operate_mode = str(telemetry.robot.get("operate_mode", "manual") or "manual").lower()
        powered = bool(telemetry.robot.get("powered", False))
        robot_connected = bool(telemetry.devices.get("robot") and telemetry.devices["robot"].connected)
        evaluations: list[dict[str, Any]] = []
        blockers: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        def evaluate(command: str) -> tuple[bool, str] | None:
            if command == "connect_robot":
                return robot_connected, "robot 设备应切换为 connected。"
            if command == "power_on":
                return powered, "power_on 后应观测到 powered=true。"
            if command == "set_auto_mode":
                return operate_mode == "automatic", "set_auto_mode 后应观测到 automatic。"
            if command == "lock_session":
                return workflow_artifacts.session_locked, "lock_session 后会话应被锁定。"
            if command == "load_scan_plan":
                return execution_state in self._ACTIVE_EXECUTION_STATES, "load_scan_plan 后执行态应进入 PATH_VALIDATED 或后续状态。"
            if command == "approach_prescan":
                return execution_state in {"APPROACHING", "CONTACT_SEEKING", "CONTACT_STABLE", "SCANNING", "PAUSED_HOLD", "RETREATING", "RECOVERY_RETRACT", "SCAN_COMPLETE"}, "approach_prescan 后应观测到进入路径执行态。"
            if command == "seek_contact":
                return execution_state in {"CONTACT_SEEKING", "CONTACT_STABLE", "SCANNING", "PAUSED_HOLD"}, "seek_contact 后应观测到接触相关执行态。"
            if command == "start_procedure":
                return execution_state in {"SCANNING", "PAUSED_HOLD", "SCAN_COMPLETE"}, "start_procedure(scan) 后应观测到进入 SCANNING/PAUSED_HOLD/SCAN_COMPLETE。"
            if command == "pause_scan":
                return execution_state == "PAUSED_HOLD", "pause_scan 后应观测到 PAUSED_HOLD。"
            if command == "resume_scan":
                return execution_state == "SCANNING", "resume_scan 后应观测到 SCANNING。"
            if command == "safe_retreat":
                return execution_state in {"RETREATING", "RECOVERY_RETRACT", "AUTO_READY", "SCAN_COMPLETE"}, "safe_retreat 后应观测到退让或回到安全状态。"
            if command == "disconnect_robot":
                return not robot_connected, "disconnect_robot 后 robot 设备应断开。"
            return None

        latest_checked_command = ""
        for item in reversed([dict(x) for x in recent_commands[-8:]]):
            if not bool(item.get("ok", False)):
                continue
            command = str(item.get("command", ""))
            verdict = evaluate(command)
            if verdict is None:
                continue
            latest_checked_command = command
            observed, detail = verdict
            evaluations.append({
                "command": command,
                "observed": observed,
                "detail": detail,
                "message": str(item.get("message", "")),
                "request_id": str(item.get("request_id", "")),
            })
            if not observed:
                blockers.append({"name": f"命令 {command} 未被观测确认", "detail": detail})
            break

        failed = [dict(item) for item in recent_commands[-8:] if not bool(dict(item).get("ok", False))]
        if failed:
            warnings.append({"name": "最近命令窗口存在失败", "detail": f"最近 {len(recent_commands[-8:])} 条命令内失败 {len(failed)} 条。"})

        if blockers:
            summary_state = "blocked"
            summary_label = "命令确认缺失"
        elif warnings:
            summary_state = "degraded"
            summary_label = "命令窗口降级"
        else:
            summary_state = "ready"
            summary_label = "命令已观测确认"

        return {
            "summary_state": summary_state,
            "summary_label": summary_label,
            "latest_checked_command": latest_checked_command,
            "evaluations": evaluations,
            "blockers": blockers,
            "warnings": warnings,
        }
