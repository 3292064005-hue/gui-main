#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.core.artifact_lifecycle_registry import iter_artifact_lifecycle_specs
from spine_ultrasound_ui.core.artifact_schema_registry import schema_for_artifact


def main() -> int:
    specs = list(iter_artifact_lifecycle_specs())
    if not specs:
        print('artifact lifecycle registry is empty', file=sys.stderr)
        return 1
    seen: set[str] = set()
    errors: list[str] = []
    for spec in specs:
        if spec.artifact_name in seen:
            errors.append(f'duplicate artifact lifecycle entry: {spec.artifact_name}')
        seen.add(spec.artifact_name)
        if not spec.producer:
            errors.append(f'artifact lifecycle entry missing producer: {spec.artifact_name}')
        if not spec.consumers:
            errors.append(f'artifact lifecycle entry missing consumers: {spec.artifact_name}')
        if not spec.source_stage:
            errors.append(f'artifact lifecycle entry missing source_stage: {spec.artifact_name}')
        schema_hint = schema_for_artifact(spec.artifact_name)
        if schema_hint == '' and spec.required_for_release:
            errors.append(f'release-critical artifact missing schema hint: {spec.artifact_name}')
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1
    print(json.dumps({
        'registry_count': len(specs),
        'release_required': [spec.artifact_name for spec in specs if spec.required_for_release],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
