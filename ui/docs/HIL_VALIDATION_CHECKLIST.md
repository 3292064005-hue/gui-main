# HIL Validation Checklist — xMateRobot-only Mainline

This checklist closes the remaining non-sandboxable risk items for the RT phase-controller upgrade.

## Preconditions
- Ubuntu host on the same wired-direct subnet as the controller
- `remote_ip` and `local_ip` match the deployed xMateRobot profile
- RobotAssist is not acting as a competing control source
- Controller firmware is xCore v2.1+
- Operator has manual/automatic mode transition authority

## Required evidence
1. `connect_robot` succeeds with `live_binding_established=true`
2. `query_sdk_runtime_config` reports:
   - `robot_model = xmate3`
   - `sdk_robot_class = xMateRobot`
   - `axis_count = 6`
3. `query_runtime_alignment` reports:
   - `control_source_exclusive = true`
   - `preferred_link = wired_direct`
4. NRT smoke:
   - `go_home` completes without error
   - `safe_retreat` completes without error
5. RT smoke:
   - `seek_contact` enters `seek_contact` phase and reaches `contact_hold`
   - `start_scan` enters `scan_follow` phase and maintains force within tolerance
   - `pause_scan` enters `pause_hold` phase without drift instability
   - `safe_retreat` or `controlled_retract` exits RT cleanly
6. Telemetry:
   - RT state stream starts successfully
   - no controller-side network instability fault under nominal conditions
   - stale-state protection trips cleanly when telemetry is intentionally withheld
7. Cleanup:
   - `stopLoop`, `stopMove`, and `stopReceiveRobotState` leave the controller in a recoverable state

## Phase-specific measurements
### seek_contact
- contact establish time
- peak force overshoot
- maximum seek travel

### scan_follow
- normal-force RMS error
- tangent-speed RMS
- lateral-modulation on/off comparison
- contact-quality downgrade behavior

### pause_hold
- 30 s / 60 s drift magnitude
- disturbance recovery time

### controlled_retract
- release detection time
- total retract completion time
- timeout/fault behavior when release does not happen

## Recommended sequence
1. `scripts/run_hil_readiness.sh <remote_ip> <local_ip>`
2. Start the desktop backend / `spine_robot_core`
3. Execute protocol-bridge smoke test against the live runtime
4. Run one NRT-only sequence
5. Run one RT-only sequence with low gains and low speeds
6. Record logs and controller diagnostics
7. Repeat RT sequence with nominal gains after low-gain validation passes

## Acceptance bar
The HIL item is closed only when all required evidence above is captured from the real controller and archived with the deployment record.


## Captured evidence files
- `runtime_config.json` — captured from `get_sdk_runtime_config`
- `rt_phase_metrics.json` — measured HIL phase metrics with keys `seek_contact`, `scan_follow`, `pause_hold`, `controlled_retract`

## Automated evidence gate
After collecting controller evidence, run:

```bash
python scripts/validate_hil_phase_metrics.py --runtime-config runtime_config.json --evidence rt_phase_metrics.json
```

The gate fails if measured values exceed the active RT phase contract published by the runtime.


## Bundle packaging
After collecting `runtime_config.json` and `rt_phase_metrics.json`, package the archived controller evidence with:

```bash
python scripts/package_live_evidence_bundle.py \
  --runtime-config runtime_config.json \
  --phase-metrics rt_phase_metrics.json \
  --readiness-manifest runtime_readiness_manifest.json \
  --output live_evidence_bundle.zip
```

Only the archived `.zip` bundle may be passed to `scripts/write_verification_report.py --live-evidence-bundle ...`. The bundle itself must contain `runtime_config.json`, `rt_phase_metrics.json`, and `runtime_readiness_manifest.json`. A directory path, a missing bundle, or an external readiness manifest is not valid proof.
