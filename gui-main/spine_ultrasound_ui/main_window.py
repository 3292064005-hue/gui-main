from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QPushButton, QWidget

from spine_ultrasound_ui.models import ExperimentRecord
from spine_ultrasound_ui.styles import MAIN_STYLESHEET
from spine_ultrasound_ui.widgets import ConfigForm, ExperimentTableModel
from spine_ultrasound_ui.views.main_window_layout import MainWindowLayoutBuilder
from spine_ultrasound_ui.views.main_window_runtime_bridge import MainWindowRuntimeBridge
from spine_ultrasound_ui.views.main_window_status_presenter import MainWindowStatusPresenter


class MainWindow(QMainWindow):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.setWindowTitle("脊柱侧弯自动检测研究平台")
        self.resize(1720, 1020)
        self.exp_model = ExperimentTableModel([])
        self.status_presenter = MainWindowStatusPresenter()
        self.runtime_bridge = MainWindowRuntimeBridge(self)
        self.config_form = ConfigForm(self.backend.config)
        if hasattr(self.backend, "update_config"):
            self.config_form.config_applied.connect(self.backend.update_config)
        self._build_ui()
        self._connect_backend()
        self._restore_ui_preferences()
        self.setStyleSheet(MAIN_STYLESHEET)

    def _build_ui(self) -> None:
        MainWindowLayoutBuilder(self).build()

    def _connect_backend(self) -> None:
        self.backend.status_updated.connect(self._on_status, Qt.QueuedConnection)
        self.backend.log_generated.connect(self._append_log, Qt.QueuedConnection)
        for signal_name, handler in [
            ("camera_pixmap_ready", self._update_camera_pixmap),
            ("ultrasound_pixmap_ready", self._update_ultrasound_pixmap),
            ("reconstruction_pixmap_ready", self._update_reconstruction_pixmap),
        ]:
            if hasattr(self.backend, signal_name):
                getattr(self.backend, signal_name).connect(handler, Qt.QueuedConnection)
        self.backend.experiments_updated.connect(self._on_experiments, Qt.QueuedConnection)
        self.backend.system_state_changed.connect(self._on_system_state, Qt.QueuedConnection)
        if hasattr(self.backend, "alarm_raised"):
            self.backend.alarm_raised.connect(self._on_alarm, Qt.QueuedConnection)
        self._connect_settings_page()

    def _connect_settings_page(self) -> None:
        if not hasattr(self.settings_page, "save_requested"):
            return
        self.settings_page.save_requested.connect(self._save_runtime_config)
        self.settings_page.reload_requested.connect(self._reload_runtime_config)
        self.settings_page.restore_defaults_requested.connect(self._restore_default_config)
        self.settings_page.save_layout_requested.connect(self._save_ui_preferences)
        for signal_name, handler in [
            ("apply_baseline_requested", self.backend.apply_clinical_baseline),
            ("export_governance_requested", self.backend.export_governance_snapshot),
            ("refresh_governance_requested", self.backend.refresh_session_governance),
        ]:
            if hasattr(self.settings_page, signal_name):
                getattr(self.settings_page, signal_name).connect(handler)

    def _apply_permissions(self, payload: dict) -> None:
        actions = payload.get("actions", {})
        mapping = {
            self.btn_connect: "connect_robot",
            self.btn_disconnect: "disconnect_robot",
            self.btn_power_on: "power_on",
            self.btn_power_off: "power_off",
            self.btn_auto: "set_auto_mode",
            self.btn_manual: "set_manual_mode",
            self.btn_new_exp: "create_experiment",
            self.btn_localize: "run_localization",
            self.btn_path: "generate_path",
            self.btn_scan_start: "start_scan",
            self.btn_scan_pause: "pause_scan",
            self.btn_scan_resume: "resume_scan",
            self.btn_scan_stop: "stop_scan",
            self.btn_home: "go_home",
            self.btn_retreat: "safe_retreat",
            self.btn_pre: "run_preprocess",
            self.btn_recon: "run_reconstruction",
            self.btn_assess: "run_assessment",
            self.btn_export: "export_summary",
            self.btn_sdk_refresh: "refresh_sdk_assets",
            self.btn_query_log: "query_controller_log",
            self.btn_run_rl: "run_rl_project",
            self.btn_pause_rl: "pause_rl_project",
            self.btn_enable_drag: "enable_drag",
            self.btn_disable_drag: "disable_drag",
            self.btn_replay_path: "replay_path",
        }
        for button, key in mapping.items():
            rule = actions.get(key, {"enabled": True, "reason": ""})
            button.setEnabled(bool(rule.get("enabled", True)))
            button.setToolTip(str(rule.get("reason", "")))

    def _set_badge_state(self, widget: QLabel, text: str, state: str) -> None:
        widget.setText(text)
        widget.setProperty("state", state)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    @staticmethod
    def _device_state(connected: bool, health: str) -> str:
        health_upper = str(health or "").upper()
        if not connected:
            return "danger"
        if health_upper in {"WARN", "WARNING", "DEGRADED"}:
            return "warn"
        return "ok"

    @staticmethod
    def _system_state_kind(state: str) -> str:
        state_upper = str(state or "").upper()
        if any(token in state_upper for token in ["FAULT", "ESTOP", "ALARM", "ERROR"]):
            return "danger"
        if any(token in state_upper for token in ["PAUSED", "SEEKING", "RETREAT", "BOOT", "DISCONNECTED"]):
            return "warn"
        return "ok"

    @staticmethod
    def _readiness_state(percent: int) -> str:
        if percent >= 100:
            return "ok"
        if percent >= 50:
            return "warn"
        return "danger"

    def _save_runtime_config(self) -> None:
        self.runtime_bridge.save_runtime_config()

    def _reload_runtime_config(self) -> None:
        self.runtime_bridge.reload_runtime_config(self.config_form)

    def _restore_default_config(self) -> None:
        self.runtime_bridge.restore_default_config(self.config_form)

    def _restore_ui_preferences(self) -> None:
        self.runtime_bridge.restore_ui_preferences()

    def _save_ui_preferences(self) -> None:
        self.runtime_bridge.save_ui_preferences()

    @Slot(dict)
    def _on_status(self, payload: dict) -> None:
        self.status_presenter.apply(self, payload)

    @Slot(list)
    def _on_experiments(self, records: list[ExperimentRecord]) -> None:
        self.exp_model.set_records(records)

    @Slot(str)
    def _on_system_state(self, state: str) -> None:
        self.runtime_bridge.on_system_state(state)

    @Slot(str)
    def _on_alarm(self, message: str) -> None:
        self.runtime_bridge.on_alarm(message)

    @Slot(str, str)
    def _append_log(self, level: str, message: str) -> None:
        self.runtime_bridge.append_log(level, message)

    def _update_camera_pixmap(self, pix) -> None:
        self.runtime_bridge.update_camera_pixmap(pix)

    def _update_ultrasound_pixmap(self, pix) -> None:
        self.runtime_bridge.update_ultrasound_pixmap(pix)

    def _update_reconstruction_pixmap(self, pix) -> None:
        self.runtime_bridge.update_reconstruction_pixmap(pix)

    def _confirm_estop(self) -> None:
        self.runtime_bridge.confirm_estop()

    def closeEvent(self, event) -> None:
        try:
            self._save_ui_preferences()
        finally:
            super().closeEvent(event)
