from __future__ import annotations

from dataclasses import dataclass

from spine_ultrasound_ui.models import SystemState


@dataclass
class WorkflowContext:
    core_state: SystemState = SystemState.BOOT
    has_experiment: bool = False
    session_locked: bool = False
    localization_ready: bool = False
    preview_plan_ready: bool = False
    path_ready: bool = False


class WorkflowStateMachine:
    ACTION_LABELS = {
        "connect_robot": "连接机器人",
        "disconnect_robot": "断开机器人",
        "power_on": "上电",
        "power_off": "下电",
        "set_auto_mode": "切换自动模式",
        "set_manual_mode": "切换手动模式",
        "create_experiment": "新建实验",
        "run_localization": "执行视觉定位",
        "generate_path": "生成扫查路径",
        "start_scan": "开始扫查",
        "pause_scan": "暂停扫查",
        "resume_scan": "恢复扫查",
        "stop_scan": "停止扫查",
        "safe_retreat": "安全退让",
        "go_home": "回零位",
        "run_preprocess": "图像预处理",
        "run_reconstruction": "执行重建",
        "run_assessment": "执行评估",
        "export_summary": "导出摘要",
        "refresh_sdk_assets": "刷新 SDK 资产",
        "query_controller_log": "查询控制器日志",
        "run_rl_project": "运行 RL 工程",
        "pause_rl_project": "暂停 RL 工程",
        "enable_drag": "启用拖动示教",
        "disable_drag": "关闭拖动示教",
        "replay_path": "回放示教路径",
    }

    def permission_matrix(self, ctx: WorkflowContext) -> dict[str, dict[str, str | bool]]:
        s = ctx.core_state
        plan_ready = ctx.preview_plan_ready or ctx.path_ready
        ready_for_local_ops = s in {
            SystemState.AUTO_READY,
            SystemState.SESSION_LOCKED,
            SystemState.PATH_VALIDATED,
            SystemState.SCAN_COMPLETE,
        }
        return {
            "connect_robot": self._rule(
                s in {SystemState.BOOT, SystemState.DISCONNECTED},
                ok_reason="当前可建立控制链路。",
                blocked_reason=f"当前状态为 {s.value}，只有 BOOT / DISCONNECTED 可重新连接。",
            ),
            "disconnect_robot": self._rule(
                s not in {SystemState.BOOT, SystemState.DISCONNECTED, SystemState.ESTOP},
                ok_reason="当前允许安全断开。",
                blocked_reason=f"当前状态为 {s.value}，不允许断开或已断开。",
            ),
            "power_on": self._rule(
                s == SystemState.CONNECTED,
                ok_reason="机器人已连接，可执行上电。",
                blocked_reason="需要先完成机器人连接。",
            ),
            "power_off": self._rule(
                s in {SystemState.POWERED, SystemState.AUTO_READY, SystemState.SESSION_LOCKED, SystemState.PATH_VALIDATED, SystemState.SCAN_COMPLETE},
                ok_reason="当前允许安全下电。",
                blocked_reason=f"当前状态为 {s.value}，不建议或不允许下电。",
            ),
            "set_auto_mode": self._rule(
                s == SystemState.POWERED,
                ok_reason="机器人已上电，可切换自动模式。",
                blocked_reason="需要先完成上电。",
            ),
            "set_manual_mode": self._rule(
                s in {SystemState.AUTO_READY, SystemState.SESSION_LOCKED, SystemState.PATH_VALIDATED, SystemState.SCAN_COMPLETE},
                ok_reason="当前允许切回手动模式。",
                blocked_reason="只有自动就绪或流程结束后才允许切回手动模式。",
            ),
            "create_experiment": self._rule(
                s == SystemState.AUTO_READY,
                ok_reason="系统已自动就绪，可创建新实验。",
                blocked_reason="需要机器人处于 AUTO_READY。",
            ),
            "run_localization": self._rule(
                ctx.has_experiment and ready_for_local_ops,
                ok_reason="实验已创建，可执行视觉定位。",
                blocked_reason=self._localization_reason(ctx, ready_for_local_ops),
            ),
            "generate_path": self._rule(
                ctx.has_experiment and ctx.localization_ready and ready_for_local_ops,
                ok_reason="定位完成，可生成扫查路径。",
                blocked_reason=self._path_reason(ctx, ready_for_local_ops),
            ),
            "start_scan": self._rule(
                plan_ready and s in {SystemState.AUTO_READY, SystemState.PATH_VALIDATED, SystemState.SCAN_COMPLETE},
                ok_reason="路径预览完成，可执行扫查启动链。",
                blocked_reason=self._start_scan_reason(ctx, plan_ready),
            ),
            "pause_scan": self._rule(
                s == SystemState.SCANNING,
                ok_reason="当前处于扫查中，可暂停。",
                blocked_reason="只有 SCANNING 状态允许暂停。",
            ),
            "resume_scan": self._rule(
                s == SystemState.PAUSED_HOLD,
                ok_reason="当前处于暂停保持，可恢复。",
                blocked_reason="只有 PAUSED_HOLD 状态允许恢复。",
            ),
            "stop_scan": self._rule(
                s in {SystemState.SCANNING, SystemState.PAUSED_HOLD, SystemState.APPROACHING, SystemState.CONTACT_SEEKING, SystemState.CONTACT_STABLE},
                ok_reason="当前流程中允许中止并回退。",
                blocked_reason="当前没有正在执行的扫查链路。",
            ),
            "safe_retreat": self._rule(
                s in {SystemState.PATH_VALIDATED, SystemState.APPROACHING, SystemState.CONTACT_SEEKING, SystemState.CONTACT_STABLE, SystemState.SCANNING, SystemState.PAUSED_HOLD, SystemState.FAULT},
                ok_reason="当前支持安全退让。",
                blocked_reason="当前状态无需安全退让。",
            ),
            "go_home": self._rule(
                s not in {SystemState.BOOT, SystemState.DISCONNECTED, SystemState.ESTOP},
                ok_reason="当前允许回零位。",
                blocked_reason="机器人未连接或已急停，无法回零位。",
            ),
            "run_preprocess": self._rule(
                s == SystemState.SCAN_COMPLETE,
                ok_reason="扫查完成，可执行预处理。",
                blocked_reason="需要先完成扫查。",
            ),
            "run_reconstruction": self._rule(
                s == SystemState.SCAN_COMPLETE,
                ok_reason="扫查完成，可执行重建。",
                blocked_reason="需要先完成扫查。",
            ),
            "run_assessment": self._rule(
                s == SystemState.SCAN_COMPLETE,
                ok_reason="扫查完成，可执行评估。",
                blocked_reason="需要先完成扫查。",
            ),
            "export_summary": self._rule(
                ctx.session_locked,
                ok_reason="会话已锁定，可导出正式摘要。",
                blocked_reason="需要先进入正式会话并锁定。",
            ),
            "refresh_sdk_assets": self._rule(
                s not in {SystemState.BOOT, SystemState.DISCONNECTED},
                ok_reason="当前允许刷新 SDK 资产。",
                blocked_reason="需要先连接机器人后再刷新 SDK 资产。",
            ),
            "query_controller_log": self._rule(
                s not in {SystemState.BOOT, SystemState.DISCONNECTED},
                ok_reason="当前允许查询控制器日志。",
                blocked_reason="机器人未连接，无法查询控制器日志。",
            ),
            "run_rl_project": self._rule(
                s in {SystemState.AUTO_READY, SystemState.SESSION_LOCKED, SystemState.PATH_VALIDATED, SystemState.SCAN_COMPLETE},
                ok_reason="当前允许运行 RL 工程。",
                blocked_reason="需要系统进入自动就绪或流程结束状态。",
            ),
            "pause_rl_project": self._rule(
                s not in {SystemState.BOOT, SystemState.DISCONNECTED, SystemState.ESTOP},
                ok_reason="当前允许暂停 RL 工程。",
                blocked_reason="机器人未连接或已急停，无法暂停 RL 工程。",
            ),
            "enable_drag": self._rule(
                s in {SystemState.AUTO_READY, SystemState.SCAN_COMPLETE},
                ok_reason="当前允许进入拖动示教。",
                blocked_reason="只在 AUTO_READY 或流程结束后允许拖动示教。",
            ),
            "disable_drag": self._rule(
                s not in {SystemState.BOOT, SystemState.DISCONNECTED},
                ok_reason="当前允许退出拖动示教。",
                blocked_reason="机器人未连接，无需关闭拖动示教。",
            ),
            "replay_path": self._rule(
                s in {SystemState.AUTO_READY, SystemState.SCAN_COMPLETE},
                ok_reason="当前允许执行路径回放。",
                blocked_reason="需要系统进入 AUTO_READY 或 SCAN_COMPLETE。",
            ),
        }

    def permissions(self, ctx: WorkflowContext) -> dict[str, bool]:
        return {name: bool(rule["enabled"]) for name, rule in self.permission_matrix(ctx).items()}

    @staticmethod
    def _rule(enabled: bool, *, ok_reason: str, blocked_reason: str) -> dict[str, str | bool]:
        return {
            "enabled": enabled,
            "reason": ok_reason if enabled else blocked_reason,
        }

    @staticmethod
    def _localization_reason(ctx: WorkflowContext, ready_for_local_ops: bool) -> str:
        if not ctx.has_experiment:
            return "需要先创建实验。"
        if not ready_for_local_ops:
            return "需要系统处于 AUTO_READY / SESSION_LOCKED / PATH_VALIDATED / SCAN_COMPLETE。"
        return "当前不可执行视觉定位。"

    @staticmethod
    def _path_reason(ctx: WorkflowContext, ready_for_local_ops: bool) -> str:
        if not ctx.has_experiment:
            return "需要先创建实验。"
        if not ctx.localization_ready:
            return "需要先完成视觉定位。"
        if not ready_for_local_ops:
            return "需要系统处于允许的本地规划状态。"
        return "当前不可生成扫查路径。"

    @staticmethod
    def _start_scan_reason(ctx: WorkflowContext, plan_ready: bool) -> str:
        if not ctx.has_experiment:
            return "需要先创建实验。"
        if not ctx.localization_ready:
            return "需要先完成视觉定位。"
        if not plan_ready:
            return "需要先生成并确认扫查路径。"
        return "当前系统状态不允许开始扫查。"
