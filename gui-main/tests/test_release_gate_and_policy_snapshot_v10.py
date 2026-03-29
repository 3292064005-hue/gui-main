from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.services.command_policy_snapshot_service import CommandPolicySnapshotService
from spine_ultrasound_ui.services.release_gate_decision_service import ReleaseGateDecisionService


def _write(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding='utf-8')


def test_command_policy_snapshot_materializes_decisions() -> None:
    service = CommandPolicySnapshotService()
    payload = service.build(
        session_id='S1',
        manifest={'scan_plan_hash': 'ph1'},
        scan_plan={'plan_hash': 'ph1'},
        recovery_report={'summary': {'latest_recovery_state': 'HOLDING'}},
        resume_decision={'resume_mode': 'segment_restart', 'required_contact_state': 'CONTACT_STABLE'},
        resume_attempts={'summary': {'latest_mode': 'segment_restart'}},
    )
    assert payload['execution_state'] == 'PAUSED_HOLD'
    assert payload['decision_count'] > 0
    assert 'resume_scan' in payload['decisions']


def test_release_gate_decision_reports_gate_metadata(tmp_path: Path) -> None:
    session = tmp_path / 'S1'
    _write(session / 'meta' / 'manifest.json', {'session_id': 'S1'})
    _write(session / 'derived' / 'session' / 'contract_consistency.json', {'summary': {'consistent': True}})
    _write(session / 'export' / 'release_evidence_pack.json', {'release_candidate': True})
    _write(session / 'export' / 'diagnostics_pack.json', {'summary': {'issue_count': 0}})
    _write(session / 'export' / 'session_integrity.json', {'summary': {'integrity_ok': True}})
    _write(session / 'derived' / 'events' / 'event_delivery_summary.json', {'summary': {'continuity_gap_count': 0}})
    _write(session / 'derived' / 'session' / 'resume_attempt_outcomes.json', {'summary': {'latest_outcome': 'success'}})
    _write(session / 'derived' / 'planning' / 'selected_execution_rationale.json', {'selected_plan_id': 'P1'})
    _write(session / 'derived' / 'session' / 'command_policy_snapshot.json', {'policy_version': 'command_state_policy_v2', 'decision_count': 5, 'decisions': {'start_scan': {'allowed': True}}})
    _write(session / 'derived' / 'session' / 'contract_kernel_diff.json', {'summary': {'consistent': True}})
    decision = ReleaseGateDecisionService().build(session)
    assert decision['gate_version'] == 'release_gate_v3'
    assert decision['release_allowed'] is True
    assert any(item['name'] == 'command_policy_snapshot' for item in decision['check_results'])
    assert 'derived/session/command_policy_snapshot.json' in decision['evaluated_artifacts']
