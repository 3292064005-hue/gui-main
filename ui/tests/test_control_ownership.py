from __future__ import annotations

from spine_ultrasound_ui.services.control_authority_service import ControlAuthorityService


def test_control_ownership_stable_surface_uses_current_claim_guard() -> None:
    service = ControlAuthorityService(strict_mode=True, auto_issue_implicit_lease=True)
    decision = service.guard_command(
        'safe_retreat',
        {'_command_context': {'actor_id': 'desktop-owner', 'workspace': 'desktop', 'role': 'operator'}},
        current_session_id='S-OWN',
        source='headless',
    )
    assert decision['allowed'] is True
    snapshot = service.snapshot()
    assert snapshot['owner']['actor_id'] == 'desktop-owner'
    assert 'rt_motion_write' in snapshot['granted_claims']


def test_control_ownership_review_surface_checks_claims_without_bootstrapping_lease() -> None:
    service = ControlAuthorityService(strict_mode=True, auto_issue_implicit_lease=True)
    decision = service.guard_command(
        'validate_scan_plan',
        {'_command_context': {'actor_id': 'reviewer', 'workspace': 'review', 'role': 'review'}},
        current_session_id='S-OWN',
        source='headless',
        require_lease=False,
    )
    assert decision['allowed'] is True
    assert decision['normalized_payload']['_command_context']['lease_required'] is False
    assert service.snapshot()['active_lease'] == {}
