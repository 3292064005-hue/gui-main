from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text


class ReleaseEvidencePackService:
    REQUIRED_RELEASE_ARTIFACTS = {
        'manifest': 'meta/manifest.json',
        'scan_plan': 'meta/scan_plan.json',
        'session_integrity': 'export/session_integrity.json',
        'diagnostics_pack': 'export/diagnostics_pack.json',
        'contract_consistency': 'derived/session/contract_consistency.json',
        'resume_decision': 'meta/resume_decision.json',
        'event_log_index': 'derived/events/event_log_index.json',
        'recovery_decision_timeline': 'derived/recovery/recovery_decision_timeline.json',
        'session_report': 'export/session_report.json',
        'qa_pack': 'export/qa_pack.json',
    }

    def build(self, session_dir: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        diagnostics = self._read_json(session_dir / 'export' / 'diagnostics_pack.json')
        integrity = self._read_json(session_dir / 'export' / 'session_integrity.json')
        contract = self._read_json(session_dir / 'derived' / 'session' / 'contract_consistency.json')
        readiness = self._read_json(session_dir / 'meta' / 'device_readiness.json')
        resume_decision = self._read_json(session_dir / 'meta' / 'resume_decision.json')
        artifact_registry = dict(manifest.get('artifact_registry', {}))
        evidence_index = []
        gaps = []
        for name, relative in sorted(self.REQUIRED_RELEASE_ARTIFACTS.items()):
            exists = (session_dir / relative).exists()
            descriptor = artifact_registry.get(name, {})
            evidence_index.append({
                'artifact': name,
                'path': relative,
                'exists': exists,
                'registered': bool(descriptor),
                'checksum': str(descriptor.get('checksum', '')),
                'schema': str(descriptor.get('schema', '')),
            })
            if not exists:
                gaps.append(f'missing:{name}')
        if not bool(integrity.get('summary', {}).get('integrity_ok', False)):
            gaps.append('integrity_not_ok')
        if not bool(contract.get('summary', {}).get('consistent', False)):
            gaps.append('contract_inconsistent')
        advisory_gaps: list[str] = []
        if not bool(readiness.get('ready_to_lock', False)):
            advisory_gaps.append('device_not_ready_snapshot')
        if not bool(resume_decision.get('resume_allowed', True)):
            advisory_gaps.append('resume_blocked')
        release_candidate = bool(contract.get('summary', {}).get('consistent', False))
        return {
            'generated_at': now_text(),
            'session_id': str(manifest.get('session_id', session_dir.name)),
            'release_candidate': release_candidate,
            'release_readiness': {
                'integrity_ok': bool(integrity.get('summary', {}).get('integrity_ok', False)),
                'contract_consistent': bool(contract.get('summary', {}).get('consistent', False)),
                'device_ready_snapshot': bool(readiness.get('ready_to_lock', False)),
                'resume_allowed': bool(resume_decision.get('resume_allowed', False)),
            },
            'version_lock': {
                'software_version': manifest.get('software_version', ''),
                'build_id': manifest.get('build_id', ''),
                'protocol_version': manifest.get('protocol_version', 0),
                'core_protocol_version': manifest.get('core_protocol_version', 0),
                'planner_version': manifest.get('planner_version', ''),
                'registration_version': manifest.get('registration_version', ''),
            },
            'diagnostics_summary': diagnostics.get('summary', {}),
            'integrity_summary': integrity.get('summary', {}),
            'contract_summary': contract.get('summary', {}),
            'evidence_index': evidence_index,
            'open_gaps': gaps,
            'advisory_gaps': advisory_gaps,
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding='utf-8'))
