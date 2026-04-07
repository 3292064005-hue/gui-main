from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService


def _reset_app() -> None:
    app = QApplication.instance()
    if app is None:
        return
    if hasattr(app, 'quit'):
        try:
            app.quit()
        except Exception:
            pass
    if hasattr(app, 'processEvents'):
        try:
            app.processEvents()
        except Exception:
            pass
    if hasattr(type(app), '_instance'):
        type(app)._instance = None


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_sdk_runtime_asset_service_collects_mock_inventory(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    service = SdkRuntimeAssetService()
    snapshot = service.refresh(backend, RuntimeConfig())
    assert snapshot["controller_logs"]
    assert snapshot["rl_projects"]
    assert snapshot["path_library"]
    assert snapshot["safety_profile"]["collision_detection_enabled"] is True
    assert snapshot["motion_contract"]["rt_mode"] == "cartesianImpedance"
    assert snapshot["errors"] == []


def test_generated_execution_plan_produces_ready_model_report(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    controller = AppController(tmp_path, backend)
    try:
        controller.connect_robot()
        controller.power_on()
        controller.set_auto_mode()
        controller.create_experiment()
        controller.run_localization()
        controller.generate_path()

        report = controller.model_report
        assert report["summary_state"] == "ready"
        assert report["plan_metrics"]["total_waypoints"] > 0
        assert report["execution_selection"]["selected_profile"]
        assert report["envelope"]["approach_jump_mm"] >= 0.0
        assert report["envelope"]["retreat_jump_mm"] >= 0.0
    finally:
        controller.shutdown()
        _reset_app()


def test_status_payload_exposes_sdk_runtime_and_model_report(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    controller = AppController(tmp_path, backend)
    payloads: list[dict] = []
    controller.status_updated.connect(payloads.append)

    try:
        controller.connect_robot()
        controller.power_on()
        controller.set_auto_mode()
        controller.create_experiment()
        controller.run_localization()
        controller.generate_path()
        controller.refresh_sdk_assets()
        controller.run_rl_project()
        controller.enable_drag()
        controller._emit_status()

        latest = payloads[-1]
        assert latest["sdk_runtime"]["rl_status"]["running"] is True
        assert latest["sdk_runtime"]["drag_status"]["enabled"] is True
        assert latest["model_report"]["summary_label"] == "模型前检通过"
    finally:
        controller.shutdown()
        _reset_app()
