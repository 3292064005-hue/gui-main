# Rewrite v4 Summary

## Core changes

- Strengthened `CoreRuntime` with formal contracts:
  - capability contract
  - model authority contract
  - release contract
- Tightened `lock_session` so it blocks on mainline legality and capability blockers.
- Tightened `compileScanPlanVerdictLocked(...)` so release decisions include:
  - mainline blockers/warnings
  - plan-hash freeze consistency
  - official limit checks
- Added runtime command handlers for contract queries:
  - `get_capability_contract`
  - `get_model_authority_contract`
  - `get_release_contract`

## Desktop/runtime alignment

- IPC schema now exposes the new contract queries.
- SDK runtime asset service now loads and surfaces:
  - capability contract
  - model authority contract
  - release contract
- Monitor presenter renders the new contract summaries.
- Mock runtime mirrors the new contract/query surface so mock and real do not diverge.

## Session-lock / canonical plan fix

A critical regression was fixed in the scan-start chain:

- Before the fix, `lock_session` froze the hash of the session-bound canonical scan plan, but `load_scan_plan` still sent the pre-lock execution plan.
- That caused a `scan_plan_hash` mismatch and aborted startup before `approach_prescan` / `seek_contact` / `safe_retreat`.
- Now `start_scan()` always switches to the canonical session-bound plan returned by `ensure_locked(...)` before sending `load_scan_plan`.

## Tests

- Added runtime contract enforcement tests.
- Added regression coverage to guarantee `load_scan_plan` uses the session-bound canonical plan.
- Full pytest passes in the current environment.
