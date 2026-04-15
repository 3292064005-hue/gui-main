from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService
from spine_ultrasound_ui.services.backend_base import BackendBase
from spine_ultrasound_ui.services.backend_link_service import BackendLinkMetrics, BackendLinkService
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter
from spine_ultrasound_ui.services.mock_backend import MockBackend


class _AuthorityBackend(BackendBase):
    def resolve_authoritative_runtime_envelope(self) -> dict:
        return {
            'control_authority': {'summary_state': 'ready', 'owner': {'actor_id': 'runtime', 'workspace': 'runtime', 'role': 'runtime', 'session_id': ''}},
            'runtime_config_applied': {'pressure_target': 8.0},
            'final_verdict': {'accepted': True, 'source': 'cpp_robot_core'},
        }

    def resolve_final_verdict(self, plan=None, config: RuntimeConfig | None = None, *, read_only: bool) -> dict:
        return {'accepted': True, 'source': 'cpp_robot_core'}


def test_backend_base_control_authority_defaults_to_authoritative_envelope() -> None:
    backend = _AuthorityBackend()
    payload = backend.resolve_control_authority()
    assert payload['summary_state'] == 'ready'
    assert payload['owner']['actor_id'] == 'runtime'


def test_backend_link_snapshot_surfaces_top_level_authority_fields() -> None:
    snapshot = BackendLinkService().build_snapshot(
        mode='core',
        http_base='tls://127.0.0.1:5656',
        ws_base='tls://127.0.0.1:5657',
        status={'backend_mode': 'core'},
        health={'adapter_running': True, 'telemetry_stale': False, 'latest_telemetry_age_ms': 10},
        metrics=BackendLinkMetrics(rest_reachable=True, telemetry_connected=True),
        control_plane={'summary_label': '控制面一致'},
        authoritative_runtime_envelope={
            'control_authority': {'summary_state': 'ready'},
            'final_verdict': {'accepted': True, 'source': 'cpp_robot_core'},
        },
    )
    assert snapshot['authoritative_runtime_envelope']['control_authority']['summary_state'] == 'ready'
    assert snapshot['control_authority']['summary_state'] == 'ready'
    assert snapshot['final_verdict']['accepted'] is True


def test_mock_backend_exposes_canonical_authority_surface(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path)
    envelope = backend.resolve_authoritative_runtime_envelope()
    authority = backend.resolve_control_authority()
    verdict = backend.resolve_final_verdict(read_only=True)
    assert envelope['control_authority']['owner']['actor_id'] == authority['owner']['actor_id']
    assert verdict == envelope['final_verdict']
    assert envelope['authoritative_runtime_envelope_present'] is True
    assert envelope['synthesized'] is False


def test_authoritative_contract_service_strict_surface_accepts_only_runtime_published_envelopes() -> None:
    service = BackendAuthoritativeContractService()
    direct_payload = {
        'authority_source': 'cpp_robot_core',
        'control_authority': {
            'summary_state': 'ready',
            'owner': {'actor_id': 'runtime', 'workspace': 'runtime', 'role': 'runtime', 'session_id': ''},
        },
        'runtime_config_applied': {'pressure_target': 8.0},
        'final_verdict': {'accepted': True, 'source': 'cpp_robot_core'},
    }
    envelope = service.normalize_authoritative_runtime_envelope(
        direct_payload,
        authority_source='cpp_robot_core',
        desired_runtime_config=RuntimeConfig(),
        allow_direct_payload=True,
    )
    assert envelope['authoritative_runtime_envelope_present'] is True
    assert envelope['synthesized'] is False

    synthesized = service.normalize_authoritative_runtime_envelope(
        {
            'control_plane': {
                'control_authority': {
                    'summary_state': 'ready',
                    'owner': {'actor_id': 'tester', 'workspace': 'desktop', 'role': 'operator', 'session_id': ''},
                },
                'runtime_config': {'runtime_config': {'pressure_target': 8.0}},
            },
            'accepted': True,
        },
        authority_source='unit-test',
        desired_runtime_config=RuntimeConfig(),
        allow_direct_payload=False,
    )
    assert synthesized == {}


def test_headless_adapter_returns_explicit_unavailable_envelope_without_synthesis() -> None:
    adapter = HeadlessAdapter('mock', '127.0.0.1', 5656, '127.0.0.1', 5657)
    original_dispatch = adapter.command_service._dispatch.dispatch
    adapter.command_service._dispatch.dispatch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('boom'))
    envelope = adapter.resolve_authoritative_runtime_envelope()
    adapter.command_service._dispatch.dispatch = original_dispatch
    assert envelope['summary_state'] == 'degraded'
    assert envelope['synthesized'] is False
    assert envelope['control_authority'] == {}
    assert envelope['final_verdict'] == {}


def test_backend_authority_parity_script_exercises_runtime_behavior() -> None:
    source = Path('scripts/check_backend_authority_parity.py').read_text(encoding='utf-8')
    for required in (
        'HeadlessAdapter',
        'MockBackend',
        'RobotCoreClientBackend',
        'ApiBridgeBackend',
        'normalize_authoritative_runtime_envelope',
    ):
        assert required in source


def test_backend_link_snapshot_does_not_fallback_top_level_authority_fields() -> None:
    snapshot = BackendLinkService().build_snapshot(
        mode='api',
        http_base='http://127.0.0.1:8000',
        ws_base='ws://127.0.0.1:8000',
        status={'backend_mode': 'api'},
        health={'adapter_running': True, 'telemetry_stale': False, 'latest_telemetry_age_ms': 10},
        metrics=BackendLinkMetrics(rest_reachable=True, telemetry_connected=True),
        control_plane={
            'summary_label': '控制面一致',
            'control_authority': {'summary_state': 'ready', 'summary_label': 'projected'},
            'final_verdict': {'accepted': True, 'source': 'projection'},
        },
        authoritative_runtime_envelope={},
    )
    assert snapshot['authoritative_runtime_envelope'] == {}
    assert snapshot['control_authority'] == {}
    assert snapshot['final_verdict'] == {}
    assert snapshot['projected_control_authority']['summary_label'] == 'projected'
    assert snapshot['projected_final_verdict']['source'] == 'projection'
