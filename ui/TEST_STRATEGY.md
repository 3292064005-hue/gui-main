# TEST_STRATEGY

Stable target surfaces:
- API/runtime verdict authority and command guards
- Control plane and control ownership
- Headless runtime and session products
- Release-state governance and freeze contracts
- Repository/architecture gates
- Mainline mock end-to-end workflow
- Preweight measured-only semantic closure
- Deployment profile boundary behavior

Execution:
```bash
python scripts/run_pytest_mainline.py -q
```

Archived compatibility coverage is opt-in only:
```bash
python scripts/run_pytest_mainline.py -q --include-archive-compat
```

For deployment/profile smoke:
```bash
python scripts/deployment_smoke_test.py
```

Preweight semantic closure gate:
```bash
python scripts/run_pytest_mainline.py -q tests/test_preweight_semantic_closure.py
```

This gate verifies that `preweight_deterministic` closes authoritatively when measured evidence is present and fail-closes when the measured chain is missing.

## Active gate vs archive coverage

- The active mainline gate is defined by `python scripts/run_pytest_mainline.py -q` together with `scripts/verify_mainline.sh` / `scripts/final_acceptance_audit.sh`.
- Historical compatibility suites live under `tests/archive/` only and are excluded from the default mainline run.
- Top-level `tests/test_*.py` files must belong to the current mainline surface; archive wrappers are not allowed there.
- Runtime command protocol drift is guarded by `schemas/runtime_command_manifest.json`, `spine_ultrasound_ui/services/runtime_command_catalog.py`, `cpp_robot_core/include/robot_core/generated_command_manifest.inc`, and `python scripts/check_protocol_sync.py`.


## Layered execution

Use the layered markers to narrow failures to a specific surface:

```bash
python scripts/run_pytest_mainline.py -q --report-layers
python scripts/run_pytest_mainline.py -q --layer unit
python scripts/run_pytest_mainline.py -q --layer contract
python scripts/run_pytest_mainline.py -q --layer runtime_core
python scripts/run_pytest_mainline.py -q --layer surface_integration
python scripts/run_pytest_mainline.py -q --layer mock_e2e
```

Marker assignment is centralized in `tests/conftest.py`. New tests must land in the correct layer instead of relying on ad-hoc CI job naming.
