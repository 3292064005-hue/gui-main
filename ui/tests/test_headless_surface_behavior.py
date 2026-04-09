from __future__ import annotations

from types import SimpleNamespace

from spine_ultrasound_ui.services.headless_adapter_surface import HeadlessAdapterSurface
from spine_ultrasound_ui.services.headless_control_plane_status_service import HeadlessControlPlaneStatusService


class _FakeTelemetryCache:
    def snapshot(self, topics=None):
        return [{'topic': 'core_state', 'value': 1}]


class _FakeStop:
    def is_set(self) -> bool:
        return False


class _FakeEventService:
    def __init__(self) -> None:
        self.updates = [{'topic': 'session_product_update', 'value': 2}]
        self.published = []
        self.mock_loop_called = False
        self.core_loop_called = False

    def session_product_update_envelopes(self):
        return list(self.updates)

    def publish_session_product_updates(self) -> None:
        self.published.extend(self.updates)

    def publish_event(self, item):
        self.published.append(item)

    def store_message(self, env):
        self.published.append(('store', env))

    def store_messages(self, messages):
        self.published.append(('store_many', list(messages)))

    def mock_loop(self) -> None:
        self.mock_loop_called = True

    def core_loop(self) -> None:
        self.core_loop_called = True


class _FakeControlPlane:
    def build(self):
        return {'summary_state': 'ready', 'summary_label': 'ok'}


class _FakeFrameService:
    def frame_base64(self, *, mode: str, phase: float) -> str:
        return f'{mode}:{phase:.1f}'


class _FakeAdapter:
    def __init__(self) -> None:
        self.telemetry_cache = _FakeTelemetryCache()
        self.event_bus = SimpleNamespace()
        self._stop = _FakeStop()
        self.phase = 0.0


class _Aggregator:
    def build(self, **kwargs):
        return {'summary_state': 'ready', 'control_plane_snapshot': {'session_id': kwargs['session_governance']['session_id']}}


class _ControlPlaneAdapter:
    def __init__(self, session_dir=True, evidence_error: Exception | None = None) -> None:
        self._current_session_id = 'S-1'
        self._current_session_dir = '/tmp/session' if session_dir else None
        self._evidence_error = evidence_error
        self.runtime_config_snapshot_data = {}
        self.control_plane_aggregator = _Aggregator()

    def status(self):
        return {'execution_state': 'AUTO_READY'}

    def health(self):
        return {'adapter_running': True}

    def schema(self):
        return {'protocol_version': 1}

    def runtime_config(self):
        return {'runtime_config': {}}

    def topic_catalog(self):
        return {'topics': []}

    def recent_commands(self):
        return {'recent_commands': []}

    def control_authority_status(self):
        return {'summary_state': 'ready'}

    def current_evidence_seal(self):
        if self._evidence_error is not None:
            raise self._evidence_error
        return {'seal': 'ok'}


def test_headless_adapter_surface_snapshot_includes_session_updates() -> None:
    adapter = _FakeAdapter()
    surface = HeadlessAdapterSurface(adapter)
    surface._events = _FakeEventService()
    surface._control_plane_status = _FakeControlPlane()
    surface._frames = _FakeFrameService()

    snapshot = surface.snapshot()
    assert [item['topic'] for item in snapshot] == ['core_state', 'session_product_update']
    assert surface.control_plane_status()['summary_state'] == 'ready'
    assert surface.camera_frame() == 'camera:0.1'
    assert surface.ultrasound_frame() == 'ultrasound:0.2'


def test_headless_adapter_surface_delegates_event_loops() -> None:
    adapter = _FakeAdapter()
    surface = HeadlessAdapterSurface(adapter)
    events = _FakeEventService()
    surface._events = events
    surface.publish_session_product_updates()
    surface.mock_loop()
    surface.core_loop()
    assert events.published == [{'topic': 'session_product_update', 'value': 2}]
    assert events.mock_loop_called is True
    assert events.core_loop_called is True


def test_control_plane_status_service_handles_expected_evidence_errors() -> None:
    adapter = _ControlPlaneAdapter(evidence_error=ValueError('bad evidence payload'))
    result = HeadlessControlPlaneStatusService(adapter).build()
    assert result['summary_state'] == 'ready'
    assert result['control_plane_snapshot']['session_id'] == 'S-1'
    assert result['control_authority']['summary_state'] == 'ready'
