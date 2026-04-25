from __future__ import annotations

from types import SimpleNamespace

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.api_bridge_lease_service import ApiBridgeLeaseService
from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService


class _Host:
    def __init__(self) -> None:
        self._lease_id = ''
        self._actor_id = 'desktop-1'
        self._role = 'operator'
        self._workspace = 'desktop'
        self._runtime_config_cache = {'pressure_target': 7.5}
        self._last_final_verdict = {}
        self._control_authority_cache = {'summary_state': 'ready', 'summary_label': 'desktop owns control', 'detail': 'runtime-published authority'}
        self._authoritative_envelope = {
            'control_authority': dict(self._control_authority_cache),
            'authoritative_runtime_envelope_present': True,
        }
        self._authoritative_service = BackendAuthoritativeContractService()
        self._projection_cache = SimpleNamespace(update_partition=lambda *args, **kwargs: None)
        self._last_errors = []
        self.config = RuntimeConfig()
        self.logs: list[tuple[str, str]] = []

    def _log(self, level: str, message: str) -> None:
        self.logs.append((level, message))

    def resolve_authoritative_runtime_envelope(self) -> dict[str, object]:
        return dict(self._authoritative_envelope)


def test_ensure_control_lease_is_noop_read_only() -> None:
    host = _Host()
    service = ApiBridgeLeaseService(host)

    service.ensure_control_lease()

    assert host._lease_id == ''
    assert any('read-only' in message for _, message in host.logs)


def test_acquire_control_lease_returns_runtime_snapshot_without_http_mutation() -> None:
    host = _Host()
    service = ApiBridgeLeaseService(host)

    authority = service.acquire_control_lease(force=True)

    assert authority['summary_state'] == 'ready'
    assert authority['summary_label'] == 'desktop owns control'
    assert host._lease_id == ''


def test_release_control_lease_returns_current_snapshot_without_mutation() -> None:
    host = _Host()
    service = ApiBridgeLeaseService(host)

    authority = service.release_control_lease(reason='done')

    assert authority['summary_state'] == 'ready'
    assert host._lease_id == ''
