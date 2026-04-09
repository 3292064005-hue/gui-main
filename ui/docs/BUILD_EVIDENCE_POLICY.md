# C++ Build Evidence Policy

The sandbox used for repository review may interrupt long-running target links before a final success line is emitted.
That environment behavior must not be misreported as a compiler or linker failure.

## Primary evidence path
1. Configure `cpp_robot_core` with `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON`
2. Build the key targets:
   - `spine_robot_core_runtime`
   - `spine_robot_core`
   - `test_protocol_bridge`
   - `test_rt_motion_service_truth`
   - `test_recovery_manager`
3. Archive the build log and the generated report from:

```bash
python scripts/verify_cpp_build_evidence.py --profile hil --report build_evidence.json
```

## Fallback evidence path
If the sandbox interrupts the long link stage, the evidence report is still allowed to close the code-review gate when both of the following are true:

- CMake configure succeeds and a `compile_commands.json` file is generated
- `verify_cpp_build_evidence.py` reports `syntax_only_results` of `ok` for the critical changed sources

The fallback path is a validation-environment boundary, not a code-quality waiver.
The generated `build_evidence_report.json` now records `evidence_mode`, `target_build_complete`, `syntax_only_fallback_ok`, and `target_timeout_sec` so repository proof cannot overstate a timed-out target build as a full compile pass.


## Phase-aware execution

When `verify_mainline.sh` is used for repository proof, prefer explicit phase runs when a long container session is unstable:

```bash
VERIFY_PHASE=python ./scripts/verify_mainline.sh
VERIFY_PHASE=mock ./scripts/verify_mainline.sh
VERIFY_PHASE=hil BUILD_EVIDENCE_REPORT=build_evidence.json ./scripts/verify_mainline.sh
VERIFY_PHASE=prod ROBOT_CORE_WITH_XCORE_SDK=OFF ROBOT_CORE_WITH_XMATE_MODEL=OFF ./scripts/verify_mainline.sh
```

Each phase configures an isolated build directory under the temporary build root and prints the registered `ctest` inventory before executing the suite. `VERIFY_PHASE=python` additionally executes the default mainline pytest selection in deterministic batches so repository-proof runs are less likely to be cut off by constrained sandbox execution windows. That output is part of the evidence chain and must be preserved with the logs.

`VERIFY_PHASE=prod` now builds the declared C++ target set, runs the registered `ctest` inventory, performs an isolated install into a temporary `DESTDIR`, and executes `scripts/deployment_smoke_test.py` under the clinical deployment profile. It is still **not** live-controller proof unless SDK/model bindings and robot-side validation are supplied.


## Environment readiness manifest

The runtime doctor now emits an explicit readiness manifest that separates static/sandbox readiness from real live-runtime verification. `scripts/doctor_runtime.py --manifest-only --write-manifest <path>` must not be interpreted as proof that HIL or robot-side validation has already passed. When a live evidence bundle is used, the readiness manifest must be archived inside that `.zip` bundle; `scripts/write_verification_report.py --live-evidence-bundle ...` must not accept an external readiness file.

## Claim-safe execution report

Every repository/profile proof run should archive a verification execution report:

```bash
python scripts/write_verification_report.py \
  --phase python --phase prod \
  --output verification_execution_report.json \
  --write-readiness-manifest runtime_readiness_manifest.json
```

The execution report is the machine-readable source of truth for:

- which phases actually ran,
- whether the run was only **已静态确认 / 已沙箱验证**,
- whether **未真实环境验证** still applies,
- whether a live-controller evidence bundle was explicitly supplied.

Do not summarize a run beyond what the execution report states.


## Frozen robot identity drift gate
Every repository/profile proof run must also execute `scripts/check_robot_identity_registry.py` so the xMate3/xMateRobot/6-axis frozen mainline facts cannot silently drift across Python, C++, and docs.


## Acceptance summary output

`final_acceptance_audit.sh` now writes `acceptance_summary.json` alongside `verification_execution_report.json` and `build_evidence_report.json` so the full-profile acceptance run leaves a machine-readable summary of the build/test/install evidence paths.
The acceptance summary now also mirrors the verification boundary, reported evidence tiers, and build-evidence mode so package consumers can inspect the claim boundary without resolving every linked JSON file first.


## Path portability

Machine-readable proof files archived inside a delivery package must record package-contained references as relative paths anchored to the proof file directory. Absolute host paths are only allowed for host-only tooling facts (for example `/usr/bin/cmake`) and must not be used for packaged evidence members or repository assets.
