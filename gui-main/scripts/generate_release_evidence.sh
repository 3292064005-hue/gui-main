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
from spine_ultrasound_ui.services.release_evidence_pack_service import ReleaseEvidencePackService
session_dir = Path(sys.argv[1])
payload = ReleaseEvidencePackService().build(session_dir)
print(json.dumps(payload, indent=2, ensure_ascii=False))
PY
