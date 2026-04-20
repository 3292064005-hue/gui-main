---
category: spec
authority: canonical
audience: runtime developers, reviewers
owner: cpp_robot_core
status: active
---

# Runtime Kernel

## Scope
Defines runtime-owned execution behavior across NRT and RT paths.

## Core principles
- Runtime procedure ownership lives in `cpp_robot_core`.
- Python initiates procedures but does not own phase sequencing.
- RT and NRT paths must consume the same frozen session/config/plan inputs.

## Procedure model
Canonical execution entry is `start_procedure(scan)`.
Runtime-owned sequence includes:
1. preconditions and lock assertions
2. approach / entry handling
3. contact acquisition
4. plan-driven scan execution
5. pause / resume / retreat / abort transitions

## RT constraints
- RT control assumes a controller-side 1 ms cycle and a client-side 1 kHz send discipline.
- RT purity must be preserved: no UI-, report-, or file-side work inside the RT loop.
- RT timing and live-binding state must be exported separately from nominal declarations.

## NRT execution
NRT motions must be sourced from:
1. session-frozen targets
2. configuration-defined fallback targets
3. built-in emergency fallback as a final guard only

## Control-plane authority envelope
- `authoritative_runtime_envelope` is the canonical additive contract for runtime-owned truth.
- `control_authority` inside that envelope is published from runtime-owned lease state, not from Python-side cache synthesis.
- Python backends may normalize and project that envelope, and may forward canonical lease commands with `_command_context`; API bridge now proxies acquire/renew/release lease lifecycle explicitly, but those clients may not fabricate a parallel control-authority snapshot or final write-command verdict.
- Advisory prechecks never become final runtime verdicts.

## Runtime-owned sequence constraints
- Runtime phase sequencing covers preconditions, approach, contact acquisition, plan-driven scan execution, pause/resume, retreat, and abort.
- Safe retreat and abort remain runtime actions with evidence, not UI-side retries.
- RT work must stay isolated from UI/report/file activity to preserve controller timing guarantees.
