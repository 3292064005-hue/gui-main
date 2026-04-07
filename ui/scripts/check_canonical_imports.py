from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

BANNED_MODULES: dict[str, str] = {
    'spine_ultrasound_ui.compat': 'tests.runtime_compat',
    'spine_ultrasound_ui.core.event_bus': 'spine_ultrasound_ui.core.ui_local_bus',
    'spine_ultrasound_ui.services.runtime_event_platform': 'spine_ultrasound_ui.services.event_bus or spine_ultrasound_ui.services.event_replay_bus',
    'spine_ultrasound_ui.services.sdk_unit_contract': 'spine_ultrasound_ui.utils.sdk_unit_contract',
    'spine_ultrasound_ui.core_pipeline.shm_client': 'spine_ultrasound_ui.services.transport.shm_client',
}
BANNED_FILES = [
    'spine_ultrasound_ui/compat.py',
    'spine_ultrasound_ui/core/event_bus.py',
    'spine_ultrasound_ui/services/runtime_event_platform.py',
    'spine_ultrasound_ui/services/sdk_unit_contract.py',
    'spine_ultrasound_ui/core_pipeline/shm_client.py',
]


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for folder in ['spine_ultrasound_ui', 'runtime', 'scripts', 'tests']:
        files.extend((ROOT / folder).rglob('*.py'))
    return [path for path in files if '.pytest_cache' not in path.parts and '__pycache__' not in path.parts]


def main() -> int:
    violations: list[str] = []
    for rel in BANNED_FILES:
        if (ROOT / rel).exists():
            violations.append(f'legacy shim file still exists: {rel}')
    for path in iter_python_files():
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in BANNED_MODULES:
                        violations.append(f'{path.relative_to(ROOT)} imports banned module {alias.name}; use {BANNED_MODULES[alias.name]}')
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if module in BANNED_MODULES:
                    violations.append(f'{path.relative_to(ROOT)} imports from banned module {module}; use {BANNED_MODULES[module]}')
                if module == 'spine_ultrasound_ui' and any(alias.name == 'enable_runtime_compat' for alias in node.names):
                    violations.append(f'{path.relative_to(ROOT)} imports package-level enable_runtime_compat; use tests.runtime_compat.enable_runtime_compat')
    if violations:
        for item in violations:
            print(f'[FAIL] {item}')
        return 1
    print('[PASS] canonical import audit clean')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
