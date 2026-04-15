#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.models import RuntimeConfig, SystemState
from spine_ultrasound_ui.services.mainline_runtime_doctor_service import MainlineRuntimeDoctorService
from spine_ultrasound_ui.services.mock_core_runtime import MockCoreRuntime
from scripts.validate_hil_phase_metrics import validate_metrics

DOCTOR = ROOT / 'spine_ultrasound_ui' / 'services' / 'mainline_runtime_doctor_service.py'
SCENARIOS_PATH = ROOT / 'artifacts' / 'verification' / 'current_delivery_fix' / 'rt_quality_gate_scenarios.json'
BASELINE_PATH = ROOT / 'artifacts' / 'verification' / 'current_delivery_fix' / 'rt_quality_baseline.json'
OBSERVED_PATH = ROOT / 'artifacts' / 'verification' / 'current_delivery_fix' / 'rt_quality_observed.json'
PHASE_RUNTIME_CONFIG_PATH = ROOT / 'artifacts' / 'verification' / 'current_delivery_fix' / 'rt_phase_runtime_config.json'
PHASE_METRICS_PATH = ROOT / 'artifacts' / 'verification' / 'current_delivery_fix' / 'rt_phase_metrics_evidence.json'

REQUIRED_TOKENS = {
    'rt_cycle_overrun_detected': 'Runtime doctor must block when RT overrun_count > 0',
    'rt_wake_jitter_budget_exceeded': 'Runtime doctor must block when wake jitter exceeds jitter_budget_ms',
    'rt_cycle_budget_exceeded': 'Runtime doctor must block when max_cycle_ms exceeds the cycle budget',
    'rt_quality_gate_failed': 'Runtime doctor must block when the exported RT quality gate fails',
    'current_period_ms': 'Runtime doctor must consume current_period_ms when computing RT cycle budgets',
    'jitter_budget_ms': 'Runtime doctor must consume jitter_budget_ms when computing RT cycle budgets',
    'last_wake_jitter_ms': 'Runtime doctor must consume last_wake_jitter_ms when computing RT jitter budgets',
    'rt_quality_gate_passed': 'Runtime doctor must consume the exported rt_quality_gate_passed signal',
}


def _mock_runtime_baseline() -> tuple[RuntimeConfig, dict, dict, dict, dict]:
    runtime = MockCoreRuntime()
    runtime.controller_online = True
    runtime.powered = True
    runtime.operate_mode = "automatic"
    runtime.execution_state = SystemState.AUTO_READY
    runtime.pressure_fresh = True
    runtime.robot_state_fresh = True
    runtime.tool_ready = True
    runtime.tcp_ready = True
    runtime.load_ready = True
    config = runtime.config

    def query(command: str) -> dict:
        envelope = runtime.handle_command(command)
        assert envelope.ok, f"mock runtime baseline query failed: {command}"
        return dict(envelope.data or {})

    sdk_runtime = {
        'control_governance_contract': query('get_control_governance_contract'),
        'runtime_alignment': query('get_runtime_alignment'),
        'clinical_mainline_contract': query('get_clinical_mainline_contract'),
        'capability_contract': query('get_capability_contract'),
        'robot_family_contract': query('get_robot_family_contract'),
        'vendor_boundary_contract': query('get_vendor_boundary_contract'),
        'profile_matrix_contract': runtime.deployment_profiles.build_snapshot(runtime.config),
        'model_authority_contract': query('get_model_authority_contract'),
        'motion_contract': query('get_motion_contract'),
        'session_freeze': query('get_session_freeze'),
        'session_drift_contract': query('get_session_drift_contract'),
        'hardware_lifecycle_contract': query('get_hardware_lifecycle_contract'),
        'rt_kernel_contract': query('get_rt_kernel_contract'),
        'release_contract': query('get_release_contract'),
        'deployment_contract': query('get_deployment_contract'),
        'environment_doctor': {'summary_state': 'ready'},
        'controller_evidence': query('get_controller_evidence'),
        'safety_recovery_contract': query('get_safety_recovery_contract'),
        'dual_state_machine_contract': query('get_dual_state_machine_contract'),
        'mainline_executor_contract': query('get_mainline_executor_contract'),
        'mainline_task_tree': query('get_mainline_task_tree'),
    }
    backend_link = {
        'control_authority': {'summary_state': 'ready', 'detail': 'mock authority ready'},
        'control_plane': {'control_plane_snapshot': {}},
        'final_verdict': {'accepted': True, 'authoritative': True, 'reason': 'ok'},
    }
    model_report = {'verdict_kind': 'final', 'authority_source': 'cpp_robot_core'}
    session_governance = {}
    return config, sdk_runtime, backend_link, model_report, session_governance


def _rt_blocker_names(result: dict) -> set[str]:
    return {item['name'] for item in result.get('blockers', []) if item.get('section') == 'rt_kernel'}

