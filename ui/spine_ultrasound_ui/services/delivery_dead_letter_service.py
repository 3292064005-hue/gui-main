from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass
class DeadLetterEntry:
    ack_id: str
    subscriber_id: str
    topic: str
    delivery: str
    reason: str
    attempts: int
    event_id: str
    message: dict[str, Any]
    ts_ns: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            'ack_id': self.ack_id,
            'subscriber_id': self.subscriber_id,
            'topic': self.topic,
            'delivery': self.delivery,
            'reason': self.reason,
            'attempts': self.attempts,
            'event_id': self.event_id,
            'message': self.message,
            'ts_ns': int(self.ts_ns),
        }


class DeliveryDeadLetterService:
    def __init__(self, max_entries: int = 256) -> None:
        self._entries: list[DeadLetterEntry] = []
        self._max_entries = max_entries

    def add(self, entry: DeadLetterEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

    def list_entries(self) -> list[dict[str, Any]]:
        return [entry.to_dict() for entry in self._entries]

    def stats(self) -> dict[str, Any]:
        by_reason = Counter(entry.reason for entry in self._entries)
        by_topic = Counter(entry.topic for entry in self._entries)
        return {
            'dead_letter_count': len(self._entries),
            'latest_event_id': self._entries[-1].event_id if self._entries else '',
            'latest_reason': self._entries[-1].reason if self._entries else '',
            'by_reason': dict(sorted(by_reason.items())),
            'by_topic': dict(sorted(by_topic.items())),
        }
