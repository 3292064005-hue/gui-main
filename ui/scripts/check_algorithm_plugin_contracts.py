#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services.algorithms.plugin_plane import PluginPlane


def main() -> int:
    plane = PluginPlane()
    plugins = list(plane.all_plugins()) + list(plane.guidance_plugins())
    seen: set[str] = set()
    errors: list[str] = []
    rows: list[dict[str, str]] = []
    for plugin in plugins:
        if plugin.plugin_id in seen:
            errors.append(f'duplicate plugin id: {plugin.plugin_id}')
        seen.add(plugin.plugin_id)
        if not str(plugin.stage).strip():
            errors.append(f'plugin missing stage: {plugin.plugin_id}')
        if not str(plugin.plugin_version).strip():
            errors.append(f'plugin missing version: {plugin.plugin_id}')
        if not isinstance(plugin.input_schema, dict) or not plugin.input_schema:
            errors.append(f'plugin missing input schema: {plugin.plugin_id}')
        if not isinstance(plugin.output_schema, dict) or not plugin.output_schema:
            errors.append(f'plugin missing output schema: {plugin.plugin_id}')
        rows.append({
            'plugin_id': plugin.plugin_id,
            'stage': plugin.stage,
            'version': plugin.plugin_version,
        })
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1
    print(json.dumps({'plugin_count': len(rows), 'plugins': rows}, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
