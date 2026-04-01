# Rewrite v5 summary

This wave pushes the runtime one layer closer to final operational closure:

- Added **deployment contract** as a first-class runtime asset, exposing vendored SDK expectations, bringup sequence, required host dependencies, TLS/runtime material expectations, and systemd unit names.
- Added **fault injection contract** as a first-class runtime asset, with a stable catalog for:
  - `pressure_stale`
  - `rt_jitter_high`
  - `overpressure`
  - `collision_event`
  - `plan_hash_mismatch`
  - `estop_latch`
- Added runtime commands for:
  - `get_deployment_contract`
  - `get_fault_injection_contract`
  - `inject_fault`
  - `clear_injected_faults`
- Extended the SDK runtime asset aggregator so the UI / monitor / report side can consume deployment and fault-injection contracts from the same source as the existing identity / capability / release contracts.
- Added regression coverage for protocol exposure, contract aggregation, and fault injection roundtrip behavior.

This closes an important planning gap from v4: runtime contracts are no longer limited to identity / capability / release; they now also cover **bringup readiness** and **deterministic fault-injection surfaces** for integration and HIL preparation.
