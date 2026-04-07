from __future__ import annotations

import queue
import threading
from contextlib import suppress
from dataclasses import dataclass, field
from time import monotonic_ns
from typing import Any
from uuid import uuid4

from spine_ultrasound_ui.services.delivery_policy import DeliveryPolicy
from spine_ultrasound_ui.services.delivery_dead_letter_service import DeliveryDeadLetterService, DeadLetterEntry
from spine_ultrasound_ui.services.event_envelope import EventEnvelope
from spine_ultrasound_ui.services.event_replay_bus import EventReplayBus
from spine_ultrasound_ui.services.subscriber_health_service import SubscriberHealthService


@dataclass(eq=False)
class EventSubscription:
    topics: set[str] | None = None
    categories: set[str] | None = None
    deliveries: set[str] | None = None
    latest_only: bool = True
    queue_limit: int = 256
    subscriber_name: str = ""
    ack_required: bool = False
    subscriber_id: str = field(default_factory=lambda: uuid4().hex)
    delivered: int = 0
    matched: int = 0
    dropped: int = 0
    max_depth: int = 0
    acked: int = 0
    retry_count: int = 0
    failed_delivery_count: int = 0
    health_state: str = "healthy"
    last_item: dict[str, Any] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.queue: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=self.queue_limit)
        self.closed = False

    def matches(self, item: dict[str, Any]) -> bool:
        topic = str(item.get("topic", ""))
        category = str(item.get("category", ""))
        delivery = str(item.get("delivery", ""))
        return (
            (self.topics is None or topic in self.topics)
            and (self.categories is None or category in self.categories)
            and (self.deliveries is None or delivery in self.deliveries)
        )

    def push(self, item: dict[str, Any]) -> bool:
        if self.closed or not self.matches(item):
            return False
        self.matched += 1
        self.last_item = item
        try:
            self.queue.put_nowait(item)
            self.delivered += 1
            self.max_depth = max(self.max_depth, self.queue.qsize())
            self._refresh_health()
            return True
        except queue.Full:
            self.dropped += 1
            if self.latest_only:
                with suppress(queue.Empty):
                    self.queue.get_nowait()
                with suppress(queue.Full):
                    self.queue.put_nowait(item)
                    self.delivered += 1
                    self.max_depth = max(self.max_depth, self.queue.qsize())
                    self._refresh_health()
                    return True
            self._refresh_health()
            return False

    def get(self, timeout: float = 1.0) -> dict[str, Any] | None:
        return self.queue.get(timeout=timeout)

    def close(self) -> None:
        self.closed = True
        with suppress(queue.Full):
            self.queue.put_nowait(None)

    def _refresh_health(self) -> None:
        if self.failed_delivery_count > 2:
            self.health_state = "failed"
        elif self.failed_delivery_count > 0:
            self.health_state = "quarantined"
        elif self.dropped > 0 or self.max_depth >= int(self.queue_limit * 0.75):
            self.health_state = "slow"
        else:
            self.health_state = "healthy"


@dataclass
class PendingAck:
    ack_id: str
    subscriber_id: str
    topic: str
    delivery: str
    message: dict[str, Any]
    deadline_ns: int
    attempts: int = 0
    acked: bool = False
    failed: bool = False


