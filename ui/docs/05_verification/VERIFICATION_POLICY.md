---
category: verification
authority: canonical
audience: reviewers, auditors, release engineers
owner: repository
status: active
---

# Verification Policy

## Evidence levels
- Static confirmation
- Sandbox verification
- Repository proof
- Profile gate proof
- Live-controller proof
- HIL proof

## Truthfulness rules
- Do not describe static confirmation as complete delivery proof.
- Do not describe contract-shell or mock validation as live controller validation.
- When a capability depends on SDK/model-on builds, default-off validation does not close that capability.

## Required reporting language
Every review or delivery summary must separate results into:
- **已静态确认**
- **已沙箱验证**
- **未真实环境验证**

## Readiness manifest rule
Runtime doctor/readiness output is not by itself live-runtime proof. When live evidence exists, the readiness manifest must be archived inside the same evidence bundle used by the claim.

## Execution report rule
Verification execution reports are the machine-readable ceiling for allowed claims. Human summaries must not exceed the scope recorded in the report.

## Acceptance threshold
A build is not fully releasable merely because Blocker and Critical counts are zero. Verification completeness and evidence scope must also match the claim being made.

## Active gate and archive coverage
- The active mainline verification surface is `python scripts/run_pytest_mainline.py -q` together with `scripts/verify_mainline.sh` and `scripts/final_acceptance_audit.sh`.
- Historical compatibility suites under `tests/archive/` are opt-in only and must not be confused with the active mainline gate.
- Top-level `tests/test_*.py` files must belong to the current mainline surface.

## Layered execution guidance
Use layered runs to isolate failures to a specific surface:
```bash
python scripts/run_pytest_mainline.py -q --report-layers
python scripts/run_pytest_mainline.py -q --layer unit
python scripts/run_pytest_mainline.py -q --layer contract
python scripts/run_pytest_mainline.py -q --layer runtime_core
python scripts/run_pytest_mainline.py -q --layer surface_integration
python scripts/run_pytest_mainline.py -q --layer mock_e2e
```

## Dual-Ledger Verification

Repository verification and live-controller verification are tracked separately. `repo_truth_ledger` records code/protocol/gate evidence. `live_truth_ledger` records controller logs, phase transitions, jitter/packet-loss observations, and final verdict traces.


Runtime-config evidence is now anchored by `schemas/runtime/runtime_config_v1.schema.json`. Every persisted runtime config snapshot carries `runtime_config_contract.digest` and `runtime_config_contract.schema_version`; release ledgers must preserve those fields without rewriting them.


`strict_runtime_freeze_gate` is operator-configurable as `off`, `warn`, or `enforce`. `off` records freeze facts without blocking runtime transitions, `warn` emits gate warnings while allowing execution, and `enforce` blocks lock/start/runtime transitions on freeze drift or missing live-controller evidence.


## P2 acceptance gate usage
- `scripts/check_p2_acceptance.py` must be pointed at the audited build output with `P2_ACCEPTANCE_OUTPUT_ROOT`.
- Default behavior is fail-closed when `.artifacts/p2_acceptance_static` is absent.
- `P2_ACCEPTANCE_ALLOW_GENERATE=1` is only for explicit self-generated review runs and must not be reported as audited build proof.
