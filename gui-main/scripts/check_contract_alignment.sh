#!/usr/bin/env bash
set -euo pipefail
session_dir="${1:-}"
if [[ -z "$session_dir" ]]; then
  echo "usage: $0 <session_dir>" >&2
  exit 2
fi
python - <<'PY' "$session_dir"
import json, sys
from pathlib import Path
from spine_ultrasound_ui.services.contract_consistency_service import ContractConsistencyService
session_dir = Path(sys.argv[1])
payload = ContractConsistencyService().build(session_dir)
print(json.dumps(payload, indent=2, ensure_ascii=False))
if not payload.get('summary', {}).get('consistent', False):
    raise SystemExit(1)
PY
