from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.training.specs.common import load_structured_config


def resolve_model_package(target: str | Path) -> dict[str, Any]:
    """Resolve a runtime model package from a directory or config file.

    Args:
        target: Model package directory or runtime config file.

    Returns:
        Dictionary containing ``package_dir``, ``meta``, and ``parameters``.

    Raises:
        FileNotFoundError: Raised when the package or declared runtime artifact
            cannot be found.
        ValueError: Raised when metadata files are missing.

    Boundary behaviour:
        Config files may either point directly to a package directory or to a
        specific model binary. Relative package paths inside configs are
        resolved relative to the config file itself. When a runtime model file
        or benchmark manifest is declared they are attached to the resolved
        metadata so release gates can validate the package deterministically.
    """
    target_path = Path(target)
    config_payload: dict[str, Any] = {}
    if target_path.is_file() and target_path.suffix.lower() in {'.json', '.yaml', '.yml'}:
        config_payload = load_structured_config(target_path)
        package_hint = config_payload.get('package_dir') or config_payload.get('model_dir') or target_path.parent
        package_dir = (target_path.parent / str(package_hint)).resolve() if not Path(str(package_hint)).is_absolute() else Path(str(package_hint))
    else:
        package_dir = target_path.resolve()
    if not package_dir.exists():
        raise FileNotFoundError(package_dir)
    meta_path = package_dir / 'model_meta.json'
    parameter_path = package_dir / 'parameters.json'
    if not meta_path.exists() or not parameter_path.exists():
        raise ValueError(f'invalid model package: {package_dir}')
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    parameters = json.loads(parameter_path.read_text(encoding='utf-8'))

    runtime_model_hint = str(meta.get('runtime_model_path', '') or config_payload.get('runtime_model_path', '') or '')
    runtime_model_path: Path | None = Path(runtime_model_hint) if runtime_model_hint else None
    if runtime_model_hint:
        runtime_model_path = runtime_model_path if runtime_model_path.is_absolute() else (package_dir / runtime_model_path)
        if not runtime_model_path.exists():
            raise FileNotFoundError(runtime_model_path)
        meta['runtime_model_path'] = str(runtime_model_path)

    benchmark_manifest_hint = str(config_payload.get('benchmark_manifest', '') or meta.get('benchmark_manifest_path', '') or '')
    benchmark_manifest_path: Path | None = Path(benchmark_manifest_hint) if benchmark_manifest_hint else None
    if benchmark_manifest_hint:
        benchmark_manifest_path = benchmark_manifest_path if benchmark_manifest_path.is_absolute() else (target_path.parent / benchmark_manifest_path if target_path.is_file() else package_dir / benchmark_manifest_path)
        if not benchmark_manifest_path.exists():
            raise FileNotFoundError(benchmark_manifest_path)
        meta['benchmark_manifest_path'] = str(benchmark_manifest_path)

    hash_parts = [meta_path.read_bytes(), b'\n', parameter_path.read_bytes()]
    if runtime_model_path is not None and runtime_model_path.exists():
        hash_parts.extend([b'\n', runtime_model_path.read_bytes()])
    if benchmark_manifest_path is not None and benchmark_manifest_path.exists():
        hash_parts.extend([b'\n', benchmark_manifest_path.read_bytes()])
    package_hash = hashlib.sha256(b''.join(hash_parts)).hexdigest()
    meta.setdefault('backend', str(config_payload.get('backend', meta.get('backend', 'unknown'))))
    meta.setdefault('package_name', package_dir.name)
    meta['package_dir'] = str(package_dir)
    meta['package_hash'] = package_hash
    if config_payload:
        meta['config_ref'] = str(target_path)
    return {
        'package_dir': package_dir,
        'meta': meta,
        'parameters': parameters,
        'config': config_payload,
    }
