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
from spine_ultrasound_ui.services.sdk_environment_doctor_service import SdkEnvironmentDoctorService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight doctor for the vendored xCore desktop/core mainline")
    parser.add_argument("--json", action="store_true", help="emit raw JSON only")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = RuntimeConfig()
    snapshot = SdkEnvironmentDoctorService(ROOT).inspect(config)
    if args.json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
    else:
        print(f"[{snapshot.get('summary_label', 'Doctor')}] {snapshot.get('detail', '')}")
        for item in snapshot.get('blockers', []):
            print(f"BLOCKER  {item.get('name')}: {item.get('detail')}")
        for item in snapshot.get('warnings', []):
            print(f"WARNING  {item.get('name')}: {item.get('detail')}")
    state = snapshot.get("summary_state")
    if state == "blocked":
        return 1
    if args.strict and state == "warning":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
