#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SPINE_MAINLINE_SURFACE=desktop
export ROBOT_CORE_PROFILE=prod
export SPINE_MAINLINE_BACKEND=core
export SPINE_DOCTOR_STRICT=1
export ROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-ON}"
exec python3 "$ROOT_DIR/scripts/start_mainline.py" --surface desktop --profile prod --backend core "$@"
