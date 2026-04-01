#!/usr/bin/env bash
set -euo pipefail
SESSION_DIR="${1:-}"
if [[ -z "$SESSION_DIR" ]]; then
  echo "usage: $0 <session_dir>" >&2
  exit 2
fi
python - "$SESSION_DIR" <<'PY'
import json
import sys
from pathlib import Path
from spine_ultrasound_ui.services.release_gate_decision_service import ReleaseGateDecisionService
session_dir = Path(sys.argv[1])
payload = ReleaseGateDecisionService().build(session_dir)
print(json.dumps(payload, indent=2, ensure_ascii=False))
raise SystemExit(0 if payload.get('release_allowed', False) else 1)
PY
