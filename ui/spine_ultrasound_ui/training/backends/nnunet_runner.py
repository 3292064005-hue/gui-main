from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import ensure_dir, now_text


def build_nnunet_launch_plan(request_path: Path) -> dict[str, Any]:
    """Build an nnU-Net launch plan from a serialized training request.

    Args:
        request_path: Path to the generated training request file.

    Returns:
        Launch plan describing required modules, environment variables, and the
        CLI command expected by nnU-Net v2.

    Raises:
        FileNotFoundError: Raised when the request file does not exist.

    Boundary behaviour:
        The launch plan never executes nnU-Net directly. It records the raw
        dataset root and converted dataset directory so operators can launch the
        training inside a dedicated nnU-Net environment with explicit paths.
    """
    request_path = Path(request_path)
    if not request_path.exists():
        raise FileNotFoundError(request_path)
    payload = json.loads(request_path.read_text(encoding='utf-8'))
    extra = dict(payload.get('backend_payload', {}))
    dataset_id = str(extra.get('dataset_id', 'TBD_DATASET_ID'))
    configuration = str(extra.get('configuration', '2d') or '2d')
    fold = str(extra.get('fold', '0') or '0')
    plans = str(extra.get('plans', 'nnUNetPlans') or 'nnUNetPlans')
    command = ['nnUNetv2_train', dataset_id, configuration, fold]
    if plans:
        command.extend(['-p', plans])
    nnunet_raw_root = str(extra.get('nnunet_raw_root', '') or '')
    return {
        'generated_at': now_text(),
        'trainer_backend': 'nnunetv2',
        'request_path': str(request_path),
        'required_modules': ['torch', 'nnunetv2'],
        'environment': {
            'nnUNet_raw': nnunet_raw_root,
            'nnUNet_preprocessed': str(Path(nnunet_raw_root).parent / 'nnUNet_preprocessed') if nnunet_raw_root else '',
            'nnUNet_results': str(Path(nnunet_raw_root).parent / 'nnUNet_results') if nnunet_raw_root else '',
        },
        'command': command,
        'task': payload.get('backend_payload', {}).get('task', ''),
        'nnunet_dataset_dir': str(extra.get('nnunet_dataset_dir', '') or ''),
        'conversion_manifest_path': str(extra.get('conversion_manifest_path', '') or ''),
    }


def run_request(request_path: Path) -> dict[str, Any]:
    """Validate nnU-Net availability and emit an execution manifest.

    Args:
        request_path: Path to the serialized training request.

    Returns:
        Execution manifest describing the resolved environment and converted raw
        dataset location.

    Raises:
        FileNotFoundError: Raised when the request file does not exist.
        RuntimeError: Raised when the converted dataset directory is missing.

    Boundary behaviour:
        The function validates environment prerequisites and dataset conversion
        outputs only. It does not execute ``nnUNetv2_train`` inside the desktop
        runtime environment.
    """
    request_path = Path(request_path)
    if not request_path.exists():
        raise FileNotFoundError(request_path)
    torch = importlib.import_module('torch')
    nnunet = importlib.import_module('nnunetv2')
    payload = json.loads(request_path.read_text(encoding='utf-8'))
    extra = dict(payload.get('backend_payload', {}))
    dataset_dir = Path(str(extra.get('nnunet_dataset_dir', '') or ''))
    if not dataset_dir.exists():
        raise RuntimeError(f'nnU-Net dataset directory does not exist: {dataset_dir}')
    conversion_manifest = Path(str(extra.get('conversion_manifest_path', '') or ''))
    manifest = {
        'generated_at': now_text(),
        'status': 'validated',
        'trainer_backend': 'nnunetv2',
        'request_path': str(request_path),
        'torch_version': str(getattr(torch, '__version__', '') or ''),
        'nnunet_version': str(getattr(nnunet, '__version__', '') or ''),
        'task': payload.get('backend_payload', {}).get('task', ''),
        'nnunet_dataset_dir': str(dataset_dir),
        'conversion_manifest_path': str(conversion_manifest) if conversion_manifest.exists() else '',
    }
    output_dir = ensure_dir(request_path.parent)
    (output_dir / 'nnunet_execution_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Validate an nnU-Net training request')
    parser.add_argument('--request', required=True, type=Path)
    args = parser.parse_args(argv)
    run_request(args.request)
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