class EventBus:
    def __init__(self, replay_bus: EventReplayBus | None = None, delivery_policy: DeliveryPolicy | None = None) -> None:
        self._lock = threading.Lock()
        self._subscribers: set[EventSubscription] = set()
        self._published = 0
        self._published_by_topic: dict[str, int] = {}
        self._published_by_delivery: dict[str, int] = {}
        self._published_by_category: dict[str, int] = {}
        self._pending_acks: dict[str, PendingAck] = {}
        self._delivery_failures = 0
        self._delivery_retries = 0
        self._delivery_dead_letters = DeliveryDeadLetterService()
        self._subscriber_health = SubscriberHealthService()
        self._replay_bus = replay_bus or EventReplayBus()
        self._delivery_policy = delivery_policy or DeliveryPolicy()

    def subscribe(self, topics: set[str] | None = None, *, categories: set[str] | None = None, deliveries: set[str] | None = None, latest_only: bool | None = None, queue_limit: int | None = None, subscriber_name: str = "", ack_required: bool = False) -> EventSubscription:
        resolved_latest = True if latest_only is None else latest_only
        resolved_queue = 256 if queue_limit is None else queue_limit
        if deliveries and len(deliveries) == 1:
            rule = self._delivery_policy.rule_for(next(iter(deliveries)))
            if latest_only is None:
                resolved_latest = rule.latest_only
            if queue_limit is None:
                resolved_queue = rule.queue_limit
        subscription = EventSubscription(set(topics or []) or None, set(categories or []) or None, set(deliveries or []) or None, latest_only=resolved_latest, queue_limit=resolved_queue, subscriber_name=subscriber_name, ack_required=ack_required)
        with self._lock:
            self._subscribers.add(subscription)
        return subscription

    def unsubscribe(self, subscription: EventSubscription) -> None:
        with self._lock:
            self._subscribers.discard(subscription)
            for ack_id, pending in list(self._pending_acks.items()):
                if pending.subscriber_id == subscription.subscriber_id and not pending.acked:
                    pending.failed = True
                    self._delivery_failures += 1
                    self._delivery_dead_letters.add(DeadLetterEntry(ack_id=pending.ack_id, subscriber_id=pending.subscriber_id, topic=pending.topic, delivery=pending.delivery, reason="unsubscribe", attempts=pending.attempts, event_id=str(pending.message.get("event_id", "")), message=dict(pending.message), ts_ns=monotonic_ns()))
                    del self._pending_acks[ack_id]
        subscription.close()

    def publish(self, item: dict[str, Any] | str, data: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        requested_delivery = str(kwargs.get("delivery", ""))
        if requested_delivery:
            rule = self._delivery_policy.rule_for(requested_delivery)
            kwargs.setdefault("delivery", rule.name)
        envelope = EventEnvelope.from_any(item, payload=data, **kwargs)
        rule = self._delivery_policy.rule_for(envelope.delivery)
        envelope.delivery = rule.name
        message = envelope.to_message()
        with self._lock:
            subscribers = list(self._subscribers)
            self._published += 1
            self._published_by_topic[envelope.topic] = self._published_by_topic.get(envelope.topic, 0) + 1
            self._published_by_delivery[envelope.delivery] = self._published_by_delivery.get(envelope.delivery, 0) + 1
            self._published_by_category[envelope.category] = self._published_by_category.get(envelope.category, 0) + 1
        self._replay_bus.append(envelope)
        now = monotonic_ns()
        for subscription in subscribers:
            if not subscription.matches(message):
                continue
            delivery_message = dict(message)
            if rule.must_deliver and subscription.ack_required:
                ack_id = uuid4().hex
                delivery_message["ack_id"] = ack_id
            else:
                ack_id = ""
            enqueued = subscription.push(delivery_message)
            if rule.must_deliver and subscription.ack_required:
                if enqueued:
                    pending = PendingAck(ack_id=ack_id, subscriber_id=subscription.subscriber_id, topic=envelope.topic, delivery=envelope.delivery, message=delivery_message, deadline_ns=now + (rule.ack_timeout_ms * 1_000_000))
                    with self._lock:
                        self._pending_acks[ack_id] = pending
                else:
                    subscription.failed_delivery_count += 1
                    subscription._refresh_health()
                    with self._lock:
                        self._delivery_failures += 1
                    self._delivery_dead_letters.add(DeadLetterEntry(ack_id=ack_id, subscriber_id=subscription.subscriber_id, topic=envelope.topic, delivery=envelope.delivery, reason="enqueue_failed", attempts=0, event_id=envelope.event_id, message=dict(delivery_message), ts_ns=monotonic_ns()))
        return message

    def ack(self, subscription: EventSubscription | str, ack: dict[str, Any] | str) -> bool:
        subscriber_id = subscription if isinstance(subscription, str) else subscription.subscriber_id
        ack_id = ack.get("ack_id", "") if isinstance(ack, dict) else str(ack)
        if not ack_id:
            return False
        with self._lock:
            pending = self._pending_acks.get(ack_id)
            if pending is None or pending.subscriber_id != subscriber_id:
                return False
            pending.acked = True
            del self._pending_acks[ack_id]
        if not isinstance(subscription, str):
            subscription.acked += 1
            subscription._refresh_health()
        return True

    def retry_pending(self, now_ns: int | None = None) -> dict[str, Any]:
        current = monotonic_ns() if now_ns is None else int(now_ns)
        retried = 0
        failed = 0
        with self._lock:
            subscribers_by_id = {item.subscriber_id: item for item in self._subscribers}
            pending_items = list(self._pending_acks.items())
        for ack_id, pending in pending_items:
            if pending.acked or pending.deadline_ns > current:
                continue
            subscription = subscribers_by_id.get(pending.subscriber_id)
            rule = self._delivery_policy.rule_for(pending.delivery)
            if subscription is None or subscription.closed:
                with self._lock:
                    self._pending_acks.pop(ack_id, None)
                    self._delivery_failures += 1
                self._delivery_dead_letters.add(DeadLetterEntry(ack_id=pending.ack_id, subscriber_id=pending.subscriber_id, topic=pending.topic, delivery=pending.delivery, reason="subscriber_missing", attempts=pending.attempts, event_id=str(pending.message.get("event_id", "")), message=dict(pending.message), ts_ns=current))
                failed += 1
                continue
            if pending.attempts >= rule.max_retries:
                subscription.failed_delivery_count += 1
                subscription.health_state = "quarantined"
                subscription._refresh_health()
                with self._lock:
                    self._pending_acks.pop(ack_id, None)
                    self._delivery_failures += 1
                self._delivery_dead_letters.add(DeadLetterEntry(ack_id=pending.ack_id, subscriber_id=pending.subscriber_id, topic=pending.topic, delivery=pending.delivery, reason="retry_exhausted", attempts=pending.attempts, event_id=str(pending.message.get("event_id", "")), message=dict(pending.message), ts_ns=current))
                failed += 1
                continue
            pending.attempts += 1
            pending.deadline_ns = current + (rule.ack_timeout_ms * 1_000_000)
            if subscription.push(dict(pending.message)):
                subscription.retry_count += 1
                subscription._refresh_health()
                with self._lock:
                    self._delivery_retries += 1
                retried += 1
            else:
                subscription.failed_delivery_count += 1
                subscription.health_state = "quarantined" if subscription.failed_delivery_count > 1 else subscription.health_state
                subscription._refresh_health()
                with self._lock:
                    self._pending_acks.pop(ack_id, None)
                    self._delivery_failures += 1
                self._delivery_dead_letters.add(DeadLetterEntry(ack_id=pending.ack_id, subscriber_id=pending.subscriber_id, topic=pending.topic, delivery=pending.delivery, reason="retry_enqueue_failed", attempts=pending.attempts, event_id=str(pending.message.get("event_id", "")), message=dict(pending.message), ts_ns=current))
                failed += 1
        return {"retried": retried, "failed": failed, "pending": len(self.pending_acks())}

    def pending_acks(self) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._pending_acks.values())
        return [{"ack_id": item.ack_id, "subscriber_id": item.subscriber_id, "topic": item.topic, "delivery": item.delivery, "attempts": item.attempts, "deadline_ns": item.deadline_ns} for item in items]

    def dead_letters(self) -> dict[str, Any]:
        with self._lock:
            subscribers = list(self._subscribers)
            pending_count = len(self._pending_acks)
        return {
            'entries': self._delivery_dead_letters.list_entries(),
            'summary': self._delivery_dead_letters.stats(),
            'subscriber_health': self._subscriber_health.stats(subscribers),
            'pending_ack_count': pending_count,
        }

    def delivery_audit(self) -> dict[str, Any]:
        with self._lock:
            subscribers = list(self._subscribers)
            pending = list(self._pending_acks.values())
        return {
            'generated_at_ns': monotonic_ns(),
            'delivery_rules': {name: rule.to_dict() for name, rule in self._delivery_policy.DEFAULTS.items()},
            'pending_acks': [{'ack_id': item.ack_id, 'subscriber_id': item.subscriber_id, 'topic': item.topic, 'delivery': item.delivery, 'attempts': item.attempts, 'deadline_ns': item.deadline_ns} for item in pending],
            'dead_letters': self.dead_letters(),
            'subscriber_health': self._subscriber_health.stats(subscribers),
            'replay': self._replay_bus.stats(),
        }

    def replay(self, topics: set[str] | None = None, *, limit: int | None = None, session_id: str | None = None, since_ts_ns: int | None = None, until_ts_ns: int | None = None, delivery: str | None = None, category: str | None = None, cursor: str | None = None) -> list[dict[str, Any]]:
        return self._replay_bus.replay(topics, limit=limit, session_id=session_id, since_ts_ns=since_ts_ns, until_ts_ns=until_ts_ns, delivery=delivery, category=category, cursor=cursor)

    def replay_page(self, topics: set[str] | None = None, *, page_size: int = 100, session_id: str | None = None, since_ts_ns: int | None = None, until_ts_ns: int | None = None, delivery: str | None = None, category: str | None = None, cursor: str | None = None) -> dict[str, Any]:
        return self._replay_bus.replay_page(topics, page_size=page_size, session_id=session_id, since_ts_ns=since_ts_ns, until_ts_ns=until_ts_ns, delivery=delivery, category=category, cursor=cursor)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            subscribers = list(self._subscribers)
            published = self._published
            by_topic = dict(self._published_by_topic)
            by_delivery = dict(self._published_by_delivery)
            by_category = dict(self._published_by_category)
            pending_count = len(self._pending_acks)
            failures = self._delivery_failures
            retries = self._delivery_retries
        return {
            'published_events': published,
            'subscriber_count': len(subscribers),
            'dropped_events': sum(subscription.dropped for subscription in subscribers),
            'slow_subscribers': sum(1 for subscription in subscribers if subscription.dropped > 0 or subscription.health_state != 'healthy'),
            'max_queue_depth': max((subscription.max_depth for subscription in subscribers), default=0),
            'pending_ack_count': pending_count,
            'delivery_failures': failures,
            'delivery_retries': retries,
            'published_by_topic': dict(sorted(by_topic.items())),
            'published_by_delivery': dict(sorted(by_delivery.items())),
            'published_by_category': dict(sorted(by_category.items())),
            'subscriber_health': self._subscriber_health.stats(subscribers),
            'dead_letters': self._delivery_dead_letters.stats(),
            'replay': self._replay_bus.stats(),
        }

    def close(self) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
            self._subscribers.clear()
            self._pending_acks.clear()
        for subscription in subscribers:
            subscription.close()
