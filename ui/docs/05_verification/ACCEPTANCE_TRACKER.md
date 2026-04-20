---
category: verification
authority: canonical
audience: reviewers, auditors, project leads
owner: repository
status: active
---

# Acceptance Tracker

## Integrated status snapshot
- P2-1: repository governance and canonical dependency closure tracked in current canonical docs
- P2-2: evidence/model bundle/runtime contract closure tracked in current canonical docs
- P2-3: acceptance/build/HIL proof chain must remain aligned with the enabled path
- P0-01: code-closed on the core path; write-command authority now terminates in `cpp_robot_core`, while Python/headless only forwards lease requests and command context
- P0-02: code-closed via shared `BackendCommandErrorService.build_reply(...)` usage in direct core and API bridge command surfaces
- P0-03: process-closed at the report-index layer only; build/live/HIL evidence must still be reported by proof tier and may not be over-claimed
- P1-01: closed via canonical `start_procedure(scan)` on workflow + desktop action surfaces
- P1-02: closed
- P1-03: partially closed; model-backed authoritative feasibility still requires complete build/test evidence on the target path
- P2-01: largely closed
- P2-02: closed
- P2-03: partially closed; acceptance/build/test proof must cover the same enabled path that the claim references

## How to update
When a stage closes, update:
1. evidence scope
2. remaining gap description
3. linked build/HIL proof


## Canonical follow-up documents
- `docs/05_verification/CURRENT_KNOWN_GAPS.md`
- `docs/05_verification/HIL_AND_BUILD_EVIDENCE.md`


## P2 acceptance gate usage
- `scripts/check_p2_acceptance.py` is **fail-closed** by default and does not assume repo-embedded artifacts.
- For audited build review, run it against the canonical output directory: `P2_ACCEPTANCE_OUTPUT_ROOT="$BUILD_DIR/p2_acceptance" python3 scripts/check_p2_acceptance.py`.
- For an explicit self-generated review run, opt in with: `P2_ACCEPTANCE_OUTPUT_ROOT="$BUILD_DIR/p2_acceptance" P2_ACCEPTANCE_ALLOW_GENERATE=1 python3 scripts/check_p2_acceptance.py`.
- Do not describe a self-generated review run as audited build proof.
