from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.bootstrap_env import configure_test_environment
from tests.runtime_compat import enable_runtime_compat

configure_test_environment()
enable_runtime_compat()
