import json
from pathlib import Path

from spine_ultrasound_ui.models import SystemState
from spine_ultrasound_ui.services.mainline_runtime_doctor_service import MainlineRuntimeDoctorService
from spine_ultrasound_ui.services.mock_core_runtime import MockCoreRuntime


def _rt_blocker_names(result: dict) -> set[str]:
    return {item['name'] for item in result.get('blockers', []) if item.get('section') == 'rt_kernel'}


def _baseline_inputs():
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
        assert envelope.ok, command
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


def test_runtime_doctor_rt_quality_fixture_scenarios() -> None:
    config, sdk_runtime, backend_link, model_report, session_governance = _baseline_inputs()
    service = MainlineRuntimeDoctorService()
    fixture = json.loads(Path('artifacts/verification/current_delivery_fix/rt_quality_gate_scenarios.json').read_text(encoding='utf-8'))

    base = service.inspect(
        config=config,
        sdk_runtime=sdk_runtime,
        backend_link=backend_link,
        model_report=model_report,
        session_governance=session_governance,
    )
    assert _rt_blocker_names(base) == set(fixture['baseline_expectations']['expected_blockers'])

    for scenario in fixture['scenarios']:
        scenario_runtime = dict(sdk_runtime)
        rt_kernel = dict(sdk_runtime['rt_kernel_contract'])
        rt_kernel.update(dict(scenario['patch']))
        scenario_runtime['rt_kernel_contract'] = rt_kernel
        result = service.inspect(
            config=config,
            sdk_runtime=scenario_runtime,
            backend_link=backend_link,
            model_report=model_report,
            session_governance=session_governance,
        )
        blockers = _rt_blocker_names(result)
        for expected in scenario['expected_blockers']:
            assert expected in blockers


def test_rt_quality_gate_uses_committed_baseline_fixture() -> None:
    fixture = json.loads(Path('artifacts/verification/current_delivery_fix/rt_quality_baseline.json').read_text(encoding='utf-8'))
    assert fixture['nominal_loop_hz'] == 1000
    assert fixture['fixed_period_enforced'] is True
    assert fixture['rt_quality_gate_passed'] is True
    assert fixture['monitors']['jitter_monitor'] is True


def test_rt_quality_observed_fixture_stays_within_budget() -> None:
    fixture = json.loads(Path('artifacts/verification/current_delivery_fix/rt_quality_observed.json').read_text(encoding='utf-8'))
    assert fixture['rt_quality_gate_passed'] is True
    assert fixture['fixed_period_enforced'] is True
    jitter_budget = float(fixture['jitter_budget_ms'])
    cycle_budget = float(fixture['current_period_ms']) + jitter_budget
    for sample in fixture['loop_samples']:
        assert sample['overrun'] is False
        assert abs(float(sample['wake_jitter_ms'])) <= jitter_budget
        assert float(sample['execution_ms']) <= cycle_budget


from scripts.validate_hil_phase_metrics import validate_metrics


def test_rt_phase_metrics_fixture_passes_validator() -> None:
    runtime_cfg = json.loads(Path('artifacts/verification/current_delivery_fix/rt_phase_runtime_config.json').read_text(encoding='utf-8'))
    evidence = json.loads(Path('artifacts/verification/current_delivery_fix/rt_phase_metrics_evidence.json').read_text(encoding='utf-8'))
    assert evidence['evidence_kind'] == 'measured_phase_metrics'
    assert evidence['quality_verdict'] == 'pass'
    assert validate_metrics(runtime_cfg, evidence) == []
