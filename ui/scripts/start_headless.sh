#!/usr/bin/env bash
set -euo pipefail

# Official Ubuntu 22.04 headless launcher.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

: "${SPINE_DEPLOYMENT_PROFILE:=dev}"
: "${SPINE_HEADLESS_BACKEND:=core}"
export SPINE_DEPLOYMENT_PROFILE
export SPINE_HEADLESS_BACKEND

python3 -m uvicorn spine_ultrasound_ui.api_server:app --host 0.0.0.0 --port 8000
