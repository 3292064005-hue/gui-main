from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from runtime.bootstrap_env import configure_runtime_environment


def test_package_import_has_no_runtime_side_effects(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("QT_QPA_PLATFORM", None)
    env.pop("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", None)
    env["PYTHONPATH"] = str(root)
    cmd = [
        sys.executable,
        "-c",
        (
            "import os; "
            "import spine_ultrasound_ui; "
            "print(os.environ.get('QT_QPA_PLATFORM','')); "
            "print(os.environ.get('PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION','')); "
            "print(hasattr(spine_ultrasound_ui, 'enable_runtime_compat'))"
        ),
    ]
    completed = subprocess.run(cmd, cwd=root, env=env, check=True, capture_output=True, text=True)
    lines = completed.stdout.splitlines()
    assert lines[:3] == ["", "", "False"]


def test_desktop_bootstrap_requires_real_pyside6(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.delenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", raising=False)

    import importlib.util

    original_find_spec = importlib.util.find_spec

    def _fake_find_spec(name: str, *args, **kwargs):
        if name == "PySide6":
            return None
        return original_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", _fake_find_spec)

    with pytest.raises(RuntimeError, match="PySide6 is required"):
        configure_runtime_environment(require_qt=True)

    if not os.getenv("DISPLAY") and not os.getenv("WAYLAND_DISPLAY"):
        assert os.environ["QT_QPA_PLATFORM"] == "offscreen"
    assert os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] == "python"


def test_desktop_bootstrap_rejects_unsupported_pyside6_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.delenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", raising=False)

    import importlib.util
    from importlib import metadata

    original_find_spec = importlib.util.find_spec

    def _fake_find_spec(name: str, *args, **kwargs):
        if name == "PySide6":
            return object()
        return original_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", _fake_find_spec)
    monkeypatch.setattr(metadata, "version", lambda name: "6.6.9" if name == "PySide6" else "7.34.0")

    with pytest.raises(RuntimeError, match="PySide6>=6.7"):
        configure_runtime_environment(require_qt=True)

    assert os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] == "python"


def test_runtime_bootstrap_rejects_unsupported_protobuf_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.delenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", raising=False)

    from importlib import metadata

    original_version = metadata.version

    def _fake_version(name: str) -> str:
        if name == "protobuf":
            return "8.0.0"
        return original_version(name)

    monkeypatch.setattr(metadata, "version", _fake_version)

    with pytest.raises(RuntimeError, match="protobuf runtime is unsupported"):
        configure_runtime_environment(require_qt=False)

    assert os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] == "python"
