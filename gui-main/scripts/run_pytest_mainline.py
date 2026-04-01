from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.bootstrap_env import configure_test_environment


def _cleanup_generated_python_artifacts() -> None:
    for root, dirs, files in os.walk(ROOT, topdown=False):
        root_path = Path(root)
        if '.git' in root_path.parts:
            continue
        for filename in files:
            if filename.endswith(('.pyc', '.pyo')):
                (root_path / filename).unlink(missing_ok=True)
        for dirname in dirs:
            if dirname == '.pytest_cache':
                import shutil
                shutil.rmtree(root_path / dirname, ignore_errors=True)
            elif dirname == "__pycache__":
                import shutil
                shutil.rmtree(root_path / dirname, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    configure_test_environment()
    import pytest

    args = list(argv if argv is not None else sys.argv[1:])
    if '-p' not in args and '--cache-dir' not in args:
        args = ['-p', 'no:cacheprovider', *args]
    try:
        return pytest.main(args)
    finally:
        _cleanup_generated_python_artifacts()


if __name__ == "__main__":
    raise SystemExit(main())
