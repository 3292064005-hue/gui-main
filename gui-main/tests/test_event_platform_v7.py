from __future__ import annotations

from spine_ultrasound_ui.services.event_bus import EventBus


def test_event_bus_moves_exhausted_ack_to_dead_letter_lane():
    bus = EventBus()
    subscription = bus.subscribe(deliveries={'must_deliver'}, categories={'session'}, subscriber_name='qa-feed', ack_required=True)
    bus.publish('release_evidence_updated', {'session_id': 'S1'}, session_id='S1', category='session', delivery='must_deliver', ts_ns=10)
    message = subscription.get(timeout=0.2)
    assert message is not None
    pending = bus.pending_acks()[0]
    # exhaust retries
    for _ in range(6):
      bus.retry_pending(now_ns=int(pending['deadline_ns']) + 10_000_000)
      current = bus.pending_acks()
      if not current:
        break
      pending = current[0]
    dead_letters = bus.dead_letters()
    assert dead_letters['summary']['dead_letter_count'] >= 1
    assert dead_letters['entries'][-1]['reason'] in {'retry_exhausted', 'retry_enqueue_failed'}
    bus.unsubscribe(subscription)
