#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 scripts/mock_robot_core_server.py &
MOCK_PID=$!
trap 'kill "$MOCK_PID" >/dev/null 2>&1 || true' EXIT
sleep 1
export ROBOT_CORE_PROFILE=mock
export SPINE_DEPLOYMENT_PROFILE=dev
export SPINE_HEADLESS_BACKEND=mock
export SPINE_UI_BACKEND=mock
python3 run.py --backend mock
