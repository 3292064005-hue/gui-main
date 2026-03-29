from __future__ import annotations

from spine_ultrasound_ui.services.event_bus import EventBus


def test_event_bus_filters_by_delivery_and_category():
    bus = EventBus()
    telemetry_sub = bus.subscribe(deliveries={'telemetry'}, categories={'runtime'})
    persisted_sub = bus.subscribe(deliveries={'persisted'}, categories={'session'})

    bus.publish('core_state', {'execution_state': 'AUTO_READY'}, session_id='S1', category='runtime', delivery='telemetry', ts_ns=1)
    bus.publish('event_log_index_updated', {'session_id': 'S1'}, session_id='S1', category='session', delivery='persisted', ts_ns=2)

    telemetry = telemetry_sub.get(timeout=0.2)
    persisted = persisted_sub.get(timeout=0.2)
    assert telemetry is not None and telemetry['topic'] == 'core_state'
    assert persisted is not None and persisted['topic'] == 'event_log_index_updated'
    assert bus.stats()['published_by_delivery']['persisted'] == 1
    bus.unsubscribe(telemetry_sub)
    bus.unsubscribe(persisted_sub)


def test_event_bus_replay_can_filter_by_delivery_category_and_session():
    bus = EventBus()
    bus.publish('core_state', {'execution_state': 'AUTO_READY'}, session_id='S1', category='runtime', delivery='telemetry', ts_ns=10)
    bus.publish('session_product_update', {'session_id': 'S1'}, session_id='S1', category='session', delivery='event', ts_ns=20)
    bus.publish('event_log_index_updated', {'session_id': 'S1'}, session_id='S1', category='session', delivery='persisted', ts_ns=30)
    replay = bus.replay(session_id='S1', category='session', delivery='persisted')
    assert len(replay) == 1
    assert replay[0]['topic'] == 'event_log_index_updated'
