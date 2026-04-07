from __future__ import annotations

import base64
import socket
import time
from contextlib import suppress
from typing import Any, Iterator

try:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QGuiApplication
except ImportError:  # pragma: no cover
    QBuffer = QByteArray = QIODevice = QGuiApplication = None  # type: ignore

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.core_transport import parse_telemetry_payload
from spine_ultrasound_ui.services.ipc_protocol import TelemetryEnvelope
from spine_ultrasound_ui.services.protobuf_transport import DEFAULT_TLS_SERVER_NAME, recv_length_prefixed_message


def _ensure_qt_app() -> bool:
    if QGuiApplication is None:
        return False
    app = QGuiApplication.instance()
    if app is None:
        QGuiApplication([])
    return True


def _static_png_base64() -> str:
    return 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Ww2cQAAAABJRU5ErkJggg=='


def _pixmap_to_base64(mode: str, phase: float) -> str:
    if not _ensure_qt_app() or QBuffer is None or QByteArray is None or QIODevice is None:
        return _static_png_base64()
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QColor, QPainter, QPixmap

    pixmap = QPixmap(640, 360)
    pixmap.fill(QColor('#0F172A' if mode == 'camera' else '#111827'))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor('#38BDF8' if mode == 'camera' else '#A78BFA'))
    x = 40 + int((phase % 6.0) * 80)
    painter.drawRoundedRect(QRectF(x, 120, 180, 96), 22, 22)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, 'PNG')
    return base64.b64encode(bytes(data)).decode('ascii')


class HeadlessAdapterSurface:
    def __init__(self, adapter) -> None:
        self.adapter = adapter

    def snapshot(self, topics: set[str] | None = None) -> list[dict[str, Any]]:
        payloads = self.adapter.telemetry_cache.snapshot(topics)
        for product_update in self._session_product_update_envelopes():
            if topics is None or product_update['topic'] in topics:
                payloads.append(product_update)
        return payloads

    def control_plane_status(self) -> dict[str, Any]:
        adapter = self.adapter
        status = adapter.status()
        health = adapter.health()
        schema = adapter.schema()
        runtime_config = adapter.runtime_config()
        topics = adapter.topic_catalog()
        recent_commands = adapter.recent_commands().get('recent_commands', [])
        control_authority = adapter.control_authority_status()
        session_governance = {
            'summary_state': 'idle',
            'summary_label': '未锁定会话',
            'detail': 'no_active_session',
            'session_locked': False,
            'session_id': adapter._current_session_id,
        }
        evidence_seal: dict[str, Any] = {}
        if adapter._current_session_dir is not None:
            session_governance = {
                'summary_state': 'ready',
                'summary_label': '会话已锁定',
                'detail': str(adapter._current_session_dir),
                'session_locked': True,
                'session_id': adapter._current_session_id,
            }
            with suppress(Exception):
                evidence_seal = adapter.current_evidence_seal()
        summary = adapter.control_plane_aggregator.build(
            local_config=RuntimeConfig.from_dict(
                dict(runtime_config.get('runtime_config', {})) or adapter.runtime_config_snapshot_data or RuntimeConfig().to_dict()
            ),
            runtime_config=runtime_config,
            schema=schema,
            status=status,
            health=health,
            topic_catalog=topics,
            recent_commands=recent_commands,
            control_authority=control_authority,
            session_governance=session_governance,
            evidence_seal=evidence_seal,
        )
        return {
            **summary,
            'status': status,
            'health': health,
            'schema': schema,
            'runtime_config': runtime_config,
            'topics': topics,
            'recent_commands': {'recent_commands': recent_commands},
            'control_authority': control_authority,
            'control_plane_snapshot': summary.get('control_plane_snapshot', {}),
        }

    def replay_events(
        self,
        *,
        topics: set[str] | None = None,
        session_id: str | None = None,
        since_ts_ns: int | None = None,
        until_ts_ns: int | None = None,
        delivery: str | None = None,
        category: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        resolved_page_size = max(1, int(page_size or limit or 100))
        payload = self.adapter.event_bus.replay_page(
            topics,
            page_size=resolved_page_size,
            session_id=session_id,
            since_ts_ns=since_ts_ns,
            until_ts_ns=until_ts_ns,
            delivery=delivery,
            category=category,
            cursor=cursor,
        )
        payload['session_id'] = session_id or self.adapter._current_session_id
        return payload

    def subscribe(self, topics: set[str] | None = None, *, include_snapshot: bool = True, categories: set[str] | None = None, deliveries: set[str] | None = None):
        subscription = self.adapter.event_bus.subscribe(topics, categories=categories, deliveries=deliveries, subscriber_name='websocket_feed')
        if include_snapshot:
            for item in self.snapshot(topics):
                subscription.push(item)
        return subscription

    def unsubscribe(self, subscription) -> None:
        self.adapter.event_bus.unsubscribe(subscription)

    def iter_events(self, topics: set[str] | None = None) -> Iterator[dict[str, Any]]:
        subscription = self.subscribe(topics)
        try:
            while not self.adapter._stop.is_set() and not subscription.closed:
                item = subscription.get(timeout=1.0)
                if item is None:
                    break
                yield item
        finally:
            self.unsubscribe(subscription)

    def camera_frame(self) -> str:
        self.adapter.phase += 0.1
        return _pixmap_to_base64('camera', self.adapter.phase)

    def ultrasound_frame(self) -> str:
        self.adapter.phase += 0.1
        return _pixmap_to_base64('ultrasound', self.adapter.phase)

    def publish_session_product_updates(self) -> None:
        for event in self._session_product_update_envelopes():
            self.publish_event(event)

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
            except OSError:
                if not self.adapter._stop.is_set():
                    time.sleep(1.0)
            except Exception:
                if self.adapter._stop.is_set():
                    break
                time.sleep(1.0)

    def _session_product_update_envelopes(self) -> list[dict[str, Any]]:
        session_dir = self.adapter._resolve_session_dir()
        manifest = self.adapter._read_manifest_if_available(session_dir)
        session_id = manifest.get('session_id', self.adapter._current_session_id or (session_dir.name if session_dir else ''))
        return self.adapter.session_watcher.poll(session_dir, session_id=session_id)
