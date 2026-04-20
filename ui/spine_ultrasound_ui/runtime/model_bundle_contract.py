from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_model_bundle_manifest(*, bundle_id: str, package_name: str, runtime_profile: str, weights_path: str, entrypoint: str,
                                parameter_path: str, meta_path: str, metrics: dict[str, Any] | None = None,
                                robot_models: list[str] | None = None, runtime_modes: list[str] | None = None,
                                preprocess: dict[str, Any] | None = None, postprocess: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        'bundle_id': bundle_id,
        'bundle_version': 'v1',
        'package_name': package_name,
        'runtime_profile': runtime_profile,
        'artifacts': {
            'weights_path': weights_path,
            'entrypoint': entrypoint,
            'parameter_path': parameter_path,
            'meta_path': meta_path,
        },
        'compatibility': {
            'robot_models': list(robot_models or ['xmate3', 'xmate7', 'xmateer3pro', 'xmateer7pro']),
            'runtime_modes': list(runtime_modes or ['core', 'headless_review']),
        },
        'preprocess': dict(preprocess or {}),
        'postprocess': dict(postprocess or {}),
        'metrics': dict(metrics or {}),
    }


def write_model_bundle_manifest(package_dir: Path, manifest: dict[str, Any]) -> Path:
    path = Path(package_dir) / 'bundle_manifest.json'
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return path


def load_model_bundle_manifest(package_dir: str | Path) -> dict[str, Any]:
    path = Path(package_dir) / 'bundle_manifest.json'
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding='utf-8'))
    required = ['bundle_id', 'bundle_version', 'runtime_profile', 'artifacts', 'compatibility', 'metrics']
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f'missing bundle manifest fields: {", ".join(missing)}')
    return payload
