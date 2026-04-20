---
category: runbook
authority: canonical
audience: release engineers, auditors, reviewers
owner: repository
status: active
---

# Release Ledger

## Purpose
Provide one claim-safe file that indexes the proof artifacts produced by the final acceptance flow.

## Canonical artifact
- `release_ledger.json`

## Required linked inputs
- `verification_execution_report.json`
- `runtime_readiness_manifest.json` when the acceptance run generated a standalone local readiness file
- `build_evidence_report.json`
- `acceptance_summary.json`
- archived live evidence bundle when one exists for the claim; its embedded `runtime_readiness_manifest.json` is the canonical readiness proof for that path

## Rules
- The release ledger does not replace upstream proof artifacts.
- The release ledger must never strengthen the claim boundary beyond what the linked artifacts already prove.
- Missing or invalid linked JSON must appear as absent evidence, not as synthesized success.

## Producer
- `scripts/write_release_ledger.py`
- `scripts/final_acceptance_audit.sh` invokes the script automatically after acceptance summary generation.

## Live-bundle rule
- When `final_acceptance_audit.sh` is driven by `LIVE_EVIDENCE_BUNDLE`, the release ledger must not synthesize a local `runtime_readiness_manifest.json` link just to satisfy indexing.
- In that mode the ledger reads runtime-readiness summary fields from `verification_execution_report.json`, which already mirrors the archived bundle evidence, and keeps `readiness_manifest` empty unless a real local manifest was generated.
