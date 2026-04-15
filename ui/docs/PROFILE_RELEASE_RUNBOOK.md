# Profile / Release / Evidence Runbook

This runbook operationalizes the repository governance rules for the active runtime profiles. It does not replace the release/profile matrices; it turns them into a repeatable execution checklist.

## Shared rules

1. `control_authority`, `final_verdict`, and `authoritative_runtime_envelope` must be read from the canonical governance projection via `RuntimeGovernanceQuerySurface`.
2. Canonical plan precheck command is `validate_scan_plan`. `compile_scan_plan` is compatibility-only and must not be used in new code paths.
3. Session export/review artifacts must carry `authority_metadata` so degraded or prior-assisted outputs are not rendered as authoritative results.
4. Release evidence must record the proof level used for validation: static, sandbox, or HIL/live.

## Dev / mock profile

Preconditions:
- Mock backend selected explicitly.
- No live-hardware claim is emitted.
- Authority source is marked mock or simulated.

Checklist:
- `python scripts/check_protocol_sync.py`
- `python scripts/run_pytest_mainline.py -q --layer contract`
- `python scripts/run_pytest_mainline.py -q --layer mock_e2e`

Rollback:
- Revert to previous manifest + generated registry pair.
- Re-enable compatibility alias path if a newly promoted canonical command breaks mock UI flows.

## Lab / core profile

Preconditions:
- Runtime contracts available from `cpp_robot_core`.
- Control authority shows no lease conflict.
- Final verdict is supplied by runtime kernel or query surface.

Checklist:
- `python scripts/check_protocol_sync.py`
- `python scripts/run_pytest_mainline.py -q --layer runtime_core`
- `python scripts/run_pytest_mainline.py -q --layer surface_integration`
- C++ configure in the intended profile (`ROBOT_CORE_PROFILE=mock|hil|prod`)

Rollback:
- Restore previous C++ registry/include pair and revert dispatcher lane change.
- Fall back to compatibility shell consumers while keeping governance projection additive-only.

## Clinical / review profile

Preconditions:
- Session is locked.
- Exported assessment artifacts contain `authority_metadata`.
- Review suitability is explicitly encoded for each exported artifact.

Checklist:
- Confirm governance projection summary is not blocked.
- Confirm final verdict source and authority source are present in exported metadata.
- Confirm release package includes evidence ID / lineage where applicable.

Rollback:
- Stop clinical/review export promotion for artifacts missing authority metadata.
- Revert to previous reader/exporter revision that last produced authoritative metadata-complete outputs.
