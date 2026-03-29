from __future__ import annotations

from spine_ultrasound_ui.services.event_bus import EventBus


def test_event_bus_must_deliver_ack_and_retry_cycle():
    bus = EventBus()
    subscription = bus.subscribe(deliveries={'must_deliver'}, categories={'session'}, subscriber_name='qa-feed', ack_required=True)
    bus.publish('contract_consistency_updated', {'session_id': 'S1'}, session_id='S1', category='session', delivery='must_deliver', ts_ns=10)

    message = subscription.get(timeout=0.2)
    assert message is not None
    assert message['topic'] == 'contract_consistency_updated'
    assert message['ack_id']
    assert bus.stats()['pending_ack_count'] == 1

    assert bus.ack(subscription, message) is True
    assert bus.stats()['pending_ack_count'] == 0
    bus.unsubscribe(subscription)


def test_event_bus_retry_pending_requeues_expired_ack():
    bus = EventBus()
    subscription = bus.subscribe(deliveries={'must_deliver'}, categories={'session'}, subscriber_name='audit-feed', ack_required=True)
    bus.publish('release_evidence_updated', {'session_id': 'S1'}, session_id='S1', category='session', delivery='must_deliver', ts_ns=15)
    first = subscription.get(timeout=0.2)
    assert first is not None and first['ack_id']

    # Let the pending item expire immediately.
    pending = bus.pending_acks()[0]
    outcome = bus.retry_pending(now_ns=int(pending['deadline_ns']) + 1)
    assert outcome['retried'] == 1
    retried = subscription.get(timeout=0.2)
    assert retried is not None
    assert retried['ack_id'] == first['ack_id']
    assert bus.ack(subscription, retried) is True
    bus.unsubscribe(subscription)


def test_event_bus_replay_page_supports_cursor():
    bus = EventBus()
    bus.publish('core_state', {'execution_state': 'AUTO_READY'}, session_id='S1', category='runtime', delivery='telemetry', ts_ns=1)
    bus.publish('session_product_update', {'session_id': 'S1'}, session_id='S1', category='session', delivery='event', ts_ns=2)
    bus.publish('event_log_index_updated', {'session_id': 'S1'}, session_id='S1', category='session', delivery='persisted', ts_ns=3)

    first_page = bus.replay_page(session_id='S1', page_size=2)
    assert first_page['summary']['count'] == 2
    assert first_page['next_cursor']
    second_page = bus.replay_page(session_id='S1', page_size=2, cursor=first_page['next_cursor'])
    assert second_page['summary']['count'] == 1
    assert second_page['events'][0]['topic'] == 'event_log_index_updated'
