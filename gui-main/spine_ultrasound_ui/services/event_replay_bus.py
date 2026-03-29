from __future__ import annotations

from collections import Counter, deque
from typing import Any

from spine_ultrasound_ui.services.event_envelope import EventEnvelope


class EventReplayBus:
    def __init__(self, max_events: int = 1024) -> None:
        self._events: deque[EventEnvelope] = deque(maxlen=max_events)

    def append(self, envelope: EventEnvelope) -> None:
        self._events.append(envelope)

    def _filtered_messages(
        self,
        topics: set[str] | None = None,
        *,
        session_id: str | None = None,
        since_ts_ns: int | None = None,
        until_ts_ns: int | None = None,
        delivery: str | None = None,
        category: str | None = None,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        messages = []
        cursor_active = cursor is None
        for event in self._events:
            if not cursor_active:
                cursor_active = event.event_id == cursor
                continue
            if topics is not None and event.topic not in topics:
                continue
            if session_id and event.session_id != session_id:
                continue
            if delivery and event.delivery != delivery:
                continue
            if category and event.category != category:
                continue
            if since_ts_ns is not None and int(event.ts_ns) < int(since_ts_ns):
                continue
            if until_ts_ns is not None and int(event.ts_ns) > int(until_ts_ns):
                continue
            messages.append(event.to_message())
        return messages

    def replay(
        self,
        topics: set[str] | None = None,
        *,
        limit: int | None = None,
        session_id: str | None = None,
        since_ts_ns: int | None = None,
        until_ts_ns: int | None = None,
        delivery: str | None = None,
        category: str | None = None,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        messages = self._filtered_messages(
            topics,
            session_id=session_id,
            since_ts_ns=since_ts_ns,
            until_ts_ns=until_ts_ns,
            delivery=delivery,
            category=category,
            cursor=cursor,
        )
        if limit is not None:
            messages = messages[-limit:]
        return messages

    def replay_page(
        self,
        topics: set[str] | None = None,
        *,
        page_size: int = 100,
        session_id: str | None = None,
        since_ts_ns: int | None = None,
        until_ts_ns: int | None = None,
        delivery: str | None = None,
        category: str | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        messages = self._filtered_messages(
            topics,
            session_id=session_id,
            since_ts_ns=since_ts_ns,
            until_ts_ns=until_ts_ns,
            delivery=delivery,
            category=category,
            cursor=cursor,
        )
        page = messages[: max(1, page_size)]
        next_cursor = page[-1]["event_id"] if len(messages) > len(page) and page else None
        return {
            "events": page,
            "next_cursor": next_cursor,
            "summary": {
                "count": len(page),
                "page_size": max(1, page_size),
                "remaining": max(0, len(messages) - len(page)),
            },
        }

    def stats(self) -> dict[str, Any]:
        delivery_counts = Counter(event.delivery for event in self._events)
        category_counts = Counter(event.category for event in self._events)
        topic_counts = Counter(event.topic for event in self._events)
        return {
            "buffered_events": len(self._events),
            "topics": sorted(topic_counts),
            "topic_counts": dict(sorted(topic_counts.items())),
            "delivery_counts": dict(sorted(delivery_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
            "session_ids": sorted({event.session_id for event in self._events if event.session_id}),
            "latest_event_id": self._events[-1].event_id if self._events else "",
        }
