from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService


def main() -> int:
    snapshot = DeploymentProfileService(dict(os.environ)).build_snapshot()
    required = [
        "name",
        "allows_write_commands",
        "requires_strict_control_authority",
        "requires_session_evidence_seal",
        "review_only",
        "log_granularity",
        "seal_strength",
        "provenance_strength",
    ]
    missing = [key for key in required if key not in snapshot]
    if missing:
        print(json.dumps({"ok": False, "missing": missing}, ensure_ascii=False))
        return 1
    if snapshot["name"] == "clinical" and not snapshot.get("requires_api_token", False):
        print(json.dumps({"ok": False, "reason": "clinical profile must require api token"}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True, "profile": snapshot}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
