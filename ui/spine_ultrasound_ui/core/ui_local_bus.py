from __future__ import annotations

"""Canonical UI-local signal bus.

This module is the only supported source for in-process Qt UI signals.
This module is the only supported import location for in-process Qt UI
signals.
"""

from spine_ultrasound_ui.core.qt_signal_bus import QtSignalBus, get_qt_signal_bus, qt_bus

__all__ = ["QtSignalBus", "get_qt_signal_bus", "qt_bus"]
