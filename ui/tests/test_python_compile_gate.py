from __future__ import annotations

from pathlib import Path

from scripts.check_python_compile import ROOT, iter_python_files, main as compile_gate_main


def test_python_compile_gate_passes() -> None:
    assert compile_gate_main() == 0


def test_python_compile_gate_scans_scripts_runtime_ui_and_tests() -> None:
    roots = {path.relative_to(ROOT).parts[0] for path in iter_python_files()}
    assert {'scripts', 'runtime', 'spine_ultrasound_ui', 'tests'}.issubset(roots)


def test_python_compile_gate_does_not_emit_cache_artifacts(tmp_path: Path) -> None:
    before = {path for path in ROOT.rglob('__pycache__')} | {path for path in ROOT.rglob('*.pyc')}
    assert compile_gate_main() == 0
    after = {path for path in ROOT.rglob('__pycache__')} | {path for path in ROOT.rglob('*.pyc')}
    assert after == before
