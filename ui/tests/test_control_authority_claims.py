from __future__ import annotations

from spine_ultrasound_ui.services.control_authority_service import ControlAuthorityService


def test_control_authority_auto_grants_required_claim_for_operator() -> None:
    service = ControlAuthorityService(strict_mode=True, auto_issue_implicit_lease=True)
    decision = service.guard_command(
        'start_scan',
        {'_command_context': {'actor_id': 'desktop-a', 'workspace': 'desktop', 'role': 'operator'}},
        current_session_id='S1',
        source='headless',
    )
    assert decision['allowed'] is True
    ctx = decision['normalized_payload']['_command_context']
    assert ctx['required_claim'] == 'rt_motion_write'
    assert 'rt_motion_write' in ctx['granted_claims']
    snapshot = service.snapshot()
    assert 'rt_motion_write' in snapshot['granted_claims']
    assert snapshot['claim_bindings']['rt_motion_write']['owner'] == 'desktop-a'


def test_control_authority_rejects_role_without_required_claim() -> None:
    service = ControlAuthorityService(strict_mode=True, auto_issue_implicit_lease=True)
    decision = service.guard_command(
        'start_scan',
        {'_command_context': {'actor_id': 'desktop-b', 'workspace': 'desktop', 'role': 'researcher'}},
        current_session_id='S1',
        source='headless',
    )
    assert decision['allowed'] is False
    assert '无权获取 rt_motion_write' in decision['message']


def test_validate_scan_plan_capability_check_does_not_allocate_lease() -> None:
    service = ControlAuthorityService(strict_mode=True, auto_issue_implicit_lease=True)
    decision = service.guard_command(
        'validate_scan_plan',
        {'_command_context': {'actor_id': 'review-a', 'workspace': 'review', 'role': 'review'}},
        current_session_id='S1',
        source='headless',
        require_lease=False,
    )
    assert decision['allowed'] is True
    ctx = decision['normalized_payload']['_command_context']
    assert ctx['lease_required'] is False
    assert 'plan_compile' in ctx['granted_claims']
    snapshot = service.snapshot()
    assert snapshot['active_lease'] == {}
    assert snapshot['granted_claims'] == []
