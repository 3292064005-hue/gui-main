from __future__ import annotations

import json
import os
from pathlib import Path

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState, RuntimeConfig
from spine_ultrasound_ui.services.api_command_guard import ApiCommandGuardService, ApiCommandHeaders
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.planning import LocalizationResult
from spine_ultrasound_ui.services.runtime_command_catalog import (
    canonical_command_name,
    command_alias_kind,
    is_write_command,
)
from spine_ultrasound_ui.services.scan_plan_contract import runtime_scan_plan_payload


class _AdapterStub:
    read_only_mode = True



def _ready_localization() -> LocalizationResult:
    return LocalizationResult(
        status=CapabilityStatus(
            ready=True,
            state='READY',
            implementation=ImplementationState.IMPLEMENTED.value,
            detail='deterministic test localization',
        ),
        roi_center_y=0.0,
        segment_count=3,
        confidence=0.97,
        patient_registration={
            'registration_hash': 'reg-test-001',
            'scan_corridor': {
                'start_mm': {'x': 110.0, 'y': -18.0},
                'centerline_mm': {'y': 0.0},
            },
        },
        localization_readiness={'ready': True, 'source': 'test'},
        calibration_bundle={'bundle_id': 'cal-test-001'},
        manual_adjustment={'approved': False},
        source_frame_set={'frames': []},
        localization_replay_index={'entries': []},
        guidance_algorithm_registry={'algorithms': []},
        guidance_processing_steps=[{'name': 'test-localization', 'ok': True}],
    )



def test_runtime_verdict_service_prefers_runtime_contract(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path / 'backend')
    controller = AppController(tmp_path / 'app', backend)
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    report = controller.model_report
    assert report['authority_source'] == 'cpp_robot_core'
    assert report['verdict_kind'] == 'final'
    assert report['final_verdict']['advisory_only'] is False
    assert report['final_verdict']['source'] == 'cpp_robot_core'



