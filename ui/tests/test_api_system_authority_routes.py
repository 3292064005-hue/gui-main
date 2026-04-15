from __future__ import annotations

import pytest

pytest.importorskip('fastapi')
pytest.importorskip('httpx')

from fastapi.testclient import TestClient

import spine_ultrasound_ui.api_server as api_server
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter


class _StubAdapter:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def status(self) -> dict:
        return {'backend_mode': 'mock', 'execution_state': 'AUTO_READY', 'protocol_version': 1}

    def health(self) -> dict:
        return {'adapter_running': True, 'telemetry_stale': False, 'latest_telemetry_age_ms': 5}

    def snapshot(self, topics=None):
        return []

    def schema(self) -> dict:
        return {'protocol_version': 1, 'commands': {}, 'telemetry_topics': {}, 'force_control': {}}

    def runtime_config(self) -> dict:
        return {'runtime_config': {}}

    def topic_catalog(self) -> dict:
        return {'topics': []}

    def recent_commands(self) -> dict:
        return {'recent_commands': []}

    def resolve_control_authority(self) -> dict:
        return {'summary_state': 'ready', 'summary_label': '控制权已收口', 'detail': 'runtime-owned'}

    def resolve_authoritative_runtime_envelope(self) -> dict:
        return {
            'authority_source': 'headless_adapter',
            'authoritative_runtime_envelope_present': True,
            'control_authority': {'summary_state': 'ready', 'summary_label': '控制权已收口', 'detail': 'runtime-owned'},
            'runtime_config_applied': {'pressure_target': 8.0},
            'final_verdict': {'accepted': True, 'source': 'cpp_robot_core'},
        }

    def query_final_verdict_snapshot(self) -> dict:
        return {'accepted': True, 'source': 'cpp_robot_core'}


class _StubContainer:
    def __init__(self) -> None:
        self.runtime_adapter = _StubAdapter()
        self.deployment_profile_service = None
        self.command_guard_service = None


class _AdapterContainer:
    def __init__(self, adapter) -> None:
        self.runtime_adapter = adapter
        self.deployment_profile_service = None
        self.command_guard_service = None


def test_system_routes_prefer_canonical_authority_surface() -> None:
    app = api_server.create_app(runtime_container=_StubContainer(), allowed_origins=['http://localhost:3000'])
    with TestClient(app) as client:
        authority = client.get('/api/v1/control-authority')
        assert authority.status_code == 200
        assert authority.json()['detail'] == 'runtime-owned'

        envelope = client.get('/api/v1/authoritative-runtime-envelope')
        assert envelope.status_code == 200
        assert envelope.json()['final_verdict']['accepted'] is True

        verdict = client.get('/api/v1/final-verdict')
        assert verdict.status_code == 200
        assert verdict.json()['accepted'] is True


def test_system_routes_work_with_real_headless_adapter_surface() -> None:
    adapter = HeadlessAdapter('mock', '127.0.0.1', 5656, '127.0.0.1', 5657)
    adapter.start = lambda: None  # type: ignore[assignment]
    adapter.stop = lambda: None  # type: ignore[assignment]
    app = api_server.create_app(runtime_container=_AdapterContainer(adapter), allowed_origins=['http://localhost:3000'])
    with TestClient(app) as client:
        authority = client.get('/api/v1/control-authority').json()
        assert authority['summary_state'] in {'ready', 'degraded'}
        assert authority['owner']['actor_id'] == 'mock-runtime'

        envelope = client.get('/api/v1/authoritative-runtime-envelope').json()
        assert envelope['authoritative_runtime_envelope_present'] is True
        assert envelope['control_authority']['owner']['actor_id'] == 'mock-runtime'

        verdict = client.get('/api/v1/final-verdict').json()
        assert verdict['accepted'] is False
        assert verdict['source'] == 'cpp_robot_core'
