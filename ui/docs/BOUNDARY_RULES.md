# BOUNDARY_RULES

## Control Kernel

Owns vendor binding, NRT execution, RT execution, safety/recovery, authoritative telemetry, and final runtime verdicts.

### May do
- connect/disconnect hardware
- own motion authority
- read/update/write RT loop stages
- publish authoritative execution state

### Must not do
- expose mock-only semantics as live truth
- let UI/web/ROS2 bypass control ownership

## Governance Shell

Owns configuration governance, session governance, evidence, replay, operator-facing summaries, and release/deployment gates.

### May do
- inspect runtime contracts
- summarize readiness
- block unsafe requests before they reach the core
- seal/export evidence

### Must not do
- become a second control loop
- create a second final verdict
- write robot commands directly

## Integration Perimeter

Owns optional adapters only.

### May do
- mirror telemetry
- expose reviewed commands
- host replay/review workflows

### Must not do
- take hardware ownership
- replace runtime safety semantics


- Governance shell may summarize, but must not synthesize final verdict.
