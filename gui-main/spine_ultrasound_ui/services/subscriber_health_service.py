from __future__ import annotations

from collections import Counter
from typing import Any


class SubscriberHealthService:
    def summarize(self, subscribers: list[Any]) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for subscription in subscribers:
            queue_depth = subscription.queue.qsize() if hasattr(subscription, 'queue') else 0
            payload.append(
                {
                    'subscriber_id': subscription.subscriber_id,
                    'subscriber_name': subscription.subscriber_name or subscription.subscriber_id,
                    'topics': sorted(subscription.topics) if subscription.topics else ['*'],
                    'categories': sorted(subscription.categories) if subscription.categories else ['*'],
                    'deliveries': sorted(subscription.deliveries) if subscription.deliveries else ['*'],
                    'delivered': subscription.delivered,
                    'matched': subscription.matched,
                    'dropped': subscription.dropped,
                    'acked': subscription.acked,
                    'retries': subscription.retry_count,
                    'failed_delivery_count': subscription.failed_delivery_count,
                    'max_depth': subscription.max_depth,
                    'queue_depth': queue_depth,
                    'health_state': subscription.health_state,
                }
            )
        return payload

    def stats(self, subscribers: list[Any]) -> dict[str, Any]:
        summary = self.summarize(subscribers)
        by_state = Counter(str(item.get('health_state', 'unknown')) for item in summary)
        return {
            'subscriber_count': len(summary),
            'by_state': dict(sorted(by_state.items())),
            'slow_count': sum(1 for item in summary if str(item.get('health_state')) in {'slow', 'quarantined'}),
            'failed_count': sum(1 for item in summary if str(item.get('health_state')) == 'failed'),
            'details': summary,
        }
