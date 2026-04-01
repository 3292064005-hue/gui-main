
from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mainline_runtime_doctor_service import MainlineRuntimeDoctorService
from spine_ultrasound_ui.services.mainline_task_tree_service import MainlineTaskTreeService
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService


def test_runtime_assets_include_state_machine_executor_and_task_tree(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path)
    service = SdkRuntimeAssetService()
    snapshot = service.refresh(backend, RuntimeConfig())

    assert snapshot['dual_state_machine_contract']['execution_and_clinical_aligned'] is True
    assert snapshot['mainline_executor_contract']['rt_executor']['reference_limiter_enabled'] is True
    assert snapshot['mainline_task_tree']['nodes'][0]['name'] == 'ensure_connected'
    assert snapshot['mainline_task_tree']['async_policy'].startswith('tree_nodes_are_non_blocking')


def test_task_tree_blocks_when_control_authority_is_blocked() -> None:
    service = MainlineTaskTreeService()
    result = service.build(
        config=RuntimeConfig(),
        sdk_runtime={
            'control_governance_contract': {'controller_online': True, 'powered': True, 'automatic_mode': True, 'session_binding_valid': True, 'rt_ready': True, 'current_execution_state': 'PATH_VALIDATED'},
            'clinical_mainline_contract': {'clinical_mainline_mode': 'cartesianImpedance'},
            'session_freeze': {'session_locked': True},
            'release_contract': {'session_locked': True, 'final_verdict': {'accepted': True}},
            'mainline_executor_contract': {'task_tree_aligned': True, 'rt_executor': {'summary_state': 'ready'}, 'nrt_executor': {'summary_state': 'ready'}},
            'dual_state_machine_contract': {'runtime_state': 'PATH_VALIDATED', 'clinical_task_state': 'plan_validated', 'execution_and_clinical_aligned': True},
            'environment_doctor': {'summary_state': 'ready'},
        },
        backend_link={'control_plane': {'control_authority': {'summary_state': 'blocked', 'detail': 'lease conflict'}}},
        model_report={'final_verdict': {'accepted': True}},
        session_governance={'summary_state': 'ready'},
    )
    assert result['summary_state'] == 'blocked'
    assert any(item['name'] == 'control_authority_conflict' for item in result['blockers'])


def test_runtime_doctor_reads_new_executor_and_state_machine_contracts() -> None:
    doctor = MainlineRuntimeDoctorService()
    result = doctor.inspect(
        config=RuntimeConfig(),
        sdk_runtime={
            'control_governance_contract': {'single_control_source_required': True, 'session_binding_valid': True, 'runtime_config_bound': True, 'current_execution_state': 'SCANNING'},
            'clinical_mainline_contract': {'clinical_mainline_mode': 'cartesianImpedance'},
            'motion_contract': {'rt_mode': 'cartesianImpedance', 'nrt_contract': {}, 'rt_contract': {}},
            'session_freeze': {'session_locked': True},
            'model_authority_contract': {'planner_supported': True, 'xmate_model_supported': True},
            'runtime_alignment': {'sdk_available': True},
            'environment_doctor': {'summary_state': 'ready', 'summary_label': 'ok', 'detail': 'ok'},
            'dual_state_machine_contract': {'summary_state': 'blocked', 'detail': 'misaligned', 'execution_and_clinical_aligned': False},
            'mainline_executor_contract': {'summary_state': 'ready', 'task_tree_aligned': True, 'rt_executor': {'summary_state': 'warning', 'detail': 'rt degraded'}, 'nrt_executor': {'summary_state': 'ready'}},
            'mainline_task_tree': {'summary_state': 'warning', 'detail': 'pending startup'},
            'release_contract': {'summary_state': 'ready'},
            'deployment_contract': {'summary_state': 'ready'},
            'controller_evidence': {'last_event': 'scan_started'},
        },
        backend_link={'control_plane': {'control_authority': {'summary_state': 'ready'}}},
        model_report={'final_verdict': {'accepted': True}},
        session_governance={'summary_state': 'ready'},
    )
    assert result['summary_state'] == 'blocked'
    assert any(item['name'] == 'dual_state_machine_misaligned' for item in result['blockers'])
    assert any(item['name'] == 'rt_executor_warning' for item in result['warnings'])
