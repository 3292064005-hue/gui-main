from __future__ import annotations

from spine_ultrasound_ui.services.command_state_policy import CommandStatePolicyService
from spine_ultrasound_ui.services.resume_execution_service import ResumeExecutionService
from spine_ultrasound_ui.services.event_bus import EventBus


def test_command_policy_decision_checks_contact_and_resume_mode() -> None:
    service = CommandStatePolicyService()
    allowed = service.decision('resume_scan', 'PAUSED_HOLD', role='operator', contact_state='CONTACT_STABLE', plan_state='execution_plan_loaded', resume_mode='segment_restart')
    blocked = service.decision('resume_scan', 'PAUSED_HOLD', role='operator', contact_state='CONTACT_UNSTABLE', plan_state='execution_plan_loaded', resume_mode='segment_restart')
    assert allowed['allowed'] is True
    assert blocked['allowed'] is False
    assert blocked['reason'] == 'contact_state_gate'


def test_resume_execution_service_verifies_command_policy_contract() -> None:
    service = ResumeExecutionService()
    result = service.evaluate_attempt_outcomes(
        session_id='S1',
        resume_decision={
            'resume_mode': 'reacquire_contact_then_resume',
            'resume_token': 'rtok',
            'required_plan_hash': 'ph1',
            'required_core_state': 'PATH_VALIDATED',
            'required_contact_state': 'CONTACT_STABLE',
            'required_checkpoint_granularity': 'segment_boundary',
            'required_command_policy': ['validate_setup', 'seek_contact', 'resume_scan'],
            'sequence_outcome_contract': {'success_terminal_states': ['SCANNING']},
            'fallback_resume_mode': 'segment_restart',
            'command_sequence': [
                {'command': 'validate_setup'},
                {'command': 'seek_contact'},
                {'command': 'resume_scan', 'required_state': 'PAUSED_HOLD'},
            ],
        },
        resume_attempts={'attempts': [{'resume_attempt_id': 'attempt_001', 'command': 'resume_scan', 'ok': False, 'outcome': 'blocked', 'message': 'contact unstable', 'ts_ns': 10, 'resume_mode': 'reacquire_contact_then_resume', 'resume_token': 'rtok'}]},
        contract_consistency={'hash_alignment': {'scan_plan_hash_match': True}},
        command_policy_catalog=CommandStatePolicyService().catalog(),
    )
    outcome = result['outcomes'][0]
    assert outcome['command_policy_verified'] is True
    assert outcome['required_checkpoint_granularity'] == 'segment_boundary'
    assert outcome['sequence_outcome_contract']['success_terminal_states'] == ['SCANNING']
    assert outcome['fallback_resume_mode'] == 'segment_restart'


def test_event_bus_delivery_audit_exposes_dead_letters_and_health() -> None:
    bus = EventBus()
    sub = bus.subscribe(deliveries={'must_deliver'}, categories={'session'}, subscriber_name='qa-feed', ack_required=True)
    bus.publish('release_evidence_updated', {'session_id': 'S1'}, session_id='S1', category='session', delivery='must_deliver', ts_ns=10)
    message = sub.get(timeout=0.2)
    assert message is not None
    pending = bus.pending_acks()[0]
    for _ in range(8):
        bus.retry_pending(now_ns=int(pending['deadline_ns']) + 10_000_000)
        current = bus.pending_acks()
        if not current:
            break
        pending = current[0]
    audit = bus.delivery_audit()
    assert audit['dead_letters']['summary']['dead_letter_count'] >= 1
    assert audit['subscriber_health']['subscriber_count'] == 1
    bus.unsubscribe(sub)
