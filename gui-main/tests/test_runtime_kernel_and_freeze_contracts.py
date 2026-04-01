from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mainline_runtime_doctor_service import MainlineRuntimeDoctorService
from spine_ultrasound_ui.services.mainline_task_tree_service import MainlineTaskTreeService
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService


def test_runtime_assets_include_hardware_rt_kernel_and_drift_contracts(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path)
    service = SdkRuntimeAssetService()
    snapshot = service.refresh(backend, RuntimeConfig())

    assert snapshot['hardware_lifecycle_contract']['controller_manager_model'] == 'hardware_layer__read_update_write'
    assert snapshot['rt_kernel_contract']['read_update_write'] == ['read_state', 'update_phase_policy', 'write_command']
    assert snapshot['session_drift_contract']['summary_state'] == 'ready'
    assert snapshot['motion_contract']['sdk_boundary_units']['contract_hash']


def test_runtime_doctor_blocks_when_session_freeze_drifts() -> None:
    doctor = MainlineRuntimeDoctorService()
    result = doctor.inspect(
        config=RuntimeConfig(),
        sdk_runtime={
            'control_governance_contract': {'single_control_source_required': True, 'session_binding_valid': False, 'runtime_config_bound': True, 'current_execution_state': 'SCANNING'},
            'clinical_mainline_contract': {'clinical_mainline_mode': 'cartesianImpedance'},
            'motion_contract': {'rt_mode': 'cartesianImpedance', 'nrt_contract': {}, 'rt_contract': {}},
            'session_freeze': {'session_locked': True},
            'session_drift_contract': {'summary_state': 'blocked', 'detail': 'hard freeze drift detected', 'drifts': [{'name': 'runtime_profile_hash'}]},
            'hardware_lifecycle_contract': {'summary_state': 'ready', 'live_takeover_ready': True},
            'rt_kernel_contract': {'summary_state': 'ready', 'monitors': {'reference_limiter': True, 'freshness_guard': True, 'jitter_monitor': True}},
            'model_authority_contract': {'planner_supported': True, 'xmate_model_supported': True},
            'runtime_alignment': {'sdk_available': True},
            'environment_doctor': {'summary_state': 'ready', 'summary_label': 'ok', 'detail': 'ok'},
            'dual_state_machine_contract': {'summary_state': 'ready', 'execution_and_clinical_aligned': True},
            'mainline_executor_contract': {'summary_state': 'ready', 'task_tree_aligned': True, 'rt_executor': {'summary_state': 'ready'}, 'nrt_executor': {'summary_state': 'ready'}},
            'mainline_task_tree': {'summary_state': 'ready', 'detail': 'ok'},
            'release_contract': {'summary_state': 'ready'},
            'deployment_contract': {'summary_state': 'ready'},
            'controller_evidence': {'last_event': 'scan_started'},
        },
        backend_link={'control_plane': {'control_authority': {'summary_state': 'ready'}}},
        model_report={'final_verdict': {'accepted': True}},
        session_governance={'summary_state': 'ready'},
    )
    assert result['summary_state'] == 'blocked'
    assert any(item['name'] == 'session_freeze_drift' for item in result['blockers'])
    assert result['session_freeze_drift_count'] == 1


def test_mainline_task_tree_exports_behavior_tree_outline() -> None:
    service = MainlineTaskTreeService()
    tree = service.build(
        config=RuntimeConfig(),
        sdk_runtime={
            'control_governance_contract': {'controller_online': True, 'powered': True, 'automatic_mode': True, 'session_binding_valid': True, 'rt_ready': True, 'current_execution_state': 'PATH_VALIDATED'},
            'clinical_mainline_contract': {'clinical_mainline_mode': 'cartesianImpedance'},
            'session_freeze': {'session_locked': True},
            'session_drift_contract': {'summary_state': 'ready', 'drifts': []},
            'release_contract': {'session_locked': True, 'final_verdict': {'accepted': True}},
            'mainline_executor_contract': {'task_tree_aligned': True, 'rt_executor': {'summary_state': 'ready'}, 'nrt_executor': {'summary_state': 'ready'}},
            'dual_state_machine_contract': {'runtime_state': 'PATH_VALIDATED', 'clinical_task_state': 'plan_validated', 'execution_and_clinical_aligned': True},
            'environment_doctor': {'summary_state': 'ready'},
            'hardware_lifecycle_contract': {'summary_state': 'ready'},
            'rt_kernel_contract': {'summary_state': 'ready'},
        },
        backend_link={'control_plane': {'control_authority': {'summary_state': 'ready'}}},
        model_report={'final_verdict': {'accepted': True}},
        session_governance={'summary_state': 'ready'},
    )
    assert tree['tree_format'] == 'behavior_tree_async_contract_v2'
    assert '<BehaviorTree ID="ClinicalMainline">' in tree['xml_outline']
    assert any(node['name'] == 'ensure_control_lease' for node in tree['nodes'])
    assert any(node['name'] == 'export_artifacts' for node in tree['nodes'])
