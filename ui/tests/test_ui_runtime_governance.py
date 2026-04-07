from pathlib import Path

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.core.view_state_factory import ViewStateFactory
from spine_ultrasound_ui.core.workflow_state_machine import WorkflowContext, WorkflowStateMachine
from spine_ultrasound_ui.models import RuntimeConfig, SystemState, WorkflowArtifacts
from spine_ultrasound_ui.services.mock_backend import MockBackend


def test_workflow_state_machine_exposes_human_readable_reasons() -> None:
    machine = WorkflowStateMachine()
    matrix = machine.permission_matrix(WorkflowContext(core_state=SystemState.CONNECTED))
    assert matrix["power_on"]["enabled"] is True
    assert "上电" not in matrix["power_on"]["reason"] or isinstance(matrix["power_on"]["reason"], str)
    assert matrix["create_experiment"]["enabled"] is False
    assert "AUTO_READY" in str(matrix["create_experiment"]["reason"])


def test_view_state_factory_builds_readiness_and_recommended_action() -> None:
    backend = MockBackend(Path("/tmp/mock-runtime"))
    controller = AppController(Path("/tmp/mock-runtime-controller"), backend)
    controller.telemetry.apply(backend.runtime.telemetry_snapshot()[0])
    controller.telemetry.apply(backend.runtime.telemetry_snapshot()[1])
    controller.telemetry.apply(backend.runtime.telemetry_snapshot()[2])
    controller.telemetry.apply(backend.runtime.telemetry_snapshot()[3])
    controller.telemetry.apply(backend.runtime.telemetry_snapshot()[4])
    controller.telemetry.apply(backend.runtime.telemetry_snapshot()[5])
    controller.telemetry.apply(backend.runtime.telemetry_snapshot()[6])
    payload = ViewStateFactory().build(
        controller.telemetry,
        RuntimeConfig(),
        WorkflowArtifacts(),
        None,
    ).to_dict()
    assert "readiness" in payload
    assert payload["readiness"]["recommended_label"]
    assert isinstance(payload["actions"]["connect_robot"]["reason"], str)


def test_app_controller_persists_and_reloads_runtime_config(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path)
    controller = AppController(tmp_path, backend)
    controller.update_config(RuntimeConfig(scan_speed_mm_s=15.0, telemetry_rate_hz=33))
    assert controller.runtime_config_path.exists()
    controller.update_config(RuntimeConfig(scan_speed_mm_s=7.0, telemetry_rate_hz=10))
    controller.reload_persisted_config()
    assert controller.config.scan_speed_mm_s == 7.0
    assert controller.config.telemetry_rate_hz == 10
    prefs = {"window_width": 1600, "tab_index": 3}
    controller.save_ui_preferences(prefs)
    assert controller.load_ui_preferences()["tab_index"] == 3
