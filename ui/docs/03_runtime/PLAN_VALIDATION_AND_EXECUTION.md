---
category: spec
authority: canonical
audience: runtime developers, auditors, validation engineers
owner: cpp_robot_core
status: active
---

# Plan Validation and Execution

## Purpose
Describe how plans move from advisory data into executable runtime state, and how plan validity is judged.

## Canonical runtime plan model
- Planning outputs are frozen into a canonical execution-plan runtime representation.
- Runtime progress is tracked against segments and waypoints, not synthetic frame counters alone.
- Validation must distinguish schema correctness from executable feasibility.

## Validation layers
1. `schema_valid`
2. `kinematic_valid`
3. `runtime_feasible`
4. `profile_compatible`

## Authoritative precheck
Authoritative precheck is the highest validation tier and must use robot-model capabilities when available.
Current integration path requires the runtime to call authoritative kinematic validation during:
- plan load / freeze-time runtime compilation
- verdict compilation prior to execution

## Current status rule
A plan may be structurally and operationally acceptable without yet being considered fully authoritative if live SDK/model proof has not been closed in the target environment.
