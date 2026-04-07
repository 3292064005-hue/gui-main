from __future__ import annotations

from importlib import import_module

__all__ = [
    "StatusCard",
    "ImagePane",
    "ConfigForm",
    "ExperimentTableModel",
    "AlarmBanner",
    "StateTimeline",
    "LogConsole",
]

_MODULE_MAP = {
    "StatusCard": ".status_card",
    "ImagePane": ".image_pane",
    "ConfigForm": ".config_form",
    "ExperimentTableModel": ".experiment_table_model",
    "AlarmBanner": ".alarm_banner",
    "StateTimeline": ".state_timeline",
    "LogConsole": ".log_console",
}


def __getattr__(name: str):
    if name not in _MODULE_MAP:
        raise AttributeError(name)
    module = import_module(_MODULE_MAP[name], __name__)
    return getattr(module, name)
