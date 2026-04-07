from __future__ import annotations

import os

from tests.pyside6_stub import install_pyside6_stub


def enable_runtime_compat(*, allow_pyside6_stub: bool = True, force_python_protobuf: bool = True) -> None:
    """Apply test-only runtime compatibility hooks.

    Args:
        allow_pyside6_stub: Whether the PySide6 stub may be installed when Qt is
            unavailable in the test environment.
        force_python_protobuf: Whether to force the pure-Python protobuf runtime
            for deterministic test execution.

    Returns:
        None.

    Raises:
        RuntimeError: Reserved for future test bootstrap failures.
    """
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if force_python_protobuf:
        os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
    if allow_pyside6_stub:
        install_pyside6_stub()


__all__ = ["enable_runtime_compat"]
