# Bringup and fault injection

## Bringup

1. Run `scripts/doctor_runtime.py --json` to inspect blockers and warnings.
2. Run `scripts/bootstrap_hil_runtime.sh / scripts/bootstrap_prod_runtime.sh` to generate development TLS material when absent, re-run the doctor in strict mode, and then launch the vendored xCore runtime.
3. For production-like installs, use the systemd units in `configs/systemd/` and enable `spine-ultrasound.target`.

## Fault injection

The runtime now exposes a first-class fault injection contract and command surface:

- `get_fault_injection_contract`
- `inject_fault`
- `clear_injected_faults`

Supported injections:

- `pressure_stale`
- `rt_jitter_high`
- `overpressure`
- `collision_event`
- `plan_hash_mismatch`
- `estop_latch`

These injections are intended for mock/integration/HIL preparation. They let the operator, tests, and bringup scripts validate hold / retreat / estop / plan-freeze behavior without editing application code.
