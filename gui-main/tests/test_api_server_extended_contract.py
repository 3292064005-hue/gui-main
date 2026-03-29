from __future__ import annotations

import pytest

pytest.importorskip('fastapi')
pytest.importorskip('httpx')

from fastapi.testclient import TestClient

import spine_ultrasound_ui.api_server as api_server


class _StubAdapter:
    read_only_mode = False

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def status(self) -> dict:
        return {'backend_mode': 'mock', 'execution_state': 'AUTO_READY', 'protocol_version': 1, 'session_id': 'S1'}

    def health(self) -> dict:
        return {
            'backend_mode': 'mock',
            'telemetry_stale': False,
            'latest_telemetry_age_ms': 10,
            'recovery_state': 'IDLE',
            'force_sensor_provider': 'mock_force_sensor',
            'session_locked': True,
            'build_id': 'build-1',
            'software_version': '1.0.0',
            'execution_state': 'AUTO_READY',
            'powered': True,
            'read_only_mode': False,
            'adapter_running': True,
            'protocol_version': 1,
            'topics': ['core_state'],
            'stale_threshold_ms': 250,
        }

    def snapshot(self, topics=None) -> list[dict]:
        payload = [{'topic': 'core_state', 'ts_ns': 1, 'data': {'execution_state': 'AUTO_READY'}}]
        if topics is None:
            return payload
        return [item for item in payload if item['topic'] in topics]

    def schema(self) -> dict:
        return {
            'api_version': 'v1',
            'protocol_version': 1,
            'commands': {'start_scan': {'required_payload_fields': []}},
            'telemetry_topics': {'core_state': {'core_fields': ['execution_state']}},
            'topic_catalog': {'topics': [{'topic': 'core_state', 'category': 'runtime', 'delivery': 'telemetry', 'description': 'core state'}]},
            'force_control': {
                'desired_contact_force_n': 10.0,
                'stale_telemetry_ms': 250,
                'sensor_timeout_ms': 500,
                'force_settle_window_ms': 150,
                'resume_force_band_n': 1.5,
                'max_z_force_n': 35.0,
                'warning_z_force_n': 25.0,
                'max_xy_force_n': 20.0,
                'emergency_retract_mm': 50.0,
                'force_filter_cutoff_hz': 30.0,
            },
        }

    def current_session(self) -> dict:
        return {'session_id': 'S1', 'report_available': True, 'replay_available': True, 'qa_pack_available': True, 'compare_available': True, 'readiness_available': True, 'command_trace_available': True, 'assessment_available': True}

    def current_report(self) -> dict:
        return {'session_id': 'S1', 'quality_summary': {'avg_quality_score': 0.9}}

    def current_replay(self) -> dict:
        return {'session_id': 'S1', 'timeline': []}

    def current_quality(self) -> dict:
        return {'session_id': 'S1', 'points': [], 'summary': {'coverage_ratio': 0.9}}

    def current_alarms(self) -> dict:
        return {'session_id': 'S1', 'events': [], 'summary': {'count': 0}}

    def current_artifacts(self) -> dict:
        return {'session_id': 'S1', 'artifact_registry': {'qa_pack': {'path': 'export/qa_pack.json'}}}

    def current_compare(self) -> dict:
        return {'session_id': 'S1', 'fleet_summary': {'sessions': 1}}

    def current_qa_pack(self) -> dict:
        return {'session_dir': '/tmp/S1', 'schemas': {'manifest.schema.json': {}}}

    def current_command_trace(self) -> dict:
        return {'session_id': 'S1', 'entries': [{'command': 'start_scan', 'workflow_step': 'start_scan', 'reply': {'ok': True, 'message': 'ok'}}], 'summary': {'count': 1}}

    def current_assessment(self) -> dict:
        return {'session_id': 'S1', 'confidence': 0.83, 'requires_manual_review': True, 'evidence_frames': [{'frame_id': 1, 'segment_id': 0}]}

    def current_trends(self) -> dict:
        return {'session_id': 'S1', 'history': [], 'current': {'avg_quality_score': 0.9}, 'trends': {}, 'history_window': 5, 'history_count': 0, 'fleet_summary': {'sessions': 0}}

    def current_diagnostics(self) -> dict:
        return {'session_id': 'S1', 'health_snapshot': {'execution_state': 'AUTO_READY'}, 'last_commands': [], 'last_alarms': [], 'summary': {'command_count': 1}}

    def current_annotations(self) -> dict:
        return {'session_id': 'S1', 'annotations': [{'kind': 'alarm', 'message': 'x'}]}

    def current_readiness(self) -> dict:
        return {'robot_ready': True, 'camera_ready': True, 'ultrasound_ready': True, 'force_provider_ready': True, 'storage_ready': True, 'config_valid': True, 'protocol_match': True, 'time_sync_ok': True, 'ready_to_lock': True}

    def current_profile(self) -> dict:
        return {'robot_model': 'xmate_er3', 'sdk_robot_class': 'xMateRobot', 'axis_count': 6}

    def current_patient_registration(self) -> dict:
        return {'status': 'READY', 'patient_frame': {'name': 'patient_spine'}, 'scan_corridor': {'segment_count': 4}}

    def current_scan_protocol(self) -> dict:
        return {'session_id': 'S1', 'robot_model': 'xmate_er3', 'clinical_control_modes': {'scan': 'cartesianImpedance'}, 'contact_control': {}, 'path_policy': {}}

    def current_lineage(self) -> dict:
        return {'session_id': 'S1', 'lineage': [{'kind': 'plan'}]}

    def current_resume_state(self) -> dict:
        return {'session_id': 'S1', 'resume_ready': True, 'last_successful_segment': 1}

    def current_recovery_report(self) -> dict:
        return {'session_id': 'S1', 'summary': {'latest_recovery_state': 'IDLE'}, 'events': []}

    def current_incidents(self) -> dict:
        return {'session_id': 'S1', 'summary': {'count': 1}, 'incidents': [{'incident_type': 'force_excursion_incident'}]}

    def current_resume_decision(self) -> dict:
        return {'session_id': 'S1', 'resume_allowed': False, 'blocking_reasons': ['artifact_integrity_failed'], 'mode': 'restart_required'}

    def current_event_log_index(self) -> dict:
        return {'session_id': 'S1', 'events': [{'topic': 'command_trace'}], 'summary': {'event_count': 1}}

    def current_recovery_timeline(self) -> dict:
        return {'session_id': 'S1', 'timeline': [{'decision': 'hold'}], 'summary': {'decision_count': 1}}

    def role_catalog(self) -> dict:
        return {'roles': {'operator': {'runtime_read': True, 'session_read': True, 'command_groups': ['control'], 'export_allowed': True}}}

    def topic_catalog(self) -> dict:
        return {'topics': [{'topic': 'core_state', 'category': 'runtime', 'delivery': 'telemetry', 'description': 'core state'}], 'roles': {'operator': {'runtime_read': True, 'session_read': True, 'command_groups': ['control'], 'export_allowed': True}}}

    def command(self, command: str, payload: dict) -> dict:
        return {'ok': True, 'message': 'ok', 'request_id': 'r1', 'data': payload, 'protocol_version': 1}

    def camera_frame(self) -> str:
        return 'camera'

    def ultrasound_frame(self) -> str:
        return 'ultrasound'


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(api_server, 'adapter', _StubAdapter())
    return TestClient(api_server.app)


