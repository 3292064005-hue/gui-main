from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.services.release_gate_decision_service import ReleaseGateDecisionService
from spine_ultrasound_ui.services.selected_execution_rationale_service import SelectedExecutionRationaleService


def _write(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding='utf-8')


def test_release_gate_decision_blocks_on_contract_and_continuity(tmp_path: Path):
    session = tmp_path / 'S1'
    _write(session / 'meta' / 'manifest.json', {'session_id': 'S1'})
    _write(session / 'derived' / 'session' / 'contract_consistency.json', {'summary': {'consistent': False}})
    _write(session / 'export' / 'release_evidence_pack.json', {'release_candidate': False})
    _write(session / 'export' / 'diagnostics_pack.json', {'summary': {'issue_count': 1}})
    _write(session / 'export' / 'session_integrity.json', {'summary': {'integrity_ok': True}})
    _write(session / 'derived' / 'events' / 'event_delivery_summary.json', {'summary': {'continuity_gap_count': 2}})
    _write(session / 'derived' / 'session' / 'resume_attempt_outcomes.json', {'summary': {'latest_outcome': 'failed'}})
    _write(session / 'derived' / 'planning' / 'selected_execution_rationale.json', {'selected_plan_id': 'P1', 'ranking_snapshot': []})
    _write(session / 'derived' / 'session' / 'command_policy_snapshot.json', {'policy_version': 'command_state_policy_v2', 'decision_count': 1, 'decisions': {'start_scan': {'allowed': False}}})
    _write(session / 'derived' / 'session' / 'contract_kernel_diff.json', {'summary': {'consistent': False}})
    decision = ReleaseGateDecisionService().build(session)
    assert decision['release_allowed'] is False
    assert 'contract_alignment_failed' in decision['blocking_reasons']
    assert 'event_continuity_failed' in decision['blocking_reasons']


def test_selected_execution_rationale_reads_from_scan_plan(tmp_path: Path):
    session = tmp_path / 'S1'
    _write(session / 'meta' / 'manifest.json', {'session_id': 'S1'})
    _write(session / 'meta' / 'scan_plan.json', {
        'plan_id': 'PLAN_1',
        'score_summary': {'risk': 0.1},
        'validation_summary': {
            'selection_rationale': {
                'selected_candidate_id': 'PLAN_1',
                'selection_basis': {'candidate_count': 2},
                'ranking_snapshot': [{'plan_id': 'PLAN_1'}, {'plan_id': 'PLAN_2'}],
                'rejected_candidate_reasons': ['higher_contact_risk'],
            }
        }
    })
    rationale = SelectedExecutionRationaleService().build(session)
    assert rationale['selected_candidate_id'] == 'PLAN_1'
    assert len(rationale['ranking_snapshot']) == 2
