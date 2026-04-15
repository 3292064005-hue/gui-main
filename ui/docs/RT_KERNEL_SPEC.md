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
- Alarm events are handed off to the asynchronous recorder queue under `state_mutex_`; JSON serialization and file append happen only on the recorder worker thread
- All runtime phases and guards are evaluated inside the C++ kernel only

- Static RT purity gate must fail when the RT path loses the recorded jitter/overrun evidence (`overrun_count`, `last_wake_jitter_ms`, `jitter_budget_ms`, `current_period_ms`) or when the command server stops publishing measured RT loop samples into the runtime state.
- Runtime-state gating must keep `rt_jitter_ok_` tied to both the measured sample (`recordRtLoopSample`) and the exported contract fields so release gates can reject drift between measured RT quality and governance reporting.
- The runtime doctor must block mainline execution when `overrun_count > 0`, when `last_wake_jitter_ms > jitter_budget_ms`, when `max_cycle_ms > current_period_ms + jitter_budget_ms`, or when the exported `rt_quality_gate_passed` flag is false.

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

- `scripts/check_rt_quality_gate.py` now exercises the runtime-doctor behaviour directly: a healthy RT contract must produce no `rt_kernel` blockers, while synthetic overrun / wake-jitter / cycle-budget / exported-gate failures must each produce the corresponding blocking reason. The gate also loads the committed RT-quality baseline fixture under `artifacts/verification/current_delivery_fix/rt_quality_baseline.json` and the scenario fixture under `artifacts/verification/current_delivery_fix/rt_quality_gate_scenarios.json`, then validates the runtime-doctor blocker behaviour against both the healthy baseline contract and the failure scenarios. This keeps the gate from regressing into a token-only presence check.

- Mainline RT quality gating now requires a committed observed-evidence fixture (`artifacts/verification/current_delivery_fix/rt_quality_observed.json
- `check_rt_quality_gate.py` 现在会同时校验 committed baseline、committed observed evidence，以及 overrun / wake jitter / cycle budget / exported gate 四类 failure scenarios。
- observed evidence 必须导出 `sample_count` 与 `loop_samples`，并验证样本级 `execution_ms / wake_jitter_ms / overrun` 保持在当前导出的周期 / jitter budget 内。
`) containing healthy `loop_samples` that stay within the exported jitter/cycle budget in addition to the baseline/scenario fixtures.

- `rt_phase_runtime_config.json` and `rt_phase_metrics_evidence.json` are committed delivery fixtures validated by `check_rt_quality_gate.py` via `validate_hil_phase_metrics.py`; they must remain within the exported RT phase contract budgets.
