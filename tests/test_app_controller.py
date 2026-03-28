import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.core.exception_handler import AppException
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_app_controller_locks_session_only_when_scan_starts(tmp_path):
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    assert controller.session_service.current_experiment is not None
    assert controller.session_service.current_experiment.session_id == ""
    controller.run_localization()
    controller.generate_path()
    assert controller.workflow_artifacts.preview_plan_ready is True
    assert controller.workflow_artifacts.session_locked is False
    controller.start_scan()
    assert controller.workflow_artifacts.session_locked is True
    assert controller.session_service.current_experiment.session_id
    manifest_path = controller.session_service.current_session_dir / "meta" / "manifest.json"
    assert manifest_path.exists()
    manifest = __import__("json").loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["protocol_version"] == 1
    assert manifest["force_sensor_provider"] == controller.config.force_sensor_provider
    assert manifest["safety_thresholds"]["sensor_timeout_ms"] == 500
    assert "pressure" in manifest["device_health_snapshot"]


def test_app_controller_rolls_back_local_session_if_core_lock_fails(tmp_path):
    class LockFailBackend(MockBackend):
        def send_command(self, command, payload=None):
            if command == "lock_session":
                return ReplyEnvelope(ok=False, message="lock rejected", data={})
            return super().send_command(command, payload)

    _app()
    backend = LockFailBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()
    assert controller.workflow_artifacts.session_locked is False
    assert controller.session_service.current_session_dir is None
    assert controller.session_service.current_experiment.session_id == ""


def test_app_controller_rejects_config_updates_after_session_lock(tmp_path):
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()

    try:
        controller.update_config(RuntimeConfig(pressure_target=1.8))
    except AppException as exc:
        assert "Session is locked" in str(exc)
    else:
        raise AssertionError("config updates should be blocked after session lock")


def test_app_controller_requests_safe_retreat_if_scan_start_chain_fails(tmp_path):
    class SeekContactFailBackend(MockBackend):
        def __init__(self, root_dir: Path):
            super().__init__(root_dir)
            self.commands: list[str] = []

        def send_command(self, command, payload=None):
            self.commands.append(command)
            if command == "seek_contact":
                return ReplyEnvelope(ok=False, message="contact failed", data={})
            return super().send_command(command, payload)

    _app()
    backend = SeekContactFailBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()

    assert "safe_retreat" in backend.commands
    assert controller.workflow_artifacts.session_locked is True


def test_app_controller_keeps_session_locked_if_load_scan_plan_fails(tmp_path):
    class LoadPlanFailBackend(MockBackend):
        def __init__(self, root_dir: Path):
            super().__init__(root_dir)
            self.commands: list[str] = []

        def send_command(self, command, payload=None):
            self.commands.append(command)
            if command == "load_scan_plan":
                return ReplyEnvelope(ok=False, message="invalid plan", data={})
            return super().send_command(command, payload)

    _app()
    backend = LoadPlanFailBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()

    assert controller.workflow_artifacts.session_locked is True
    assert controller.session_service.current_session_dir is not None
    assert "approach_prescan" not in backend.commands


def test_app_controller_requests_safe_retreat_if_pause_scan_fails(tmp_path):
    class PauseFailBackend(MockBackend):
        def __init__(self, root_dir: Path):
            super().__init__(root_dir)
            self.commands: list[str] = []

        def send_command(self, command, payload=None):
            self.commands.append(command)
            if command == "pause_scan":
                return ReplyEnvelope(ok=False, message="pause failed", data={})
            return super().send_command(command, payload)

    _app()
    backend = PauseFailBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()
    controller.pause_scan()

    assert backend.commands.count("safe_retreat") >= 1
    assert controller.workflow_artifacts.session_locked is True
