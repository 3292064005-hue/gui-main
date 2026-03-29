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
    def permissions(self, ctx: WorkflowContext) -> dict[str, bool]:
        s = ctx.core_state
        plan_ready = ctx.preview_plan_ready or ctx.path_ready
        ready_for_local_ops = s in {
            SystemState.AUTO_READY,
            SystemState.SESSION_LOCKED,
            SystemState.PATH_VALIDATED,
            SystemState.SCAN_COMPLETE,
        }
        return {
            "connect_robot": s in {SystemState.BOOT, SystemState.DISCONNECTED},
            "disconnect_robot": s not in {SystemState.BOOT, SystemState.DISCONNECTED, SystemState.ESTOP},
            "power_on": s == SystemState.CONNECTED,
            "power_off": s in {SystemState.POWERED, SystemState.AUTO_READY, SystemState.SESSION_LOCKED, SystemState.PATH_VALIDATED, SystemState.SCAN_COMPLETE},
            "set_auto_mode": s == SystemState.POWERED,
            "set_manual_mode": s in {SystemState.AUTO_READY, SystemState.SESSION_LOCKED, SystemState.PATH_VALIDATED, SystemState.SCAN_COMPLETE},
            "create_experiment": s == SystemState.AUTO_READY,
            "run_localization": ctx.has_experiment and ready_for_local_ops,
            "generate_path": ctx.has_experiment and ctx.localization_ready and ready_for_local_ops,
            "start_scan": plan_ready and s in {SystemState.AUTO_READY, SystemState.PATH_VALIDATED, SystemState.SCAN_COMPLETE},
            "pause_scan": s == SystemState.SCANNING,
            "resume_scan": s == SystemState.PAUSED_HOLD,
            "stop_scan": s in {SystemState.SCANNING, SystemState.PAUSED_HOLD, SystemState.APPROACHING, SystemState.CONTACT_SEEKING, SystemState.CONTACT_STABLE},
            "safe_retreat": s in {SystemState.PATH_VALIDATED, SystemState.APPROACHING, SystemState.CONTACT_SEEKING, SystemState.CONTACT_STABLE, SystemState.SCANNING, SystemState.PAUSED_HOLD, SystemState.FAULT},
            "go_home": s not in {SystemState.BOOT, SystemState.DISCONNECTED, SystemState.ESTOP},
            "run_preprocess": s == SystemState.SCAN_COMPLETE,
            "run_reconstruction": s == SystemState.SCAN_COMPLETE,
            "run_assessment": s == SystemState.SCAN_COMPLETE,
            "export_summary": ctx.session_locked,
        }
