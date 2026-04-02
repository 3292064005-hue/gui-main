from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication, QMessageBox


class MainWindowRuntimeHost(Protocol):
    backend: Any
    alarm_banner: Any
    log_box: Any
    robot_monitor_page: Any
    scan_page: Any
    vision_page: Any
    reconstruction_page: Any
    main_splitter: Any
    tabs: Any

    def x(self) -> int: ...
    def y(self) -> int: ...
    def width(self) -> int: ...
    def height(self) -> int: ...
    def move(self, x: int, y: int) -> None: ...
    def resize(self, width: int, height: int) -> None: ...
    def statusBar(self) -> Any: ...


class MainWindowRuntimeBridge:
    def __init__(self, host: MainWindowRuntimeHost):
        self.host = host

    def save_runtime_config(self) -> None:
        if hasattr(self.host.backend, "save_runtime_config"):
            self.host.backend.save_runtime_config()

    def reload_runtime_config(self, config_form: Any) -> None:
        if hasattr(self.host.backend, "reload_persisted_config"):
            self.host.backend.reload_persisted_config()
            config_form.populate_from_config(self.host.backend.config)

    def restore_default_config(self, config_form: Any) -> None:
        if hasattr(self.host.backend, "restore_default_config"):
            self.host.backend.restore_default_config()
            config_form.populate_from_config(self.host.backend.config)

    def restore_ui_preferences(self) -> None:
        if not hasattr(self.host.backend, "load_ui_preferences"):
            return
        prefs = self.host.backend.load_ui_preferences() or {}
        width = int(prefs.get("window_width", 1720))
        height = int(prefs.get("window_height", 1020))
        width, height = _clamp_window_size(width, height)
        pos_x = int(prefs.get("window_x", _default_window_x()))
        pos_y = int(prefs.get("window_y", _default_window_y()))
        pos_x, pos_y = _clamp_window_position(pos_x, pos_y, width, height)
        self.host.resize(width, height)
        self.host.move(pos_x, pos_y)
        tab_index = int(prefs.get("tab_index", 0))
        if 0 <= tab_index < self.host.tabs.count():
            self.host.tabs.setCurrentIndex(tab_index)
        splitter_sizes = prefs.get("splitter_sizes")
        if isinstance(splitter_sizes, list) and len(splitter_sizes) == 3:
            self.host.main_splitter.setSizes([int(v) for v in splitter_sizes])

    def save_ui_preferences(self) -> None:
        if not hasattr(self.host.backend, "save_ui_preferences"):
            return
        sizes = self.host.main_splitter.sizes() if hasattr(self.host.main_splitter, "sizes") else [360, 1020, 340]
        self.host.backend.save_ui_preferences(
            {
                "window_x": self.host.x(),
                "window_y": self.host.y(),
                "window_width": self.host.width(),
                "window_height": self.host.height(),
                "tab_index": self.host.tabs.currentIndex(),
                "splitter_sizes": list(sizes),
            }
        )

    @Slot(str)
    def on_system_state(self, state: str) -> None:
        self.host.statusBar().showMessage(f"系统状态切换：{state}", 3000)

    @Slot(str)
    def on_alarm(self, message: str) -> None:
        self.host.alarm_banner.set_alarm("ALARM", message)
        self.append_log("ALARM", message)

    @Slot(str, str)
    def append_log(self, level: str, message: str) -> None:
        self.host.log_box.append_colored(level, message)
        self.host.robot_monitor_page.log_view.append(message)

    @Slot(object)
    def update_camera_pixmap(self, pix: Any) -> None:
        self.host.scan_page.camera_pane.set_pixmap(pix)
        self.host.vision_page.camera_pane.set_pixmap(pix)
        self.host.reconstruction_page.raw_pane.set_pixmap(pix)

    @Slot(object)
    def update_ultrasound_pixmap(self, pix: Any) -> None:
        self.host.scan_page.ultrasound_pane.set_pixmap(pix)
        self.host.reconstruction_page.pre_pane.set_pixmap(pix)
        self.host.reconstruction_page.feature_pane.set_pixmap(pix)

    @Slot(object)
    def update_reconstruction_pixmap(self, pix: Any) -> None:
        self.host.reconstruction_page.reconstruction_pane.set_pixmap(pix)

    def confirm_estop(self) -> None:
        ret = QMessageBox.warning(
            self.host,
            "急停确认",
            "确认执行急停？该操作将立即停止当前流程。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret == QMessageBox.Yes:
            self.host.alarm_banner.set_alarm("ALARM", "急停触发，所有运动应立即中止。")
            if hasattr(self.host.backend, "emergency_stop"):
                self.host.backend.emergency_stop()
            else:
                self.host.backend.safe_retreat()


def _clamp_window_size(width: int, height: int) -> tuple[int, int]:
    screen = QApplication.primaryScreen()
    if screen is None:
        return width, height
    available = screen.availableGeometry()
    max_width = max(960, available.width() - 24)
    max_height = max(640, available.height() - 24)
    min_width = min(max_width, 1180)
    min_height = min(max_height, 640)
    clamped_width = min(max(width, min_width), max_width)
    preferred_max_height = min(780, max_height)
    clamped_height = min(max(height, min_height), preferred_max_height)
    return clamped_width, clamped_height


def _default_window_x() -> int:
    screen = QApplication.primaryScreen()
    if screen is None:
        return 24
    available = screen.availableGeometry()
    return available.x() + 12


def _default_window_y() -> int:
    screen = QApplication.primaryScreen()
    if screen is None:
        return 24
    available = screen.availableGeometry()
    return available.y() + 12


def _clamp_window_position(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    screen = QApplication.primaryScreen()
    if screen is None:
        return x, y
    available = screen.availableGeometry()
    min_x = available.x() + 12
    min_y = available.y() + 12
    max_x = max(min_x, available.x() + available.width() - width - 12)
    max_y = max(min_y, available.y() + available.height() - height - 12)
    clamped_x = min(max(x, min_x), max_x)
    clamped_y = min(max(y, min_y), max_y)
    return clamped_x, clamped_y
