from __future__ import annotations

from spine_ultrasound_ui.services.command_state_policy import CommandStatePolicyService
from spine_ultrasound_ui.services.resume_execution_service import ResumeExecutionService


def test_command_state_policy_catalog_exposes_role_and_state_matrix():
    service = CommandStatePolicyService()
    catalog = service.catalog()
    connect_policy = next(item for item in catalog['policies'] if item['command'] == 'connect_robot')
    assert 'BOOT' in connect_policy['allowed_states']
    assert 'operator' in connect_policy['role_write_gate']
    assert connect_policy['reject_reason_code'] == 'connect_robot_state_gate'


def test_resume_execution_service_generates_outcome_contract():
    service = ResumeExecutionService()
    result = service.evaluate_attempt_outcomes(
        session_id='S1',
        resume_decision={
            'resume_mode': 'reacquire_contact_then_resume',
            'resume_token': 'rtok',
            'required_plan_hash': 'ph1',
            'command_sequence': [{'command': 'validate_setup'}, {'command': 'resume_scan'}],
        },
        resume_attempts={
            'attempts': [
                {
                    'command': 'resume_scan',
                    'ok': False,
                    'outcome': 'blocked',
                    'message': 'contact unstable',
                    'ts_ns': 10,
                    'resume_mode': 'reacquire_contact_then_resume',
                    'resume_token': 'rtok',
                }
            ]
        },
        contract_consistency={'hash_alignment': {'scan_plan_hash_match': True}},
    )
    assert result['summary']['attempt_count'] == 1
    assert result['outcomes'][0]['sequence_outcome'] == 'blocked'
    assert result['outcomes'][0]['fallback_resume_mode'] == 'segment_restart'
    assert result['outcomes'][0]['plan_hash_verified'] is True
