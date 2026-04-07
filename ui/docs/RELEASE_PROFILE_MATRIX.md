# Release Profile Matrix

## Profiles

- `dev`
- `lab`
- `research`
- `clinical`
- `review`

## Frozen constraints

- `clinical` requires HIL gate and release-ready evidence
- `review` is read-only and must not allow write commands
- `lab` may use LabRobotPort

## Binding truth

- `dev` may run with the contract shell only.
- `lab` may use `LabRobotPort`, but must still report whether live SDK binding is established.
- `research` / `clinical` must not treat vendored SDK detection as equivalent to live takeover readiness.
- `review` remains read-only regardless of SDK availability.
