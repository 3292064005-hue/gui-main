from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.services.backend_errors import normalize_backend_exception
from spine_ultrasound_ui.services.core_transport import parse_telemetry_payload
from spine_ultrasound_ui.services.ipc_protocol import TelemetryEnvelope
from spine_ultrasound_ui.services.protobuf_transport import DEFAULT_TLS_SERVER_NAME, recv_length_prefixed_message

import socket
import time


class HeadlessEventSurfaceService:
    """Own telemetry cache writes, event publication, and core-loop fault envelopes."""

    def __init__(self, adapter) -> None:
        self.adapter = adapter

    def publish_session_product_updates(self) -> None:
        for event in self.session_product_update_envelopes():
            self.publish_event(event)

    def session_product_update_envelopes(self) -> list[dict[str, Any]]:
        """Return the current authoritative session-product update envelopes.

        This is the only supported read surface for derived session product events.
        Callers must not reach into private helper methods from outside the service.
        """
        return self._session_product_update_envelopes()

    def publish_event(self, item: dict[str, Any]) -> None:
        topic = str(item.get('topic', ''))
        category = 'session' if topic.endswith('_updated') or topic in {'artifact_ready', 'session_product_update'} else str(item.get('category', 'runtime'))
        delivery = 'event' if category == 'session' else str(item.get('delivery', 'telemetry'))
        self.adapter.topic_registry.ensure(topic, category=category, delivery=delivery)
        self.adapter.event_bus.publish(item, category=category, delivery=delivery)

    def store_message(self, env: TelemetryEnvelope) -> None:
        payload = self.adapter.telemetry_cache.store(env)
        self.adapter.topic_registry.ensure(env.topic, category='runtime', delivery='telemetry')
        self.adapter.event_bus.publish(
            env.topic,
            {k: v for k, v in payload.items() if k != '_ts_ns'},
            ts_ns=payload['_ts_ns'],
            session_id=str(payload.get('session_id', self.adapter._current_session_id)),
            category='runtime',
            delivery='telemetry',
            source='robot_core' if self.adapter.mode == 'core' else 'mock_core',
        )

    def store_messages(self, messages: list[TelemetryEnvelope]) -> None:
        for env in messages:
            self.store_message(env)

    def mock_loop(self) -> None:
        assert self.adapter.runtime is not None
        while not self.adapter._stop.is_set():
            self.store_messages(self.adapter.runtime.tick())
            self.publish_session_product_updates()
            time.sleep(0.1)

    def core_loop(self) -> None:
        while not self.adapter._stop.is_set():
            try:
                with socket.create_connection((self.adapter.telemetry_host, self.adapter.telemetry_port), timeout=1.0) as raw_sock:
                    raw_sock.settimeout(2.0)
                    assert self.adapter.ssl_context is not None
                    with self.adapter.ssl_context.wrap_socket(raw_sock, server_hostname=DEFAULT_TLS_SERVER_NAME) as tls_sock:
                        while not self.adapter._stop.is_set():
                            message_bytes = recv_length_prefixed_message(tls_sock)
                            self.store_message(parse_telemetry_payload(message_bytes))
                            self.publish_session_product_updates()
            except Exception as exc:
                normalized = normalize_backend_exception(exc, context='headless_core_loop')
                if self.adapter._stop.is_set():
                    break
                self.publish_event({
                    'topic': 'runtime.surface_fault',
                    'category': 'runtime',
                    'delivery': 'event',
                    'error_type': normalized.error_type,
                    'message': normalized.message,
                    'retryable': normalized.retryable,
                    'http_status': normalized.http_status,
                })
                time.sleep(1.0)

    def _session_product_update_envelopes(self) -> list[dict[str, Any]]:
        session_dir = self.adapter._resolve_session_dir()
        manifest = self.adapter._read_manifest_if_available(session_dir)
        session_id = manifest.get('session_id', self.adapter._current_session_id or (session_dir.name if session_dir else ''))
        return self.adapter.session_watcher.poll(session_dir, session_id=session_id)
