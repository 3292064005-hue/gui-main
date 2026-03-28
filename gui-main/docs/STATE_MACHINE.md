# Workflow State Machine

## Top-level states
- BOOT
- DISCONNECTED
- CONNECTED
- POWERED
- AUTO_READY
- SESSION_LOCKED
- PATH_VALIDATED
- APPROACHING
- CONTACT_SEEKING
- SCANNING
- PAUSED_HOLD
- RETREATING
- SCAN_COMPLETE
- FAULT
- ESTOP

## Hard guards
- Robot must be connected before powering on.
- Power and automatic mode must be ready before session lock.
- UI workflow must finish `create_experiment -> localization -> preview plan` before `lock_session`.
- Session must be locked before scan plan load.
- Path must exist before pre-scan approach and scan start.
- Contact must be established before segmented scan.
- Critical RT parameters are locked during an active session.
- Recoverable faults enter hold/retract flow before resume.
- ESTOP requires reinitialization.
