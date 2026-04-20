from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_npz_bundle(path: Path) -> dict[str, Any]:
    import numpy as _np

    fallback = {
        'session_id': '',
        'image': _np.zeros((1, 1), dtype=_np.float32),
        'slices': [],
        'stats': {},
        'row_geometry': [],
        'contributing_frames': [],
        'contribution_map': _np.zeros((1, 1), dtype=_np.float32),
    }
    if not path.exists():
        return fallback

    def _bundle_json(bundle: Any, key: str, default: Any) -> Any:
        if key not in bundle:
            return default
        try:
            return json.loads(str(bundle[key]))
        except Exception:
            return default

    try:
        with _np.load(path, allow_pickle=True) as bundle:
            image = bundle['image'] if 'image' in bundle else fallback['image']
            return {
                'session_id': '',
                'image': image,
                'slices': _bundle_json(bundle, 'slices', []),
                'stats': _bundle_json(bundle, 'stats', {}),
                'row_geometry': _bundle_json(bundle, 'row_geometry', []),
                'contributing_frames': _bundle_json(bundle, 'contributing_frames', []),
                'contribution_map': bundle['contribution_map'] if 'contribution_map' in bundle else _np.zeros_like(image, dtype=_np.float32),
            }
    except Exception:
        return fallback
