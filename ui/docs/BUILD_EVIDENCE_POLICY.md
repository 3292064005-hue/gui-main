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


## Phase-aware execution

When `verify_mainline.sh` is used for repository proof, prefer explicit phase runs when a long container session is unstable:

```bash
VERIFY_PHASE=python ./scripts/verify_mainline.sh
VERIFY_PHASE=mock ./scripts/verify_mainline.sh
VERIFY_PHASE=hil BUILD_EVIDENCE_REPORT=build_evidence.json ./scripts/verify_mainline.sh
VERIFY_PHASE=prod ROBOT_CORE_WITH_XCORE_SDK=OFF ROBOT_CORE_WITH_XMATE_MODEL=OFF ./scripts/verify_mainline.sh
```

Each phase configures an isolated build directory under the temporary build root and prints the registered `ctest` inventory before executing the suite. `VERIFY_PHASE=python` additionally executes the default mainline pytest selection in deterministic batches so repository-proof runs are less likely to be cut off by constrained sandbox execution windows. That output is part of the evidence chain and must be preserved with the logs.