def test_extended_headless_endpoints(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        assert client.get('/api/v1/schema/artifacts').status_code == 200
        assert client.get('/api/v1/topics').json()['topics'][0]['topic'] == 'core_state'
        assert 'operator' in client.get('/api/v1/roles').json()['roles']
        assert client.get('/api/v1/sessions/current/quality').json()['summary']['coverage_ratio'] == 0.9
        assert client.get('/api/v1/sessions/current/alarms').json()['summary']['count'] == 0
        assert client.get('/api/v1/sessions/current/artifacts').json()['artifact_registry']['qa_pack']['path'] == 'export/qa_pack.json'
        assert client.get('/api/v1/sessions/current/compare').json()['fleet_summary']['sessions'] == 1
        assert client.get('/api/v1/sessions/current/trends').json()['session_id'] == 'S1'
        assert client.get('/api/v1/sessions/current/diagnostics').json()['summary']['command_count'] == 1
        assert client.get('/api/v1/sessions/current/annotations').json()['annotations'][0]['kind'] == 'alarm'
        assert client.get('/api/v1/sessions/current/readiness').json()['ready_to_lock'] is True
        assert client.get('/api/v1/sessions/current/profile').json()['axis_count'] == 6
        assert client.get('/api/v1/sessions/current/patient-registration').json()['patient_frame']['name'] == 'patient_spine'
        assert client.get('/api/v1/sessions/current/scan-protocol').json()['robot_model'] == 'xmate_er3'
        assert client.get('/api/v1/sessions/current/command-trace').json()['summary']['count'] == 1
        assert client.get('/api/v1/sessions/current/assessment').json()['requires_manual_review'] is True
        assert client.get('/api/v1/sessions/current/lineage').json()['lineage'][0]['kind'] == 'plan'
        assert client.get('/api/v1/sessions/current/resume-state').json()['resume_ready'] is True
        assert client.get('/api/v1/sessions/current/recovery-report').json()['summary']['latest_recovery_state'] == 'IDLE'
        assert client.get('/api/v1/sessions/current/incidents').json()['summary']['count'] == 1
        assert client.get('/api/v1/sessions/current/resume-decision').json()['mode'] == 'restart_required'
        assert client.get('/api/v1/sessions/current/event-log-index').json()['summary']['event_count'] == 1
        assert client.get('/api/v1/sessions/current/recovery-timeline').json()['summary']['decision_count'] == 1
        assert 'schemas' in client.get('/api/v1/sessions/current/qa-pack').json()


def test_researcher_role_cannot_issue_commands(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.post('/api/v1/commands/start_scan', headers={'X-Spine-Role': 'researcher'}, json={})
        assert response.status_code == 403
        assert 'not allowed' in response.json()['detail']


def test_operator_role_can_issue_commands(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.post('/api/v1/commands/start_scan', headers={'X-Spine-Role': 'operator'}, json={})
        assert response.status_code == 200
        assert response.json()['ok'] is True
