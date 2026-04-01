from __future__ import annotations

import importlib.util
import os
from importlib import metadata

from spine_ultrasound_ui.services.runtime_version_policy import (
    check_protobuf_runtime_version,
    check_pyside6_version,
)


def configure_runtime_environment(*, require_qt: bool = False) -> None:
    """Apply deterministic runtime environment defaults.

    This function intentionally does **not** install PySide6 stubs. Test-only
    callers that want GUI shims must opt in through
    ``tests.runtime_compat.enable_runtime_compat``.
    """
    if os.getenv("DISPLAY", "") == "" and os.getenv("WAYLAND_DISPLAY", "") == "":
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
    if require_qt:
        try:
            spec = importlib.util.find_spec("PySide6")
        except (ImportError, ValueError):
            spec = None
        if spec is None:
            raise RuntimeError(
                "PySide6 is required for the desktop runtime. Install requirements.txt "
                "for real desktop execution; only tests may opt into the PySide6 stub."
            )
        pyside6_check = check_pyside6_version(_distribution_version("PySide6"))
        if not pyside6_check.ok:
            raise RuntimeError(
                "PySide6>=6.7 is required for the desktop runtime; "
                f"detected {pyside6_check.detail}."
            )

    protobuf_check = check_protobuf_runtime_version(_distribution_version("protobuf"))
    if not protobuf_check.ok:
        raise RuntimeError(
            "The Python protobuf runtime is unsupported for the converged mainline; "
            f"detected {protobuf_check.detail}."
        )


def _distribution_version(distribution_name: str) -> str:
    try:
        return metadata.version(distribution_name)
    except metadata.PackageNotFoundError:
        return ""
    except Exception:
        return ""
