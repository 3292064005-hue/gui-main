# RT Phase Control Contract — xMateRobot-only Mainline

This document defines the feedback-controller contract for the RT mainline.

## Common limits
- `rt_stale_state_timeout_ms`
- `rt_phase_transition_debounce_cycles`
- `rt_max_cart_step_mm`
- `rt_max_cart_vel_mm_s`
- `rt_max_cart_acc_mm_s2`
- `rt_max_pose_trim_deg`
- `rt_max_force_error_n`
- `rt_integrator_limit_n`

## seek_contact
- target: `contact_force_target_n`
- tolerance: `contact_force_tolerance_n`
- controller: `contact_control` (primary nested contract) with legacy projection fields `normal_admittance_gain`, `normal_damping_gain` retained for compatibility
- convergence: `contact_establish_cycles`, `normal_velocity_quiet_threshold_mm_s`
- safety: `seek_contact_max_step_mm`, `seek_contact_max_travel_mm`

## scan_follow
- target: `scan_force_target_n`
- tolerance: `scan_force_tolerance_n`
- controller: `scan_follow_admittance` (derived from `contact_control`)
- tangent feed: `scan_tangent_speed_min_mm_s` ~ `scan_tangent_speed_max_mm_s` via `TangentialScanController`
- trim: `orientation_trim` (primary nested contract) with legacy `scan_pose_trim_gain` retained for compatibility
- optional modulation: `scan_follow_enable_lateral_modulation`, `scan_follow_lateral_amplitude_mm`, `scan_follow_frequency_hz`

## pause_hold
- guards: `pause_hold_position_guard_mm`, `pause_hold_force_guard_n`
- controller: `pause_hold_admittance` (derived from `contact_control`) with legacy `pause_hold_drift_*` retained as compatibility projection
- anti-windup: `pause_hold_integrator_leak`

## controlled_retract
- release detection: `retract_release_force_n`, `retract_release_cycles`
- retreat geometry: `retract_safe_gap_mm`, `retract_max_travel_mm`, `retract_travel_mm`
- timing: `retract_timeout_ms`
- smoothness: `retract_jerk_limit_mm_s3`


## Contact-control mainline

The clinical real-time mainline keeps `cartesianImpedance` as the xCore execution mode while the project computes a **project-side normal-axis admittance outer loop**. The outer loop uses a fused `NormalForceEstimator` (pressure + wrench), a `NormalAxisAdmittanceController` for the surface-normal axis, a `TangentialScanController` for along-spine travel, and an `OrientationTrimController` for bounded probe attitude compensation. Camera guidance does not participate in the admittance loop.


## Compatibility notes
- `contact_control`, `force_estimator`, and `orientation_trim` are now the primary configuration surfaces.
- Legacy flat RT fields are still emitted and parsed as compatibility projections.
- `cpp_robot_core/examples/impedance_scan_example.cpp` is now a controller-composition demo, not an alternative production control law.