def _baseline_contract_matches_fixture(sdk_runtime: dict) -> list[str]:
    failures: list[str] = []
    if not BASELINE_PATH.exists():
        return [f'missing RT quality baseline fixture: {BASELINE_PATH.relative_to(ROOT)}']
    expected = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
    actual = dict(sdk_runtime.get('rt_kernel_contract', {}))
    required_keys = [
        'nominal_loop_hz',
        'current_period_ms',
        'jitter_budget_ms',
        'fixed_period_enforced',
        'network_healthy',
        'monitors',
        'rt_quality_gate_passed',
    ]
    for key in required_keys:
        if actual.get(key) != expected.get(key):
            failures.append(f'baseline rt_kernel fixture drift for {key}: expected={expected.get(key)!r} actual={actual.get(key)!r}')
    return failures



def _observed_contract_matches_fixture(sdk_runtime: dict) -> list[str]:
    failures: list[str] = []
    if not OBSERVED_PATH.exists():
        return [f'missing RT quality observed fixture: {OBSERVED_PATH.relative_to(ROOT)}']
    observed = json.loads(OBSERVED_PATH.read_text(encoding='utf-8'))
    actual = dict(sdk_runtime.get('rt_kernel_contract', {}))
    required_equal = [
        'nominal_loop_hz',
        'current_period_ms',
        'jitter_budget_ms',
        'fixed_period_enforced',
        'network_healthy',
    ]
    for key in required_equal:
        if observed.get(key) != actual.get(key):
            failures.append(f'observed rt_kernel fixture drift for {key}: expected={observed.get(key)!r} actual={actual.get(key)!r}')
    loop_samples = list(observed.get('loop_samples', []) or [])
    if not loop_samples:
        failures.append('observed RT quality fixture must include loop_samples evidence')
        return failures
    current_period_ms = float(observed.get('current_period_ms', 0.0) or 0.0)
    jitter_budget_ms = float(observed.get('jitter_budget_ms', 0.0) or 0.0)
    if current_period_ms <= 0.0 or jitter_budget_ms <= 0.0:
        failures.append('observed RT quality fixture must export positive current_period_ms and jitter_budget_ms')
        return failures
    for index, sample in enumerate(loop_samples):
        if not isinstance(sample, dict):
            failures.append(f'observed RT loop sample #{index} must be an object')
            continue
        execution_ms = float(sample.get('execution_ms', sample.get('cycle_ms', 0.0)) or 0.0)
        wake_jitter_ms = abs(float(sample.get('wake_jitter_ms', 0.0) or 0.0))
        overrun = bool(sample.get('overrun', False))
        if overrun:
            failures.append(f'observed RT loop sample #{index} unexpectedly overran')
        if wake_jitter_ms > jitter_budget_ms:
            failures.append(f'observed RT loop sample #{index} exceeds jitter budget: {wake_jitter_ms:.3f} > {jitter_budget_ms:.3f}')
        if execution_ms > (current_period_ms + jitter_budget_ms):
            failures.append(f'observed RT loop sample #{index} exceeds cycle budget: {execution_ms:.3f} > {(current_period_ms + jitter_budget_ms):.3f}')
    return failures


def _live_observed_contract() -> dict:
    runtime = MockCoreRuntime()
    runtime.controller_online = True
    runtime.powered = True
    runtime.operate_mode = "automatic"
    runtime.execution_state = SystemState.AUTO_READY
    runtime.pressure_fresh = True
    runtime.robot_state_fresh = True
    runtime.tool_ready = True
    runtime.tcp_ready = True
    runtime.load_ready = True
    envelope = runtime.handle_command("get_rt_kernel_contract")
    assert envelope.ok, "mock runtime live observed query failed: get_rt_kernel_contract"
    payload = dict(envelope.data or {})
    payload.setdefault("sample_count", len(payload.get("loop_samples", []) or []))
    return payload


def _validate_observed_metadata(observed: dict) -> list[str]:
    failures: list[str] = []
    if observed.get('evidence_kind') != 'measured_runtime_observation':
        failures.append("observed RT quality fixture must declare evidence_kind='measured_runtime_observation'")
    if observed.get('capture_source') not in {'mock_core_runtime_live_export', 'command_server_rt_observed'}:
        failures.append('observed RT quality fixture must declare a committed capture_source')
    sample_count = int(observed.get('sample_count', 0) or 0)
    loop_samples = list(observed.get('loop_samples', []) or [])
    if sample_count != len(loop_samples):
        failures.append(f'observed RT quality fixture sample_count drift: expected={sample_count} actual={len(loop_samples)}')
    if observed.get('quality_verdict') != 'pass':
        failures.append("observed RT quality fixture must declare quality_verdict='pass'")
    return failures



