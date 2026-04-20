#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifests = list(ROOT.glob('models/*/bundle_manifest.json'))
    if not manifests:
        print('[FAIL] no model bundle manifests found', file=sys.stderr)
        return 1
    required = {'bundle_id', 'bundle_version', 'runtime_profile', 'artifacts', 'compatibility', 'metrics'}
    for path in manifests:
        payload = json.loads(path.read_text(encoding='utf-8'))
        missing = sorted(required - payload.keys())
        if missing:
            print(f'[FAIL] {path}: missing {missing}', file=sys.stderr)
            return 1
        artifacts = payload.get('artifacts', {})
        for key in ('weights_path', 'entrypoint'):
            if not artifacts.get(key):
                print(f'[FAIL] {path}: artifacts.{key} missing', file=sys.stderr)
                return 1
    print(f'[OK] validated {len(manifests)} model bundle manifests')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
