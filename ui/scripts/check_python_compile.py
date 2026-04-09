#!/usr/bin/env python3
from __future__ import annotations

"""Fail fast when any first-party Python file in the repository is unparsable.

The repository gates already validate architecture, protocol sync, and pytest
behavior. This script closes the remaining blind spot by making Python syntax /
bytecode compilation an explicit required gate across the shipped source tree.
"""

import sys
import tokenize
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = ('spine_ultrasound_ui', 'runtime', 'scripts', 'tests')
IGNORED_PARTS = {'__pycache__', '.pytest_cache'}


def iter_python_files() -> list[Path]:
    """Return first-party Python files that participate in repository gates."""
    files: list[Path] = []
    for folder in SCAN_ROOTS:
        root = ROOT / folder
        if not root.exists():
            continue
        for path in root.rglob('*.py'):
            if any(part in IGNORED_PARTS for part in path.parts):
                continue
            files.append(path)
    return sorted(files)


def _compile_path(path: Path) -> None:
    """Parse and compile a Python source file without writing cache artifacts.

    Args:
        path: Repository-local Python file to validate.

    Raises:
        SyntaxError: When the source cannot be parsed/compiled.
        UnicodeError: When the file cannot be decoded according to its declared
            source encoding.
        OSError: When the file cannot be read.

    Boundary behaviour:
        - Uses :mod:`tokenize` so source-encoding cookies are honored.
        - Calls :func:`compile` directly instead of :mod:`py_compile` to avoid
          creating ``.pyc`` / ``__pycache__`` artifacts during repository gates.
    """
    with tokenize.open(path) as handle:
        source = handle.read()
    compile(source, str(path), 'exec', dont_inherit=True)


def main() -> int:
    """Compile each Python file without emitting ``.pyc`` artifacts.

    Returns:
        ``0`` when all files compile, otherwise ``1``.
    """
    failures: list[str] = []
    checked = 0
    for path in iter_python_files():
        checked += 1
        try:
            _compile_path(path)
        except SyntaxError as exc:
            failures.append(f'{path.relative_to(ROOT)}: {exc.msg} (line {exc.lineno})')
        except Exception as exc:  # pragma: no cover - defensive guardrail
            failures.append(f'{path.relative_to(ROOT)}: {exc}')
    if failures:
        for item in failures:
            print(f'[FAIL] {item}')
        return 1
    print(f'[PASS] compiled {checked} Python files without syntax errors or cache artifacts')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