def _validate_phase_metric_fixtures() -> list[str]:
    failures: list[str] = []
    if not PHASE_RUNTIME_CONFIG_PATH.exists():
        return [f'missing RT phase runtime fixture: {PHASE_RUNTIME_CONFIG_PATH.relative_to(ROOT)}']
    if not PHASE_METRICS_PATH.exists():
        return [f'missing RT phase metrics fixture: {PHASE_METRICS_PATH.relative_to(ROOT)}']
    runtime_cfg = json.loads(PHASE_RUNTIME_CONFIG_PATH.read_text(encoding='utf-8'))
    evidence = json.loads(PHASE_METRICS_PATH.read_text(encoding='utf-8'))
    failures.extend(validate_metrics(runtime_cfg, evidence))
    if evidence.get('evidence_kind') != 'measured_phase_metrics':
        failures.append("rt phase metrics fixture must declare evidence_kind='measured_phase_metrics'")
    if evidence.get('capture_source') not in {'mock_core_runtime_live_export', 'hil_runtime_capture', 'command_server_rt_observed'}:
        failures.append('rt phase metrics fixture must declare a committed capture_source')
    if evidence.get('quality_verdict') != 'pass':
        failures.append("rt phase metrics fixture must declare quality_verdict='pass'")
    mock_runtime = MockCoreRuntime()
    mock_runtime.controller_online = True
    mock_runtime.powered = True
    mock_runtime.operate_mode = 'automatic'
    mock_runtime.execution_state = SystemState.AUTO_READY
    mock_runtime.pressure_fresh = True
    mock_runtime.robot_state_fresh = True
    mock_runtime.tool_ready = True
    mock_runtime.tcp_ready = True
    mock_runtime.load_ready = True
    envelope = mock_runtime.handle_command('get_sdk_runtime_config')
    assert envelope.ok, 'mock runtime phase config query failed: get_sdk_runtime_config'
    live_cfg = dict(envelope.data or {})
    for key in ('robot_model', 'sdk_robot_class', 'rt_phase_contract'):
        if live_cfg.get(key) != runtime_cfg.get(key):
            failures.append(f'rt phase runtime fixture drift for {key}: expected={runtime_cfg.get(key)!r} actual={live_cfg.get(key)!r}')
    return failures

def _ensure_rt_kernel_behavior() -> list[str]:
    config, sdk_runtime, backend_link, model_report, session_governance = _mock_runtime_baseline()
    service = MainlineRuntimeDoctorService()
    failures: list[str] = []
    failures.extend(_baseline_contract_matches_fixture(sdk_runtime))
    failures.extend(_observed_contract_matches_fixture(sdk_runtime))
    observed_fixture = json.loads(OBSERVED_PATH.read_text(encoding='utf-8')) if OBSERVED_PATH.exists() else {}
    failures.extend(_validate_observed_metadata(observed_fixture))
    live_observed = _live_observed_contract()
    for key in ('nominal_loop_hz', 'current_period_ms', 'jitter_budget_ms', 'fixed_period_enforced', 'network_healthy'):
        if live_observed.get(key) != observed_fixture.get(key):
            failures.append(f'live RT observed contract drift for {key}: expected={observed_fixture.get(key)!r} actual={live_observed.get(key)!r}')
    if int(live_observed.get('sample_count', len(live_observed.get('loop_samples', []) or [])) or 0) <= 0:
        failures.append('live RT observed contract must export positive sample_count')
    if not SCENARIOS_PATH.exists():
        return [f'missing RT quality scenarios fixture: {SCENARIOS_PATH.relative_to(ROOT)}']
    scenarios_doc = json.loads(SCENARIOS_PATH.read_text(encoding='utf-8'))

    observed_runtime = dict(sdk_runtime)
    observed_runtime['rt_kernel_contract'] = json.loads(OBSERVED_PATH.read_text(encoding='utf-8'))

    base = service.inspect(
        config=config,
        sdk_runtime=observed_runtime,
        backend_link=backend_link,
        model_report=model_report,
        session_governance=session_governance,
    )
    base_rt_blockers = _rt_blocker_names(base)
    expected_baseline = set(scenarios_doc.get('baseline_expectations', {}).get('expected_blockers', []))
    if base_rt_blockers != expected_baseline:
        failures.append(f'baseline rt_kernel contract expected blockers={sorted(expected_baseline)} but got {sorted(base_rt_blockers)}')

    for scenario in scenarios_doc.get('scenarios', []):
        patch = dict(scenario.get('patch', {}))
        expected = set(scenario.get('expected_blockers', []))
        scenario_runtime = dict(sdk_runtime)
        rt_kernel = dict(sdk_runtime['rt_kernel_contract'])
        rt_kernel.update(patch)
        scenario_runtime['rt_kernel_contract'] = rt_kernel
        result = service.inspect(
            config=config,
            sdk_runtime=scenario_runtime,
            backend_link=backend_link,
            model_report=model_report,
            session_governance=session_governance,
        )
        blockers = _rt_blocker_names(result)
        missing = expected - blockers
        if missing:
            failures.append(f"{scenario.get('name', '<unnamed>')}: missing expected blockers {sorted(missing)}; got {sorted(blockers)}")
    return failures


def main() -> int:
    text = DOCTOR.read_text(encoding='utf-8')
    failures: list[str] = []
    for token, reason in REQUIRED_TOKENS.items():
        if token not in text:
            failures.append(f'{DOCTOR.relative_to(ROOT)}: missing {token} ({reason})')
    failures.extend(_ensure_rt_kernel_behavior())
    failures.extend(_validate_phase_metric_fixtures())
    if failures:
        for item in failures:
            print(f'[FAIL] {item}')
        return 1
    print('rt quality gate: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
