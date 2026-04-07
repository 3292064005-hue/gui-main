from __future__ import annotations

import importlib.util
import os

from tests.pyside6_stub import install_pyside6_stub


def configure_test_environment() -> None:
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
    try:
        spec = importlib.util.find_spec("PySide6")
    except ValueError:
        spec = None
    if spec is None:
        install_pyside6_stub()
