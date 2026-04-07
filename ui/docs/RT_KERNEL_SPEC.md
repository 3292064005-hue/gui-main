# RT Kernel Spec

## Scope

This document freezes the mainline real-time kernel contract used by `cpp_robot_core`.

## Invariants

- Fixed nominal period target: 1 ms / 1 kHz
- Scheduler implementation uses absolute-deadline wakeups; measured wake jitter / execution time / overrun are exported in the runtime contract
- Single authoritative write source
- Outer execution lanes are split into `command`, `query`, and `rt_control` dispatch paths so query traffic does not share the same outer mutex with mutating commands or RT maintenance loops
- Runtime commands `seek_contact`, `start_scan`, `pause_scan`, `resume_scan`, and `safe_retreat` are explicitly routed through the `rt_control` lane rather than the generic command lane
- No blocking I/O, dynamic allocation, JSON formatting, or UI callbacks inside the measured RT loop
- All runtime phases and guards are evaluated inside the C++ kernel only

## Phases

- `idle`
- `seek_contact`
- `contact_stabilize`
- `scan_follow`
- `pause_hold`
- `controlled_retract`
- `fault_latched`

## Read / Update / Write stages

1. Read state
2. Update phase policy
3. Write command

## Monitors

- reference limiter
- freshness guard
- jitter monitor
- force-band monitor
- network guard
- workspace margin
- singularity margin

## Failure semantics

- recoverable faults route to `pause_hold` or `controlled_retract`
- fatal faults route to `fault_latched`
