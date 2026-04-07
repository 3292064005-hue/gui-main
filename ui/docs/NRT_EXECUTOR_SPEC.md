# NRT Executor Spec

## Scope

This document freezes the non-real-time executor contract.

## Profiles

- `go_home`
- `approach_prescan`
- `align_to_entry`
- `safe_retreat`
- `recovery_retreat`
- `post_scan_home`

## Rules

- `moveReset()` is mandatory before batch execution
- a single control source is mandatory
- profile preconditions must be explicit and auditable
- completion, abort, and retry semantics must emit evidence events

## Execution record

Each profile execution records:

- profile name
- sdk command type
- command sequence
- result
- blocking reason, if any
