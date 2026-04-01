#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT_DIR/scripts/doctor_runtime.py" --json || true
python3 "$ROOT_DIR/scripts/doctor_runtime.py" --strict --json
exec bash "$ROOT_DIR/scripts/start_hil.sh"
