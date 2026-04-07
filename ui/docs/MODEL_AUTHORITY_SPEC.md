# Model Authority Spec

## Goal

Freeze the authoritative model/planner hierarchy for compile-time and runtime motion decisions.

## Authority order

1. `cpp_robot_core` runtime verdict
2. vendored xCore SDK and xMateModel bindings
3. frozen family descriptor matrix
4. Python advisory fallbacks

## Required methods

- `robot.model()`
- `getCartPose`
- `getJointPos`
- `jacobian`
- `getTorque`

## Planner primitives

- `JointMotionGenerator`
- `CartMotionGenerator`
- `FollowPosition`
