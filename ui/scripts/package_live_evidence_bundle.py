#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services.live_evidence_bundle_service import LiveEvidenceBundleService


REQUIRED_INPUTS = {
    'runtime_config': 'runtime_config.json',
    'phase_metrics': 'rt_phase_metrics.json',
    'readiness_manifest': 'runtime_readiness_manifest.json',
}


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'{path} must contain a top-level JSON object')
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Package a real-controller evidence bundle for verification reporting')
    parser.add_argument('--runtime-config', required=True, help='JSON file captured from get_sdk_runtime_config')
    parser.add_argument('--phase-metrics', required=True, help='JSON file with measured RT phase metrics')
    parser.add_argument('--readiness-manifest', required=True, help='runtime_readiness_manifest.json captured for the same live run')
    parser.add_argument('--output', required=True, help='zip archive path to write')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime_cfg_path = Path(args.runtime_config)
    phase_metrics_path = Path(args.phase_metrics)
    readiness_path = Path(args.readiness_manifest)
    for candidate in (runtime_cfg_path, phase_metrics_path, readiness_path):
        if not candidate.exists():
            raise FileNotFoundError(candidate)
    _load_json(runtime_cfg_path)
    _load_json(phase_metrics_path)
    _load_json(readiness_path)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(runtime_cfg_path, REQUIRED_INPUTS['runtime_config'])
        zf.write(phase_metrics_path, REQUIRED_INPUTS['phase_metrics'])
        zf.write(readiness_path, REQUIRED_INPUTS['readiness_manifest'])
    inspection = LiveEvidenceBundleService(ROOT).inspect(
        str(output_path),
        sdk_binding_requested=True,
        model_binding_requested=True,
    )
    if not inspection.valid:
        output_path.unlink(missing_ok=True)
        raise ValueError(f'packaged live evidence bundle failed validation: {inspection.reason}')
    print(json.dumps({'ok': True, 'bundle': str(output_path), 'inspection': inspection.to_dict()}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
