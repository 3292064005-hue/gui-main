from __future__ import annotations

from spine_ultrasound_ui.services.session_resume_service import SessionResumeService


def test_resume_controller_outputs_required_states_and_command_sequence():
    service = SessionResumeService()
    result = service.evaluate(
        session_id='S1',
        manifest={'scan_plan_hash': 'ph1'},
        resume_state={
            'resume_ready': True,
            'last_successful_segment': 2,
            'last_successful_waypoint': 4,
            'plan_hash': 'ph1',
            'resume_checkpoint_policy': 'waypoint_resume',
        },
        recovery_report={'summary': {'latest_recovery_state': 'CONTROLLED_RETRACT'}},
        incidents={'summary': {'types': ['contact_instability_incident']}, 'incidents': [{'segment_id': 2, 'incident_type': 'contact_instability_incident'}]},
        integrity={'summary': {'integrity_ok': True}, 'warnings': []},
    )
    assert result['resume_allowed'] is True
    assert result['resume_mode'] == 'patch_before_resume'
    assert result['required_core_state'] == 'PATH_VALIDATED'
    assert result['required_contact_state'] == 'CONTACT_STABLE'
    assert result['required_plan_hash'] == 'ph1'
    assert result['checkpoint_granularity'] == 'waypoint_resume'
    assert result['command_sequence'][0]['command'] == 'validate_setup'
    assert result['command_sequence'][-1]['command'] == 'start_scan'
    assert 'verify_plan_hash' in result['verification_checks']
