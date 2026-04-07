from __future__ import annotations

from spine_ultrasound_ui.services.event_bus import EventBus


def test_event_bus_replay_filters_by_session_and_time_window():
    bus = EventBus()
    bus.publish('core_state', {'execution_state': 'AUTO_READY'}, session_id='S1', ts_ns=10)
    bus.publish('core_state', {'execution_state': 'SCANNING'}, session_id='S2', ts_ns=20)
    bus.publish('alarm_event', {'severity': 'WARN'}, session_id='S1', ts_ns=30, delivery='event')
    replay = bus.replay({'core_state', 'alarm_event'}, session_id='S1', since_ts_ns=15)
    assert len(replay) == 1
    assert replay[0]['topic'] == 'alarm_event'


def test_event_bus_stats_tracks_slow_subscribers():
    bus = EventBus()
    sub = bus.subscribe({'core_state'}, latest_only=True, queue_limit=1)
    bus.publish('core_state', {'n': 1}, session_id='S1')
    bus.publish('core_state', {'n': 2}, session_id='S1')
    stats = bus.stats()
    assert stats['published_events'] == 2
    assert stats['subscriber_count'] == 1
    assert stats['max_queue_depth'] >= 1
    bus.unsubscribe(sub)
