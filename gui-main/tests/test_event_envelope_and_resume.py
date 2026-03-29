from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.services.event_bus import EventBus
from spine_ultrasound_ui.services.event_envelope import EventEnvelope
from spine_ultrasound_ui.services.event_replay_bus import EventReplayBus
from spine_ultrasound_ui.services.role_matrix import RoleMatrix
from spine_ultrasound_ui.services.session_dir_watcher import SessionDirWatcher
from spine_ultrasound_ui.services.session_resume_service import SessionResumeService


def test_event_envelope_and_replay_bus_round_trip():
    replay = EventReplayBus(max_events=4)
    bus = EventBus(replay)
    bus.publish('core_state', {'execution_state': 'AUTO_READY'}, session_id='S1', correlation_id='c1', request_id='r1')
    message = bus.replay({'core_state'}, session_id='S1')[-1]
    assert message['topic'] == 'core_state'
    assert message['session_id'] == 'S1'
    assert message['correlation_id'] == 'c1'
    assert message['request_id'] == 'r1'
    assert bus.stats()['published_events'] == 1


def test_role_matrix_restricts_researcher_commands():
    matrix = RoleMatrix()
    assert matrix.can_issue_command('operator', 'start_scan') is True
    assert matrix.can_issue_command('researcher', 'start_scan') is False
    assert matrix.can_read_category('reviewer', 'session') is True
    assert matrix.can_read_category('reviewer', 'runtime') is False


def test_session_dir_watcher_detects_resume_and_incident_products(tmp_path: Path):
    session_dir = tmp_path / 'S1'
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'derived' / 'incidents').mkdir(parents=True)
    (session_dir / 'derived' / 'events').mkdir(parents=True)
    (session_dir / 'derived' / 'recovery').mkdir(parents=True)
    (session_dir / 'meta' / 'resume_decision.json').write_text('{}', encoding='utf-8')
    (session_dir / 'derived' / 'incidents' / 'session_incidents.json').write_text('{}', encoding='utf-8')
    (session_dir / 'derived' / 'events' / 'event_log_index.json').write_text('{}', encoding='utf-8')
    (session_dir / 'derived' / 'recovery' / 'recovery_decision_timeline.json').write_text('{}', encoding='utf-8')
    watcher = SessionDirWatcher()
    watcher.poll(session_dir, session_id='S1')
    (session_dir / 'meta' / 'resume_decision.json').write_text('{"changed": true}', encoding='utf-8')
    (session_dir / 'derived' / 'events' / 'event_log_index.json').write_text('{"changed": true}', encoding='utf-8')
    events = watcher.poll(session_dir, session_id='S1')
    topics = {event['topic'] for event in events}
    assert 'resume_decision_updated' in topics
    assert 'event_log_index_updated' in topics


def test_resume_service_returns_resume_controller_shape():
    service = SessionResumeService()
    result = service.evaluate(
        session_id='S1',
        manifest={'scan_plan_hash': 'ph1'},
        resume_state={'resume_ready': True, 'last_successful_segment': 2, 'last_successful_waypoint': 4, 'plan_hash': 'ph1'},
        recovery_report={'summary': {'latest_recovery_state': 'CONTROLLED_RETRACT'}},
        incidents={'summary': {'types': ['contact_instability_incident']}, 'incidents': [{'segment_id': 2, 'incident_type': 'contact_instability_incident'}]},
        integrity={'summary': {'integrity_ok': True}, 'warnings': []},
    )
    assert result['resume_allowed'] is True
    assert result['resume_mode'] == 'patch_before_resume'
    assert 'apply_patch_plan' in result['pre_resume_actions']
    assert result['resume_cursor']['segment_id'] == 2
    assert result['resume_token']
