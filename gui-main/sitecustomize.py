from __future__ import annotations

import os
import sys
from pathlib import Path


def _running_under_pytest() -> bool:
    argv0 = Path(sys.argv[0]).name.lower()
    return argv0 in {"pytest", "py.test"} or any(arg == "pytest" for arg in sys.argv[1:2])


if _running_under_pytest():
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
