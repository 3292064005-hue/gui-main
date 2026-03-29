from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeliveryRule:
    name: str
    latest_only: bool
    must_deliver: bool
    replay_persisted: bool
    queue_limit: int
    ack_timeout_ms: int
    max_retries: int
    backlog_warn_threshold: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "latest_only": self.latest_only,
            "must_deliver": self.must_deliver,
            "replay_persisted": self.replay_persisted,
            "queue_limit": self.queue_limit,
            "ack_timeout_ms": self.ack_timeout_ms,
            "max_retries": self.max_retries,
            "backlog_warn_threshold": self.backlog_warn_threshold,
        }


class DeliveryPolicy:
    DEFAULTS = {
        "telemetry": DeliveryRule(
            "telemetry",
            latest_only=True,
            must_deliver=False,
            replay_persisted=False,
            queue_limit=256,
            ack_timeout_ms=0,
            max_retries=0,
            backlog_warn_threshold=64,
        ),
        "event": DeliveryRule(
            "event",
            latest_only=False,
            must_deliver=True,
            replay_persisted=True,
            queue_limit=512,
            ack_timeout_ms=1500,
            max_retries=2,
            backlog_warn_threshold=96,
        ),
        "must_deliver": DeliveryRule(
            "must_deliver",
            latest_only=False,
            must_deliver=True,
            replay_persisted=True,
            queue_limit=1024,
            ack_timeout_ms=2500,
            max_retries=4,
            backlog_warn_threshold=128,
        ),
        "persisted": DeliveryRule(
            "persisted",
            latest_only=False,
            must_deliver=False,
            replay_persisted=True,
            queue_limit=1024,
            ack_timeout_ms=0,
            max_retries=0,
            backlog_warn_threshold=128,
        ),
    }

    def rule_for(self, delivery: str) -> DeliveryRule:
        return self.DEFAULTS.get(delivery, self.DEFAULTS["event"])
