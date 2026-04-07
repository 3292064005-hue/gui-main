from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import ensure_dir, now_text


def build_monai_launch_plan(request_path: Path) -> dict[str, Any]:
    """Build a MONAI launch plan from a serialized training request.

    Args:
        request_path: Path to the generated training request file.

    Returns:
        Launch plan describing required modules and execution hints.

    Raises:
        FileNotFoundError: Raised when the request file does not exist.

    Boundary behaviour:
        The launch plan does not execute training by itself. It records a stable
        command specification that operators can run inside a MONAI-capable
        environment.
    """
    request_path = Path(request_path)
    if not request_path.exists():
        raise FileNotFoundError(request_path)
    payload = json.loads(request_path.read_text(encoding='utf-8'))
    return {
        'generated_at': now_text(),
        'trainer_backend': 'monai',
        'runner_module': 'spine_ultrasound_ui.training.backends.monai_runner',
        'request_path': str(request_path),
        'required_modules': ['torch', 'monai'],
        'command': ['python', '-m', 'spine_ultrasound_ui.training.backends.monai_runner', '--request', str(request_path)],
        'task': payload.get('backend_payload', {}).get('task', ''),
    }


def run_request(request_path: Path) -> dict[str, Any]:
    """Validate MONAI availability and emit an execution manifest.

    Args:
        request_path: Path to the serialized training request.

    Returns:
        Execution manifest describing the resolved backend environment.

    Raises:
        RuntimeError: Raised when PyTorch or MONAI are unavailable.
        FileNotFoundError: Raised when the request file does not exist.

    Boundary behaviour:
        The function intentionally stops after environment validation and
        manifest emission. Training kernels stay external to the desktop runtime
        repository and can be implemented incrementally without changing the
        request contract.
    """
    request_path = Path(request_path)
    if not request_path.exists():
        raise FileNotFoundError(request_path)
    torch = importlib.import_module('torch')
    monai = importlib.import_module('monai')
    payload = json.loads(request_path.read_text(encoding='utf-8'))
    manifest = {
        'generated_at': now_text(),
        'status': 'validated',
        'trainer_backend': 'monai',
        'request_path': str(request_path),
        'torch_version': str(getattr(torch, '__version__', '') or ''),
        'monai_version': str(getattr(monai, '__version__', '') or ''),
        'task': payload.get('backend_payload', {}).get('task', ''),
    }
    output_dir = ensure_dir(request_path.parent)
    (output_dir / 'monai_execution_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Validate a MONAI training request')
    parser.add_argument('--request', required=True, type=Path)
    args = parser.parse_args(argv)
    run_request(args.request)
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
