from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from spine_ultrasound_ui.utils import now_text


class EventLogIndexer:
    def build(self, *, session_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
        normalized = sorted((dict(event) for event in events), key=lambda item: int(item.get("ts_ns", 0) or 0))
        topics = sorted({str(item.get("topic", "unknown")) for item in normalized})
        first_ts = int(normalized[0].get("ts_ns", 0) or 0) if normalized else 0
        last_ts = int(normalized[-1].get("ts_ns", 0) or 0) if normalized else 0
        continuity_gaps = []
        previous_ts = 0
        by_topic_counter: Counter[str] = Counter()
        by_kind_counter: Counter[str] = Counter()
        by_topic_gaps: dict[str, list[dict[str, Any]]] = defaultdict(list)
        previous_by_topic: dict[str, int] = {}
        request_ids: set[str] = set()
        correlation_ids: set[str] = set()
        for index, event in enumerate(normalized, start=1):
            current_ts = int(event.get("ts_ns", 0) or 0)
            topic = str(event.get("topic", "unknown"))
            event["event_index"] = index
            event.setdefault("event_id", f"{session_id}:{topic}:{current_ts}:{index}")
            by_topic_counter[topic] += 1
            by_kind_counter[str(event.get("kind", topic))] += 1
            request_id = str(event.get("request_id", ""))
            correlation_id = str(event.get("correlation_id", ""))
            if request_id:
                request_ids.add(request_id)
            if correlation_id:
                correlation_ids.add(correlation_id)
            if previous_ts and current_ts - previous_ts > 30_000_000_000:
                continuity_gaps.append({"from_ts_ns": previous_ts, "to_ts_ns": current_ts, "gap_ns": current_ts - previous_ts, "scope": "session"})
            topic_previous = previous_by_topic.get(topic)
            if topic_previous and current_ts - topic_previous > 30_000_000_000:
                by_topic_gaps[topic].append({"from_ts_ns": topic_previous, "to_ts_ns": current_ts, "gap_ns": current_ts - topic_previous})
            previous_by_topic[topic] = current_ts
            previous_ts = current_ts
        return {
            "generated_at": now_text(),
            "session_id": session_id,
            "events": normalized,
            "summary": {
                "event_count": len(normalized),
                "topic_count": len(topics),
                "topics": topics,
                "first_ts_ns": first_ts,
                "last_ts_ns": last_ts,
                "continuity_gap_count": len(continuity_gaps),
                "request_id_count": len(request_ids),
                "correlation_id_count": len(correlation_ids),
            },
            "by_topic": dict(sorted(by_topic_counter.items())),
            "by_kind": dict(sorted(by_kind_counter.items())),
            "continuity_gaps": continuity_gaps,
            "topic_continuity_gaps": {topic: gaps for topic, gaps in sorted(by_topic_gaps.items())},
        }
