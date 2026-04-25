#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "artifacts" / "verification" / "current_mainline_full_closure" / "verification_summary.json"
FORBIDDEN_CLAIM_PHRASES = (
    "fully verified",
    "complete release verification",
    "hil passed",
    "live scan passed",
    "real device verified",
    "real-device verified",
    "preempt_rt verified",
    "research clinical verified",
)
REQUIRED_NOT_EXECUTED = {
    "real xCore controller connection",
    "HIL/live scan",
    "C++ full CMake build",
    "full pytest",
    "PySide6 UI runtime",
}
REQUIRED_STATIC_SCOPE_TOKENS = (
    "Static/sandbox evidence only",
    "does not represent real-device",
    "HIL",
    "live scan",
)


def main() -> int:
    errors: list[str] = []
    if not SUMMARY.exists():
        print(f"missing verification summary: {SUMMARY.relative_to(ROOT)}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"invalid verification summary JSON: {exc}", file=sys.stderr)
        return 1
    text = SUMMARY.read_text(encoding="utf-8")
    lowered = text.lower()
    for phrase in FORBIDDEN_CLAIM_PHRASES:
        if phrase in lowered:
            errors.append(f"verification summary over-claims unsupported environment proof: {phrase}")
    not_executed = set(str(item) for item in payload.get("not_executed", []))
    missing_not_executed = sorted(REQUIRED_NOT_EXECUTED - not_executed)
    if missing_not_executed:
        errors.append(f"verification summary missing non-executed proof boundaries: {missing_not_executed}")
    notes = str(payload.get("notes", ""))
    for token in REQUIRED_STATIC_SCOPE_TOKENS:
        if token not in notes:
            errors.append(f"verification summary missing static claim-boundary token: {token}")
    if str(payload.get("verification_scope", "")).lower().find("static") < 0:
        errors.append("verification_scope must explicitly say static/sandbox for mainline closure evidence")
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1
    print("mainline claim boundary ok: static/sandbox proof only; live/HIL claims remain explicitly not executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
