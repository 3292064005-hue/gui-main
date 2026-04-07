from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUPPORTED_TRAINER_BACKENDS = {
    'numpy_baseline',
    'monai',
    'monai_label',
    'nnunetv2',
}


def load_structured_config(path: Path) -> dict[str, Any]:
    """Load a JSON or YAML-like configuration payload.

    Args:
        path: Configuration file path.

    Returns:
        Parsed configuration payload.

    Raises:
        FileNotFoundError: Raised when the file does not exist.
        RuntimeError: Raised when YAML parsing is requested without an
            available YAML parser.
        ValueError: Raised when the file extension is unsupported.

    Boundary behaviour:
        JSON files are always supported via the standard library. YAML files are
        supported only when a YAML parser is installed; this keeps the training
        interface import-safe in the default runtime environment.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() == '.json':
        return json.loads(path.read_text(encoding='utf-8'))
    if path.suffix.lower() in {'.yaml', '.yml'}:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError('YAML parsing requires PyYAML to be installed') from exc
        payload = yaml.safe_load(path.read_text(encoding='utf-8'))
        return dict(payload or {})
    raise ValueError(f'unsupported config format: {path.suffix}')


def normalize_trainer_backend(value: str | None) -> str:
    """Normalize trainer backend aliases.

    Args:
        value: Raw backend value.

    Returns:
        Canonical backend name.

    Raises:
        ValueError: Raised when the backend is unsupported.

    Boundary behaviour:
        Empty values fall back to ``numpy_baseline`` so historical configs keep
        working without requiring manual migration.
    """
    raw = str(value or 'numpy_baseline').strip().lower()
    alias_map = {
        'numpy': 'numpy_baseline',
        'baseline': 'numpy_baseline',
        'monai_bundle': 'monai',
        'monailabel': 'monai_label',
        'nnunet': 'nnunetv2',
        'nnunet_v2': 'nnunetv2',
    }
    normalized = alias_map.get(raw, raw)
    if normalized not in SUPPORTED_TRAINER_BACKENDS:
        raise ValueError(f'unsupported trainer_backend: {value}')
    return normalized
