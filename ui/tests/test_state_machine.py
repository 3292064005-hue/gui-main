from spine_ultrasound_ui.core.workflow_state_machine import WorkflowContext, WorkflowStateMachine
from spine_ultrasound_ui.models import SystemState


def test_permissions_follow_core_state():
    sm = WorkflowStateMachine()
    perms = sm.permissions(WorkflowContext(core_state=SystemState.AUTO_READY, has_experiment=False, session_locked=False, localization_ready=False, preview_plan_ready=False))
    assert perms["create_experiment"] is True
    assert perms["start_scan"] is False


def test_permissions_require_localization_for_path_generation():
    sm = WorkflowStateMachine()
    perms = sm.permissions(WorkflowContext(core_state=SystemState.SESSION_LOCKED, has_experiment=True, session_locked=True, localization_ready=False, path_ready=False))
    assert perms["run_localization"] is True
    assert perms["generate_path"] is False


def test_permissions_allow_scan_start_from_auto_ready_once_preview_exists():
    sm = WorkflowStateMachine()
    perms = sm.permissions(
        WorkflowContext(
            core_state=SystemState.AUTO_READY,
            has_experiment=True,
            session_locked=False,
            localization_ready=True,
            preview_plan_ready=True,
        )
    )
    assert perms["start_scan"] is True
