from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("SPINE_HEADLESS_BACKEND", os.getenv("SPINE_HEADLESS_BACKEND", "mock"))

from spine_ultrasound_ui.api_server import app  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the FastAPI OpenAPI schema for the frontend contract pipeline.")
    parser.add_argument("--output", required=True, help="Output path for the generated openapi.json")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = app.openapi()
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote OpenAPI schema to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
