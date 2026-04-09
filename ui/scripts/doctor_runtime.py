#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.runtime_readiness_manifest_service import RuntimeReadinessManifestService
from spine_ultrasound_ui.services.sdk_environment_doctor_service import SdkEnvironmentDoctorService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight doctor for the vendored xCore desktop/core mainline")
    parser.add_argument("--json", action="store_true", help="emit raw JSON only")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--surface", choices=("desktop", "headless"), default="desktop", help="runtime surface for readiness manifest resolution")
    parser.add_argument("--write-manifest", default="", help="optional path to write the readiness manifest JSON")
    parser.add_argument("--manifest-only", action="store_true", help="emit readiness manifest instead of raw doctor snapshot")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = RuntimeConfig()
    snapshot = SdkEnvironmentDoctorService(ROOT).inspect(config)
    manifest = RuntimeReadinessManifestService(ROOT).build(config=config, surface=args.surface)
    payload = manifest if args.manifest_only else snapshot
    if args.write_manifest:
        Path(args.write_manifest).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.json or args.manifest_only:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"[{snapshot.get('summary_label', 'Doctor')}] {snapshot.get('detail', '')}")
        for item in snapshot.get('blockers', []):
            print(f"BLOCKER  {item.get('name')}: {item.get('detail')}")
        for item in snapshot.get('warnings', []):
            print(f"WARNING  {item.get('name')}: {item.get('detail')}")
        print(f"[Readiness] {manifest.get('summary_label', '')}")
        print(f"Boundary  {manifest.get('verification', {}).get('verification_boundary', '')}")
    state = snapshot.get("summary_state")
    if state == "blocked":
        return 1
    if args.strict and state == "warning":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
