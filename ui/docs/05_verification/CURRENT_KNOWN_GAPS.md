---
category: verification
authority: canonical
audience: reviewers, operators, auditors
owner: repository
status: active
---

# Current Known Gaps

## Open items that must stay visible

### P0-01
The repository now carries an explicit xMateModel compile gate (`test_xmate_model_compile_contract`) and manifest/runtime parity gate (`scripts/check_runtime_contract_parity.py`). The compile gate is profile-aware: mock builds do not register it, while SDK/model-enabled profiles must compile it. This closes the previous “string-presence only” proof gap at the build-contract layer, but does **not** replace live controller or HIL evidence.

### P1-03
Authoritative precheck is now required to pass the intended build path and the generated command/runtime contract parity gate before release scripts can succeed. Full closure still depends on enabled SDK/model builds plus end-to-end behavior proof on the intended surface.

### P2-03
Acceptance scripts, test inventory, and the consolidated `release_ledger.json` are now aligned at the report-index layer, and `research`/`clinical` ledger generation is fail-closed without archived live/HIL evidence. A final release claim still requires complete build/test proof for the enabled runtime path, plus live/HIL evidence where relevant.

## Usage rule
No release, audit, or readiness statement may contradict this file without attaching the new evidence that closes the gap.

## Recently closed
- The acceptance summary / release ledger chain no longer records a synthetic local `runtime_readiness_manifest.json` when proof comes from an archived live evidence bundle; that path now preserves bundle-local readiness evidence without creating dead links.
- Repository hygiene now rejects build-machine absolute paths captured inside committed model package manifests.
