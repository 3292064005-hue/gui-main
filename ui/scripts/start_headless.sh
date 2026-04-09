#!/usr/bin/env bash
set -euo pipefail

# Official Ubuntu 22.04 headless launcher.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
: "${SPINE_DEPLOYMENT_PROFILE:=dev}"
if [[ -z "${SPINE_HEADLESS_BACKEND:-}" ]]; then
  SPINE_HEADLESS_BACKEND="$($PYTHON_BIN scripts/resolve_headless_backend.py | $PYTHON_BIN -c 'import json,sys; print(json.load(sys.stdin)["mode"])')"
fi
export SPINE_DEPLOYMENT_PROFILE
export SPINE_HEADLESS_BACKEND

"$PYTHON_BIN" -m uvicorn spine_ultrasound_ui.api_server:app --host 0.0.0.0 --port 8000
