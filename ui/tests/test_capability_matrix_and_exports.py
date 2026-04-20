from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from spine_ultrasound_ui.services.backend_capability_matrix_service import BackendCapabilityMatrixService
from spine_ultrasound_ui.services.backend_base import BackendBase


class _Backend(BackendBase):
    def start(self) -> None:
        return None

    def update_runtime_config(self, config) -> None:  # pragma: no cover - compatibility shim only
        return None

    def send_command(self, command: str, payload=None, *, context=None):  # pragma: no cover - not used here
        raise NotImplementedError


def test_capability_matrix_service_projects_visibility_modes() -> None:
    matrix = BackendCapabilityMatrixService.build({
        'camera': 'hidden',
        'ultrasound': 'monitor_only',
        'reconstruction': 'executable',
        'recording': 'monitor_only',
    })
    assert matrix['camera']['visible'] is False
    assert matrix['ultrasound']['monitor_only'] is True
    assert matrix['reconstruction']['executable'] is True
    assert BackendCapabilityMatrixService.to_media_capabilities(matrix) == {
        'camera': False,
        'ultrasound': True,
        'reconstruction': True,
        'recording': False,
    }


def test_backend_base_exposes_capability_matrix_contract() -> None:
    backend = _Backend()
    matrix = backend.capability_matrix()
    assert matrix['camera']['mode'] == 'hidden'
    assert backend.media_capabilities()['camera'] is False
    assert backend.media_capabilities()['recording'] is False


def _run_python_snippet(snippet: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, '-c', snippet],
        cwd=str(Path('.').resolve()),
        text=True,
        capture_output=True,
        check=False,
    )


def test_core_package_import_is_headless_safe() -> None:
    proc = _run_python_snippet(
        'import spine_ultrasound_ui.core as core; '
        'print(hasattr(core, "__all__")); '
        'print("AppController" in getattr(core, "__all__", []))'
    )
    assert proc.returncode == 0, proc.stderr


def test_utils_package_import_is_headless_safe() -> None:
    proc = _run_python_snippet(
        'from spine_ultrasound_ui import utils; '
        'print(utils.now_text()); '
        'print("generate_demo_pixmap" in getattr(utils, "__all__", []))'
    )
    assert proc.returncode == 0, proc.stderr


def test_core_and_utils_packages_use_lazy_exports() -> None:
    core_init = Path('spine_ultrasound_ui/core/__init__.py').read_text(encoding='utf-8')
    utils_init = Path('spine_ultrasound_ui/utils/__init__.py').read_text(encoding='utf-8')
    assert '__getattr__' in core_init
    assert '__getattr__' in utils_init
    assert 'def __getattr__' in core_init
    assert 'def __getattr__' in utils_init
    assert 'TYPE_CHECKING' in core_init
    assert 'TYPE_CHECKING' in utils_init
