# Safety Recovery Policy

## Policy layers

- `L0_hard_block`
- `L1_runtime_guard`
- `L2_auto_recovery`
- `L3_evidence_ack`

## Supported actions

- `pause_hold`
- `controlled_retract`
- `retry_wait_stable`
- `retry_ready`
- `estop_latched`

## Required evidence

Every safety-triggered action must record:

- trigger source
- active phase
- action taken
- operator acknowledgement requirement
