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
- RT host bootstrap is explicit and authoritative: scheduler policy/priority, CPU affinity, and memory lock requirements must be applied before the runtime loop starts.
- RT purity must be preserved: no UI-, report-, or file-side work inside the RT loop.
- RT timing and live-binding state must be exported separately from nominal declarations.

## NRT execution
NRT motions must be sourced from session-frozen execution targets only.
Missing or incomplete frozen targets are runtime-owned hard failures.
Configuration-defined fallback targets and built-in emergency profiles are not authoritative write sources and must not be used to drive recovery motion.

## Control-plane authority envelope
- `authoritative_runtime_envelope` is the canonical additive contract for runtime-owned truth.
- `control_authority` inside that envelope is published from runtime-owned lease state, not from Python-side cache synthesis.
- Python backends may normalize and project that envelope, but external HTTP API/review clients are read-only: they may query authority/evidence/state yet must not initiate lease mutation, runtime-config writes, or runtime write commands. Desktop remains the only real operator console.
- Advisory prechecks never become final runtime verdicts.

## Runtime-owned sequence constraints
- Runtime phase sequencing covers preconditions, approach, contact acquisition, plan-driven scan execution, pause/resume, retreat, and abort.
- Safe retreat and abort remain runtime actions with evidence, not UI-side retries.
- `stop_scan` is an orderly scan-stop request and is not equivalent to `safe_retreat`: when issued from `SCANNING` or `PAUSED_HOLD`, post-scan home may close to `SCAN_COMPLETE`; when issued before scan execution actually begins, runtime must retreat/home without advertising `SCAN_COMPLETE`.
- `start_procedure(scan)` failure inside the runtime-owned phase graph must surface as runtime recovery telemetry/alarm evidence; desktop may observe and project that state, but must not emit a second compensating `safe_retreat` write.
- RT work must stay isolated from UI/report/file activity to preserve controller timing guarantees.
