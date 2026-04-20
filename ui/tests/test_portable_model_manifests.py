from __future__ import annotations

import json
from pathlib import Path


def test_committed_model_manifests_do_not_capture_build_machine_absolute_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    flagged: list[str] = []
    keys = {'runtime_model_path', 'package_dir', 'dataset_manifest', 'output_dir'}
    for path in (repo_root / 'models').rglob('*.json'):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        stack = [payload]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key, value in current.items():
                    if key in keys and isinstance(value, str):
                        if value.startswith('/tmp/') or value.startswith('/mnt/data/') or (len(value) > 2 and value[1] == ':' and value[2] in ('\\', '/')):
                            flagged.append(f"{path.relative_to(repo_root)}::{key}={value}")
                    if isinstance(value, (dict, list)):
                        stack.append(value)
            elif isinstance(current, list):
                stack.extend(item for item in current if isinstance(item, (dict, list)))
    assert not flagged, '\n'.join(flagged)
