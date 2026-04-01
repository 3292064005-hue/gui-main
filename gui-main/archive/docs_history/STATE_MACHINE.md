# State Machine

## Execution states
- `BOOT`
- `DISCONNECTED`
- `CONNECTED`
- `POWERED`
- `AUTO_READY`
- `SESSION_LOCKED`
- `PATH_VALIDATED`
- `APPROACHING`
- `CONTACT_SEEKING`
- `SCANNING`
- `PAUSED_HOLD`
- `RETREATING`
- `SCAN_COMPLETE`
- `FAULT`
- `ESTOP`

## Recovery view exposed to product shell
- `IDLE`
- `HOLDING`
- `CONTROLLED_RETRACT`
- `RETRY_READY`
- `ESTOP_LATCHED`

## Workflow invariants
- session locking freezes manifest semantics
- preview-plan hash may not change after lock
- command journal is append-only
- report/replay/quality/alarm/qa products are generated from the session record, not from UI-only state
