from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path


os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_THIS_DIR = Path(__file__).resolve().parent
_RUNNING_AS_MAIN = __name__ == "__main__"


def _load_real_pytest():
    search_path = [
        entry
        for entry in sys.path
        if Path(entry or ".").resolve() != _THIS_DIR
    ]
    spec = importlib.machinery.PathFinder.find_spec("pytest", search_path)
    if spec is None or spec.loader is None:
        raise ImportError("Unable to locate the installed pytest package")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_REAL_PYTEST = _load_real_pytest()
sys.modules.setdefault("pytest", _REAL_PYTEST)
for name, value in _REAL_PYTEST.__dict__.items():
    if name in {"__name__", "__package__", "__loader__", "__spec__", "__file__", "__cached__"}:
        continue
    globals()[name] = value


if _RUNNING_AS_MAIN:
    raise SystemExit(_REAL_PYTEST.console_main())
