from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.bootstrap_env import configure_test_environment

ARCHIVE_COMPAT_DIR = str(Path('tests') / 'archive')


_LAYER_MARKERS = {"unit", "contract", "runtime_core", "surface_integration", "mock_e2e", "hil"}


def _extract_layer_args(args: list[str]) -> list[str]:
    filtered: list[str] = []
    requested_layers: list[str] = []
    iterator = iter(range(len(args)))
    i = 0
    while i < len(args):
        item = args[i]
        if item == '--layer' and i + 1 < len(args):
            requested_layers.append(args[i + 1])
            i += 2
            continue
        filtered.append(item)
        i += 1
    env_layer = os.environ.get('PYTEST_LAYER', '').strip()
    if env_layer:
        requested_layers.extend([part.strip() for part in env_layer.split(',') if part.strip()])
    invalid = [layer for layer in requested_layers if layer not in _LAYER_MARKERS]
    if invalid:
        raise SystemExit(f'unsupported pytest layer(s): {", ".join(sorted(set(invalid)))}')
    if requested_layers:
        marker_expr = ' or '.join(sorted(dict.fromkeys(requested_layers)))
        filtered = ['-m', marker_expr, *filtered]
    return filtered


def _maybe_report_layers(args: list[str]) -> list[str]:
    if '--report-layers' not in args:
        return args
    filtered = [item for item in args if item != '--report-layers']
    print('pytest layers: unit, contract, runtime_core, surface_integration, mock_e2e, hil')
    return filtered


MAINLINE_PYTHON_DIRS = ("spine_ultrasound_ui", "tests", "scripts", "runtime")


def _cleanup_generated_python_artifacts() -> None:
    import shutil

    allowed_roots = {ROOT / dirname for dirname in MAINLINE_PYTHON_DIRS}
    for root, dirs, files in os.walk(ROOT, topdown=False):
        root_path = Path(root)
        if '.git' in root_path.parts:
            continue
        if not any(root_path == allowed or allowed in root_path.parents for allowed in allowed_roots):
            continue
        for filename in files:
            if filename.endswith(('.pyc', '.pyo')):
                (root_path / filename).unlink(missing_ok=True)
        for dirname in dirs:
            if dirname == '.pytest_cache' or dirname == '__pycache__':
                shutil.rmtree(root_path / dirname, ignore_errors=True)


def _augment_args_with_archive_compat(args: list[str]) -> list[str]:
    """Optionally append archived compatibility suites to a mainline pytest run.

    Args:
        args: Raw pytest argument list.

    Returns:
        The argument list, optionally extended with ``tests/archive`` when the
        caller explicitly opts into compatibility coverage.

    Boundary behaviour:
        Archived compatibility suites are never part of the default mainline
        run. They are appended only when a caller passes
        ``--include-archive-compat`` or sets ``INCLUDE_ARCHIVE_COMPAT=1``.
    """
    include_archive = '--include-archive-compat' in args or os.environ.get('INCLUDE_ARCHIVE_COMPAT') == '1'
    filtered_args = [item for item in args if item != '--include-archive-compat']
    if not include_archive:
        return filtered_args
    if any(item.startswith('tests/archive') for item in filtered_args):
        return filtered_args
    return [*filtered_args, ARCHIVE_COMPAT_DIR]


def main(argv: list[str] | None = None) -> int:
    configure_test_environment()
    import pytest

    args = list(argv if argv is not None else sys.argv[1:])
    args = _maybe_report_layers(args)
    args = _extract_layer_args(args)
    if '-p' not in args and '--cache-dir' not in args:
        args = ['-p', 'no:cacheprovider', *args]
    args = _augment_args_with_archive_compat(args)
    try:
        return pytest.main(args)
    finally:
        _cleanup_generated_python_artifacts()


if __name__ == "__main__":
    raise SystemExit(main())
