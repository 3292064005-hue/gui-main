---
category: overview
authority: canonical
audience: developers, reviewers, operators
owner: repository
status: active
---

# Mainline Operation Flow

## Control flow
1. Runtime/profile selection and doctor checks
2. Device readiness and governance checks
3. Guidance and planning preparation
4. Session lock and artifact freeze
5. Plan load into C++ runtime
6. Procedure start (`start_procedure(scan)`) and runtime-owned phase transitions
7. RT/NRT execution and telemetry projection
8. Postprocess, evidence export, replay indexing, report generation

## Ownership model
- UI may request actions.
- Python workflow may prepare and validate.
- `cpp_robot_core` owns the procedure execution graph and motion authority.
- Evidence and report layers consume runtime truth after execution.

## Key transitions
- Planning is advisory until session freeze.
- After freeze, plan/runtime/session digest become immutable execution inputs.
- Desktop/UI start-scan affordances now route through canonical `start_procedure(scan)` at the controller boundary.
- `start_scan` is retired from the active runtime command surface; migration diagnostics live in `schemas/runtime_command_compat_manifest.json`.
