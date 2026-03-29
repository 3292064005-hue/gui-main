from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text


class ReleaseGateDecisionService:
    GATE_VERSION = 'release_gate_v3'

    def build(self, session_dir: Path) -> dict[str, Any]:
        contract = self._read_json(session_dir / 'derived' / 'session' / 'contract_consistency.json')
        release_evidence = self._read_json(session_dir / 'export' / 'release_evidence_pack.json')
        diagnostics = self._read_json(session_dir / 'export' / 'diagnostics_pack.json')
        integrity = self._read_json(session_dir / 'export' / 'session_integrity.json')
        event_delivery = self._read_json(session_dir / 'derived' / 'events' / 'event_delivery_summary.json')
        resume_outcomes = self._read_json(session_dir / 'derived' / 'session' / 'resume_attempt_outcomes.json')
        selected_execution = self._read_json(session_dir / 'derived' / 'planning' / 'selected_execution_rationale.json')
        command_policy_snapshot = self._read_json(session_dir / 'derived' / 'session' / 'command_policy_snapshot.json')
        contract_kernel_diff = self._read_json(session_dir / 'derived' / 'session' / 'contract_kernel_diff.json')
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')

        evaluated_artifacts = [
            'meta/manifest.json',
            'derived/session/contract_consistency.json',
            'export/release_evidence_pack.json',
            'export/diagnostics_pack.json',
            'export/session_integrity.json',
            'derived/events/event_delivery_summary.json',
            'derived/session/resume_attempt_outcomes.json',
            'derived/planning/selected_execution_rationale.json',
            'derived/session/command_policy_snapshot.json',
            'derived/session/contract_kernel_diff.json',
        ]

        check_results = [
            self._check('contract_alignment', bool(contract.get('summary', {}).get('consistent', False)), blocking_reason='contract_alignment_failed', remediation='repair_contract_consistency', evidence=['derived/session/contract_consistency.json']),
            self._check('artifact_integrity', bool(integrity.get('summary', {}).get('integrity_ok', False)), blocking_reason='artifact_integrity_failed', remediation='repair_session_integrity', evidence=['export/session_integrity.json']),
            self._check('release_candidate', bool(release_evidence.get('release_candidate', False)), warning_reason='release_evidence_not_candidate', evidence=['export/release_evidence_pack.json']),
            self._check('event_continuity', int(event_delivery.get('summary', {}).get('continuity_gap_count', 0) or 0) == 0, blocking_reason='event_continuity_failed', remediation='rebuild_event_delivery_summary', evidence=['derived/events/event_delivery_summary.json']),
            self._check('resume_viability', str(resume_outcomes.get('summary', {}).get('latest_outcome', 'not_attempted')) not in {'failed', 'blocked'}, warning_reason='resume_viability_failed', evidence=['derived/session/resume_attempt_outcomes.json']),
            self._check('execution_rationale', bool(selected_execution.get('selected_candidate_id') or selected_execution.get('selected_plan_id')), blocking_reason='selected_execution_rationale_missing', remediation='materialize_selected_execution_rationale', evidence=['derived/planning/selected_execution_rationale.json']),
            self._check('command_policy_snapshot', bool(command_policy_snapshot.get('decision_count', 0)) and bool(command_policy_snapshot.get('policy_version')), warning_reason='command_policy_snapshot_missing', remediation='materialize_command_policy_snapshot', evidence=['derived/session/command_policy_snapshot.json']),
            self._check('contract_kernel_diff', bool(contract_kernel_diff.get('summary', {}).get('consistent', False)), blocking_reason='contract_kernel_diff_failed', remediation='repair_contract_kernel_alignment', evidence=['derived/session/contract_kernel_diff.json']),
        ]

        blocking_reasons = [item['blocking_reason'] for item in check_results if item['status'] == 'failed' and item.get('blocking_reason')]
        warning_reasons = [item['warning_reason'] for item in check_results if item['status'] == 'failed' and item.get('warning_reason')]
        required_remediations = sorted({item['remediation'] for item in check_results if item['status'] == 'failed' and item.get('remediation')})
        checks = {item['name']: item['status'] == 'passed' for item in check_results}
        diagnostics_summary = dict(diagnostics.get('summary', {}))
        release_allowed = not blocking_reasons and checks.get('release_candidate', False)
        return {
            'generated_at': now_text(),
            'evaluated_ts': now_text(),
            'session_id': str(manifest.get('session_id', session_dir.name)),
            'gate_version': self.GATE_VERSION,
            'release_allowed': release_allowed,
            'blocking_reasons': blocking_reasons,
            'warning_reasons': warning_reasons,
            'required_remediations': required_remediations,
            'checks': checks,
            'check_results': check_results,
            'evaluated_artifacts': evaluated_artifacts,
            'diagnostics_summary': diagnostics_summary,
            'release_candidate': checks.get('release_candidate', False),
            'schema': 'runtime/release_gate_decision_v1.schema.json',
            'contract_kernel_diff': contract_kernel_diff,
        }

    @staticmethod
    def _check(name: str, passed: bool, *, blocking_reason: str = '', warning_reason: str = '', remediation: str = '', evidence: list[str] | None = None) -> dict[str, Any]:
        return {
            'name': name,
            'status': 'passed' if passed else 'failed',
            'blocking_reason': blocking_reason,
            'warning_reason': warning_reason,
            'remediation': remediation,
            'evidence': list(evidence or []),
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding='utf-8'))
