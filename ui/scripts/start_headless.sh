#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SPINE_MAINLINE_SURFACE=headless
export SPINE_DEPLOYMENT_PROFILE="${SPINE_DEPLOYMENT_PROFILE:-dev}"
RESOLVED_BACKEND_JSON="$(python3 "$ROOT_DIR/scripts/resolve_headless_backend.py")"
DEFAULT_HEADLESS_BACKEND="$(printf '%s' "$RESOLVED_BACKEND_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("mode", "core"))')"
export SPINE_MAINLINE_BACKEND="${SPINE_MAINLINE_BACKEND:-$DEFAULT_HEADLESS_BACKEND}"
exec python3 "$ROOT_DIR/scripts/start_mainline.py" --surface headless --profile "$SPINE_DEPLOYMENT_PROFILE" --backend "$SPINE_MAINLINE_BACKEND" "$@"
