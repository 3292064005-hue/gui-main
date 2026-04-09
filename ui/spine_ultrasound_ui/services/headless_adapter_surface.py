from __future__ import annotations

from typing import Any, Iterator

from spine_ultrasound_ui.services.headless_control_plane_status_service import HeadlessControlPlaneStatusService
from spine_ultrasound_ui.services.headless_event_surface_service import HeadlessEventSurfaceService
from spine_ultrasound_ui.services.headless_frame_surface_service import HeadlessFrameSurfaceService


class HeadlessAdapterSurface:
    """Thin façade over headless runtime support services.

    Responsibilities are intentionally split across dedicated helpers so the
    surface remains inspectable and new responsibilities do not accrete into a
    single god-object.
    """

    def __init__(self, adapter) -> None:
        self.adapter = adapter
        self._control_plane_status = HeadlessControlPlaneStatusService(adapter)
        self._events = HeadlessEventSurfaceService(adapter)
        self._frames = HeadlessFrameSurfaceService()

    def snapshot(self, topics: set[str] | None = None) -> list[dict[str, Any]]:
        payloads = self.adapter.telemetry_cache.snapshot(topics)
        for product_update in self._events.session_product_update_envelopes():
            if topics is None or product_update['topic'] in topics:
                payloads.append(product_update)
        return payloads

    def control_plane_status(self) -> dict[str, Any]:
        return self._control_plane_status.build()

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
        return self._frames.frame_base64(mode='camera', phase=self.adapter.phase)

    def ultrasound_frame(self) -> str:
        self.adapter.phase += 0.1
        return self._frames.frame_base64(mode='ultrasound', phase=self.adapter.phase)

    def publish_session_product_updates(self) -> None:
        self._events.publish_session_product_updates()

    def publish_event(self, item: dict[str, Any]) -> None:
        self._events.publish_event(item)

    def store_message(self, env) -> None:
        self._events.store_message(env)

    def store_messages(self, messages) -> None:
        self._events.store_messages(messages)

    def mock_loop(self) -> None:
        self._events.mock_loop()

    def core_loop(self) -> None:
        self._events.core_loop()

