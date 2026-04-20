---
category: index
authority: canonical
audience: all
owner: repository
status: active
last_verified_against: delivery_round6_docs_final_audit_closure
---

# Start Here

This repository uses a layered documentation system. Read by role from this page instead of scanning `docs/` alphabetically.

## Reading paths

### If you are new to the repository
1. [`01_overview/SYSTEM_OVERVIEW.md`](./01_overview/SYSTEM_OVERVIEW.md)
2. [`01_overview/MAINLINE_OPERATION_FLOW.md`](./01_overview/MAINLINE_OPERATION_FLOW.md)
3. [`02_governance/CONTROL_AUTHORITY_AND_BOUNDARIES.md`](./02_governance/CONTROL_AUTHORITY_AND_BOUNDARIES.md)

### If you are changing runtime or robot execution code
1. [`03_runtime/RUNTIME_KERNEL.md`](./03_runtime/RUNTIME_KERNEL.md)
2. [`03_runtime/PLAN_VALIDATION_AND_EXECUTION.md`](./03_runtime/PLAN_VALIDATION_AND_EXECUTION.md)
3. [`03_runtime/XCORE_SDK_INTEGRATION_GUIDE.md`](./03_runtime/XCORE_SDK_INTEGRATION_GUIDE.md)

### If you are validating release readiness
1. [`04_profiles_and_release/PROFILE_MATRIX.md`](./04_profiles_and_release/PROFILE_MATRIX.md)
2. [`04_profiles_and_release/RELEASE_READINESS.md`](./04_profiles_and_release/RELEASE_READINESS.md)
3. [`04_profiles_and_release/RELEASE_LEDGER.md`](./04_profiles_and_release/RELEASE_LEDGER.md)
4. [`05_verification/VERIFICATION_POLICY.md`](./05_verification/VERIFICATION_POLICY.md)
5. [`05_verification/CURRENT_KNOWN_GAPS.md`](./05_verification/CURRENT_KNOWN_GAPS.md)

### If you are operating the system or reviewing evidence
1. [`06_operations/OPERATIONS_AND_RECOVERY.md`](./06_operations/OPERATIONS_AND_RECOVERY.md)
2. [`06_operations/EVIDENCE_AND_REPLAY.md`](./06_operations/EVIDENCE_AND_REPLAY.md)
3. [`06_operations/RECORDING_EVENT_CONSUMPTION_MAP.md`](./06_operations/RECORDING_EVENT_CONSUMPTION_MAP.md)

### If you are maintaining repository structure and gates
1. [`07_repo_governance/REPOSITORY_GOVERNANCE.md`](./07_repo_governance/REPOSITORY_GOVERNANCE.md)
2. [`07_repo_governance/CANONICAL_MODULES_AND_DEPENDENCIES.md`](./07_repo_governance/CANONICAL_MODULES_AND_DEPENDENCIES.md)

## Documentation rules
- Canonical documents are the only source of truth for current behavior.
- Redirect stubs are not kept in the active tree.
- Historical phase, superseded, and audit material is preserved as a packaged archive under [`90_archive/README.md`](./90_archive/README.md).
- Known open gaps must be tracked in [`05_verification/CURRENT_KNOWN_GAPS.md`](./05_verification/CURRENT_KNOWN_GAPS.md).

## Operational notes
- `scripts/start_mainline.py` is the single launcher contract for desktop/headless bringup.
- `spine_ultrasound_ui.core` and `spine_ultrasound_ui.utils` keep GUI-heavy exports lazy so repository scripts and headless services do not require PySide6 at import time.
- xMateModel compile proof is profile-aware: mock builds do not claim the gate, while SDK/model-enabled profiles must compile `test_xmate_model_compile_contract`.
- `scripts/final_acceptance_audit.sh` emits `release_ledger.json` so release consumers can inspect one claim-safe proof index instead of stitching together multiple JSON reports by hand.
