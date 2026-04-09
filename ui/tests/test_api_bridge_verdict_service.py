from __future__ import annotations

import threading
from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.api_bridge_backend import ApiBridgeBackend
from spine_ultrasound_ui.services.api_bridge_verdict_service import ApiBridgeVerdictService
from spine_ultrasound_ui.services.backend_errors import BackendOperationError
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope


class _LeaseSpy:
    def __init__(self) -> None:
        self.calls: list[bool] = []

    def ensure_control_lease(self, *, force: bool = False) -> None:
        self.calls.append(bool(force))


class _OkResponse:
    status_code = 200
    content = b'{}'

    def json(self) -> dict:
        return {
            'ok': True,
            'message': 'ok',
            'request_id': 'req-1',
            'data': {'final_verdict': {'accepted': True, 'source': 'api'}},
            'protocol_version': 1,
        }


class _ClientStub:
    def __init__(self, response) -> None:
        self.response = response
        self.calls: list[tuple[str, dict | None, dict | None]] = []

    def post(self, url: str, json=None, headers=None):
        self.calls.append((url, json, headers))
        return self.response


class _AuthoritativeStub:
    def extract_final_verdict(self, payload):
        data = dict(payload or {})
        verdict = data.get('final_verdict')
        return dict(verdict or {})


def test_api_bridge_send_command_skips_lease_acquire_for_read_only_context(tmp_path: Path) -> None:
    backend = ApiBridgeBackend(tmp_path)
    lease_spy = _LeaseSpy()
    backend._lease_service = lease_spy
    backend._client = _ClientStub(_OkResponse())
    backend._capture_reply_contracts = lambda reply: None
    backend._log = lambda level, message: None

    reply = backend.send_command('query_final_verdict', {}, context={'include_lease': False, 'intent_reason': 'query_final_verdict'})

    assert reply.ok is True
    assert lease_spy.calls == []


class _VerdictHostStub:
    def __init__(self, reply: ReplyEnvelope) -> None:
        self.reply = reply
        self.calls: list[str] = []
        self._authoritative_service = _AuthoritativeStub()
        self._last_final_verdict = {'accepted': True, 'source': 'stale-cache'}
        self._control_plane_cache = {'final_verdict': {'accepted': True, 'source': 'stale-control-plane'}}
        self._lock = threading.Lock()
        self.config = RuntimeConfig()

    def send_command(self, command: str, payload=None, *, context=None) -> ReplyEnvelope:
        self.calls.append(command)
        return self.reply




def test_api_bridge_review_profile_never_acquires_control_lease_on_startup(tmp_path: Path) -> None:
    backend = ApiBridgeBackend(tmp_path, deployment_profile='review')
    lease_spy = _LeaseSpy()
    backend._lease_service = lease_spy
    backend._spawn = lambda target, name: None
    backend._push_runtime_config = lambda: None
    backend._log = lambda level, message: None

    backend.start()

    assert lease_spy.calls == []

def test_api_bridge_verdict_service_does_not_fallback_to_stale_cache_after_compile_failure() -> None:
    host = _VerdictHostStub(
        ReplyEnvelope(
            ok=False,
            message='scan plan invalid',
            request_id='req-2',
            data={'error_type': 'invalid_payload', 'http_status': 400, 'retryable': False},
            protocol_version=1,
        )
    )
    service = ApiBridgeVerdictService(host)

    try:
        service.resolve_final_verdict(plan=None, config=RuntimeConfig(), read_only=False)
    except BackendOperationError as exc:
        assert exc.error_type == 'invalid_payload'
        assert exc.http_status == 400
        assert exc.retryable is False
        assert host.calls == ['validate_scan_plan']
    else:  # pragma: no cover - this is the regression we are guarding against
        raise AssertionError('compile failure unexpectedly fell back to stale cached verdict')
