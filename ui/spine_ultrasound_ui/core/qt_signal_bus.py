from __future__ import annotations

from PySide6.QtCore import QObject, Signal
import numpy as np


class QtSignalBus(QObject):
    """Legacy Qt signal bus used only by older local process components."""

    _instance = None

    sig_robot_state_changed = Signal(str)
    sig_force_warning = Signal(float)
    sig_new_us_frame = Signal(np.ndarray)
    sig_new_pose = Signal(np.ndarray, np.ndarray)
    sig_cmd_start_procedure = Signal()
    sig_cmd_emergency_stop = Signal()
    sig_config_updated = Signal(str, object)
    sig_process_health_changed = Signal(str, bool)
    sig_new_diagnostic_data = Signal(dict)
    sig_scan_progress = Signal(float)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance


def get_qt_signal_bus() -> QtSignalBus:
    return QtSignalBus()


qt_bus = get_qt_signal_bus()
