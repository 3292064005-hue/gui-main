from __future__ import annotations

from pathlib import Path
import os

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.api_command_guard import ApiCommandGuardService, ApiCommandHeaders
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter
from spine_ultrasound_ui.services.ipc_protocol import COMMAND_SPECS, is_write_command
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.scan_plan_contract import runtime_scan_plan_payload
from spine_ultrasound_ui.services.role_matrix import RoleMatrix


class _AdapterStub:
    read_only_mode = True
    role_matrix = RoleMatrix()


def test_compile_and_query_final_verdict_are_registered_as_read_contract_commands() -> None:
    assert 'compile_scan_plan' in COMMAND_SPECS
    assert 'query_final_verdict' in COMMAND_SPECS
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
    compile_result = adapter.command('compile_scan_plan', {
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
    })
    assert 'final_verdict' in compile_result['data']
