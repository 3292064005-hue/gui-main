from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.services.command_policy_snapshot_service import CommandPolicySnapshotService
from spine_ultrasound_ui.services.contract_kernel_diff_service import ContractKernelDiffService
from spine_ultrasound_ui.services.release_gate_decision_service import ReleaseGateDecisionService


def _write(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding='utf-8')


def test_contract_kernel_diff_and_release_gate_include_alignment(tmp_path: Path):
    session = tmp_path / 'S1'
    _write(session / 'meta' / 'manifest.json', {
        'session_id': 'S1',
        'scan_plan_hash': 'ph1',
        'core_protocol_version': 1,
        'artifact_registry': {
            'selected_execution_rationale': {'path': 'derived/planning/selected_execution_rationale.json'},
            'command_policy_snapshot': {'path': 'derived/session/command_policy_snapshot.json'},
            'release_gate_decision': {'path': 'export/release_gate_decision.json'},
            'contract_consistency': {'path': 'derived/session/contract_consistency.json'},
        },
    })
    _write(session / 'meta' / 'scan_plan.json', {'plan_id': 'PLAN_1'})
    _write(session / 'derived' / 'planning' / 'selected_execution_rationale.json', {'selected_plan_id': 'PLAN_1', 'selected_plan_hash': 'ph1'})
    snapshot = CommandPolicySnapshotService().build(
        session_id='S1',
        manifest={'scan_plan_hash': 'ph1'},
        scan_plan={'plan_hash': 'ph1'},
        recovery_report={'summary': {'latest_recovery_state': 'HOLDING'}},
        resume_decision={'resume_mode': 'segment_restart', 'required_contact_state': 'CONTACT_STABLE'},
        resume_attempts={'summary': {'latest_mode': 'segment_restart'}},
    )
    _write(session / 'derived' / 'session' / 'command_policy_snapshot.json', snapshot)
    _write(session / 'derived' / 'session' / 'contract_consistency.json', {'summary': {'consistent': True}})
    _write(session / 'export' / 'release_gate_decision.json', {'schema': 'runtime/release_gate_decision_v1.schema.json'})

    diff = ContractKernelDiffService().build(session)
    assert diff['summary']['consistent'] is True
    assert diff['checks']['policy_snapshot_coverage'] is True

    _write(session / 'derived' / 'session' / 'contract_kernel_diff.json', diff)
    _write(session / 'export' / 'release_evidence_pack.json', {'release_candidate': True})
    _write(session / 'export' / 'diagnostics_pack.json', {'summary': {'issue_count': 0}})
    _write(session / 'export' / 'session_integrity.json', {'summary': {'integrity_ok': True}})
    _write(session / 'derived' / 'events' / 'event_delivery_summary.json', {'summary': {'continuity_gap_count': 0}})
    _write(session / 'derived' / 'session' / 'resume_attempt_outcomes.json', {'summary': {'latest_outcome': 'success'}})

    decision = ReleaseGateDecisionService().build(session)
    assert decision['release_allowed'] is True
    assert any(item['name'] == 'contract_kernel_diff' for item in decision['check_results'])
