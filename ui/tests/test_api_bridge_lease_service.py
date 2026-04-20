from __future__ import annotations

from types import SimpleNamespace

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.api_bridge_lease_service import ApiBridgeLeaseService
from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService
from spine_ultrasound_ui.services.backend_projection_cache import BackendProjectionCache


class _FakeResponse:
    def __init__(self, body: dict):
        self._body = body
        self.content = b'{}'

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return dict(self._body)


class _FakeClient:
    def __init__(self, body: dict):
        self._body = body
        self.calls: list[tuple[str, dict, dict]] = []

    def post(self, path: str, *, json: dict, headers: dict):
        self.calls.append((path, dict(json), dict(headers)))
        return _FakeResponse(self._body)


class _FakeHost:
    def __init__(self, body: dict):
        self._actor_id = 'desktop-auditor'
        self._role = 'operator'
        self._workspace = 'desktop'
        self._client = _FakeClient(body)
        self._authoritative_service = BackendAuthoritativeContractService()
        self._runtime_config_cache = {}
        self.config = RuntimeConfig()
        self._last_final_verdict = {}
        self._control_authority_cache = {}
        self._authoritative_envelope = {}
        self._lease_id = ''
        self._projection_cache = BackendProjectionCache()
        self._last_errors: list[str] = []
        self._lock = SimpleNamespace(__enter__=lambda s: None, __exit__=lambda s, exc_type, exc, tb: False)
        self._logs: list[tuple[str, str]] = []

    def _log(self, level: str, message: str) -> None:
        self._logs.append((level, message))


class _SimpleLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_host(body: dict) -> _FakeHost:
    host = _FakeHost(body)
    host._lock = _SimpleLock()
    return host


def test_api_bridge_lease_service_uses_nested_control_authority_when_present() -> None:
    body = {
        'ok': True,
        'summary_state': 'ready',
        'summary_label': '控制权租约已获取',
        'detail': 'lease acquired',
        'lease': {
            'lease_id': 'lease-123',
            'actor_id': 'desktop-auditor',
            'workspace': 'desktop',
            'role': 'operator',
            'session_id': 'S-1',
        },
        'control_authority': {
            'summary_state': 'ready',
            'summary_label': 'runtime authority lease active',
            'detail': 'runtime lease active',
            'owner': {
                'actor_id': 'desktop-auditor',
                'workspace': 'desktop',
                'role': 'operator',
                'session_id': 'S-1',
            },
            'active_lease': {
                'lease_id': 'lease-123',
                'actor_id': 'desktop-auditor',
                'workspace': 'desktop',
                'role': 'operator',
                'session_id': 'S-1',
            },
            'owner_provenance': {'source': 'cpp_robot_core'},
            'workspace_binding': 'desktop',
            'session_binding': 'S-1',
            'blockers': [],
            'warnings': [],
        },
    }
    host = _make_host(body)
    service = ApiBridgeLeaseService(host)

    service.ensure_control_lease()

    assert host._lease_id == 'lease-123'
    authority = host._control_authority_cache
    assert authority['owner']['actor_id'] == 'desktop-auditor'
    assert authority['active_lease']['lease_id'] == 'lease-123'
    assert authority['owner_provenance']['source'] == 'cpp_robot_core'


def test_api_bridge_lease_service_synthesizes_authority_from_lease_when_nested_surface_missing() -> None:
    body = {
        'ok': True,
        'summary_state': 'ready',
        'summary_label': '控制权租约已获取',
        'detail': 'lease acquired',
        'lease': {
            'lease_id': 'lease-456',
            'actor_id': 'desktop-auditor',
            'workspace': 'desktop',
            'role': 'operator',
            'session_id': 'S-2',
            'source': 'cpp_robot_core',
        },
    }
    host = _make_host(body)
    service = ApiBridgeLeaseService(host)

    service.ensure_control_lease()

    assert host._lease_id == 'lease-456'
    authority = host._control_authority_cache
    assert authority['owner']['actor_id'] == 'desktop-auditor'
    assert authority['active_lease']['lease_id'] == 'lease-456'
    assert authority['workspace_binding'] == 'desktop'
    assert authority['session_binding'] == 'S-2'


def test_api_bridge_lease_service_release_clears_cached_lease_id() -> None:
    body = {
        'ok': True,
        'summary_state': 'released',
        'summary_label': '控制权租约已释放',
        'detail': 'lease released',
        'control_authority': {
            'summary_state': 'released',
            'summary_label': '控制权租约已释放',
            'detail': 'runtime lease released',
            'owner': {},
            'active_lease': {},
            'owner_provenance': {'source': 'cpp_robot_core'},
            'workspace_binding': '',
            'session_binding': '',
            'blockers': [],
            'warnings': [],
        },
    }
    host = _make_host(body)
    host._lease_id = 'lease-789'
    service = ApiBridgeLeaseService(host)

    authority = service.release_control_lease(reason='done')

    assert host._lease_id == ''
    assert authority['summary_state'] == 'released'
    assert host._client.calls[-1][0] == '/api/v1/control-lease/release'

