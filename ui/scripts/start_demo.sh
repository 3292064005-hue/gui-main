#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SPINE_MAINLINE_SURFACE=desktop
export SPINE_DEPLOYMENT_PROFILE="${SPINE_DEPLOYMENT_PROFILE:-dev}"
export SPINE_MAINLINE_BACKEND="${SPINE_MAINLINE_BACKEND:-mock}"
exec python3 "$ROOT_DIR/scripts/start_mainline.py" --surface desktop --profile "$SPINE_DEPLOYMENT_PROFILE" --backend "$SPINE_MAINLINE_BACKEND" "$@"