def test_session_intelligence_materializes_governance_snapshots(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path / 'backend')
    controller = AppController(tmp_path / 'app', backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()

    session_service = controller.session_service
    assert session_service.current_session_dir is not None
    session_service.save_summary(
        {
            'control_plane_snapshot': {'summary_state': 'ready'},
            'control_authority': {'owner': {'actor_id': 'tester'}},
            'bridge_observability': {'summary_state': 'ready'},
        }
    )
    session_dir = session_service.current_session_dir
    control_plane = json.loads((session_dir / 'derived' / 'session' / 'control_plane_snapshot.json').read_text(encoding='utf-8'))
    authority = json.loads((session_dir / 'derived' / 'session' / 'control_authority_snapshot.json').read_text(encoding='utf-8'))
    bridge = json.loads((session_dir / 'derived' / 'events' / 'bridge_observability_report.json').read_text(encoding='utf-8'))
    seal = json.loads((session_dir / 'meta' / 'session_evidence_seal.json').read_text(encoding='utf-8'))
    manifest = json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8'))
    assert control_plane['summary_state'] in {'ready', 'degraded', 'blocked', 'warning'}
    assert authority['session_id'] == manifest['session_id']
    assert bridge['session_id'] == manifest['session_id']
    assert seal['seal_digest']
    assert manifest['artifact_registry']['control_plane_snapshot']['path'] == 'derived/session/control_plane_snapshot.json'
    assert manifest['artifact_registry']['session_evidence_seal']['path'] == 'meta/session_evidence_seal.json'



def test_validate_and_query_final_verdict_commands_are_manifest_backed_read_contracts() -> None:
    assert canonical_command_name('validate_scan_plan') == 'validate_scan_plan'
    assert canonical_command_name('compile_scan_plan') == 'validate_scan_plan'
    assert command_alias_kind('compile_scan_plan') == 'deprecated_alias'
    assert canonical_command_name('query_final_verdict') == 'query_final_verdict'
    assert is_write_command('validate_scan_plan') is False
    assert is_write_command('compile_scan_plan') is False
    assert is_write_command('query_final_verdict') is False



def test_runtime_scan_plan_payload_materializes_plan_hash(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path / 'backend')
    controller = AppController(tmp_path / 'app', backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()

    payload = runtime_scan_plan_payload(controller.execution_scan_plan)
    assert payload is not None
    assert payload['plan_hash'] == controller.execution_scan_plan.plan_hash()
    assert payload['plan_id'] == controller.execution_scan_plan.plan_id



def test_api_command_guard_allows_read_contract_commands_in_review_profile() -> None:
    guard = ApiCommandGuardService(env={'SPINE_DEPLOYMENT_PROFILE': 'review'})
    payload = guard.normalize_payload(
        adapter=_AdapterStub(),
        command='query_final_verdict',
        payload={},
        headers=ApiCommandHeaders(role='review', actor='auditor', workspace='review', intent='query-final-verdict'),
    )
    assert payload['_command_context']['role'] == 'review'
    assert payload['_command_context']['intent_reason'] == 'query-final-verdict'



def test_headless_adapter_allows_read_contract_commands_in_review_profile(tmp_path: Path) -> None:
    old_profile = os.environ.get('SPINE_DEPLOYMENT_PROFILE')
    try:
        os.environ['SPINE_DEPLOYMENT_PROFILE'] = 'review'
        adapter = HeadlessAdapter('mock', '127.0.0.1', 5656, '127.0.0.1', 5657)
    finally:
        if old_profile is None:
            os.environ.pop('SPINE_DEPLOYMENT_PROFILE', None)
        else:
            os.environ['SPINE_DEPLOYMENT_PROFILE'] = old_profile
    result = adapter.command('query_final_verdict', {})
    assert result['ok'] is True
    compile_result = adapter.command(
        'validate_scan_plan',
        {
            'scan_plan': {
                'session_id': 'S1',
                'plan_id': 'P1',
                'plan_hash': 'HASH12345678',
                'planner_version': 'planner',
                'registration_hash': 'reg',
                'approach_pose': {'x': 0, 'y': 0, 'z': 200, 'rx': 0, 'ry': 0, 'rz': 0},
                'retreat_pose': {'x': 0, 'y': 0, 'z': 210, 'rx': 0, 'ry': 0, 'rz': 0},
                'segments': [
                    {
                        'segment_id': 1,
                        'waypoints': [{'x': 0, 'y': 0, 'z': 200, 'rx': 0, 'ry': 0, 'rz': 0}],
                    }
                ],
            },
            'config_snapshot': RuntimeConfig().to_dict(),
        },
    )
    assert 'final_verdict' in compile_result['data']


class _FailingReply:
    def __init__(self, *, message: str = 'query failed') -> None:
        self.ok = False
        self.message = message
        self.data = {'error_type': 'runtime_rejected', 'http_status': 409, 'retryable': False}


def test_robot_core_verdict_service_does_not_fallback_to_cached_verdict_on_failed_reply() -> None:
    from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService
    from spine_ultrasound_ui.services.backend_errors import BackendOperationError
    from spine_ultrasound_ui.services.robot_core_verdict_service import RobotCoreVerdictService

    service = RobotCoreVerdictService(
        send_command=lambda command, payload: _FailingReply(message=f'{command} failed'),
        authoritative_service=BackendAuthoritativeContractService(),
        current_config=RuntimeConfig,
        read_cached_contracts=lambda: (
            {'accepted': True, 'source': 'stale-cache'},
            {'final_verdict': {'accepted': True, 'source': 'stale-envelope'}},
            {'final_verdict': {'accepted': True, 'source': 'stale-control-plane'}},
        ),
    )

    try:
        service.resolve_final_verdict(read_only=True)
    except BackendOperationError as exc:
        assert exc.error_type == 'runtime_rejected'
        assert exc.retryable is False
    else:
        raise AssertionError('expected BackendOperationError when query_final_verdict reply is not OK')
