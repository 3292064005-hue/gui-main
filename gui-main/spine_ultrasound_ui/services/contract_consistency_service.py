from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.contracts import schema_catalog
from spine_ultrasound_ui.models import ScanPlan
from spine_ultrasound_ui.utils import now_text


class ContractConsistencyService:
    REQUIRED_ARTIFACTS = {
        "scan_plan": "meta/scan_plan.json",
        "device_readiness": "meta/device_readiness.json",
        "xmate_profile": "meta/xmate_profile.json",
        "patient_registration": "meta/patient_registration.json",
        "scan_protocol": "derived/preview/scan_protocol.json",
        "session_integrity": "export/session_integrity.json",
        "lineage": "meta/lineage.json",
        "resume_state": "meta/resume_state.json",
        "resume_decision": "meta/resume_decision.json",
        "session_incidents": "derived/incidents/session_incidents.json",
        "event_log_index": "derived/events/event_log_index.json",
        "recovery_decision_timeline": "derived/recovery/recovery_decision_timeline.json",
    }

    def build(self, session_dir: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        scan_plan_payload = self._read_json(session_dir / 'meta' / 'scan_plan.json')
        diagnostics = self._read_json(session_dir / 'export' / 'diagnostics_pack.json')
        resume_decision = self._read_json(session_dir / 'meta' / 'resume_decision.json')
        event_log_index = self._read_json(session_dir / 'derived' / 'events' / 'event_log_index.json')
        artifact_registry = dict(manifest.get('artifact_registry', {}))
        mismatches: list[dict[str, Any]] = []
        warnings: list[str] = []
        evidence_refs: list[dict[str, Any]] = []

        plan_hash_manifest = str(manifest.get('scan_plan_hash', ''))
        plan_hash_computed = ''
        plan_hash_template = ''
        if scan_plan_payload:
            try:
                plan = ScanPlan.from_dict(scan_plan_payload)
                plan_hash_computed = plan.plan_hash()
                plan_hash_template = plan.template_hash()
            except Exception as exc:
                warnings.append(f'scan_plan_parse_failed:{exc}')
        if plan_hash_manifest and plan_hash_computed and plan_hash_manifest != plan_hash_computed:
            mismatches.append({
                'field': 'scan_plan_hash',
                'manifest': plan_hash_manifest,
                'computed': plan_hash_computed,
                'severity': 'error',
            })
            evidence_refs.append({'kind': 'scan_plan_hash', 'manifest': plan_hash_manifest, 'computed': plan_hash_computed})

        planner_version_manifest = str(manifest.get('planner_version', ''))
        planner_version_plan = str(scan_plan_payload.get('planner_version', ''))
        planner_version_diag = str(diagnostics.get('manifest_excerpt', {}).get('planner_version', ''))
        if len({value for value in [planner_version_manifest, planner_version_plan, planner_version_diag] if value}) > 1:
            mismatches.append({
                'field': 'planner_version',
                'manifest': planner_version_manifest,
                'scan_plan': planner_version_plan,
                'diagnostics': planner_version_diag,
                'severity': 'error',
            })

        registration_hash_manifest = str(manifest.get('patient_registration_hash', ''))
        registration_hash_plan = str(scan_plan_payload.get('registration_hash', ''))
        if registration_hash_manifest and registration_hash_plan and registration_hash_manifest != registration_hash_plan:
            mismatches.append({
                'field': 'registration_hash',
                'manifest': registration_hash_manifest,
                'scan_plan': registration_hash_plan,
                'severity': 'warn',
            })

        core_protocol_version = int(manifest.get('core_protocol_version', manifest.get('protocol_version', 0)) or 0)
        protocol_version = int(manifest.get('protocol_version', 0) or 0)
        diagnostics_protocol_version = int(diagnostics.get('manifest_excerpt', {}).get('protocol_version', protocol_version) or 0)
        if len({core_protocol_version, protocol_version, diagnostics_protocol_version}) > 1:
            mismatches.append({
                'field': 'protocol_version',
                'manifest': protocol_version,
                'core': core_protocol_version,
                'diagnostics': diagnostics_protocol_version,
                'severity': 'error',
            })

        required_artifacts: list[dict[str, Any]] = []
        present_count = 0
        for name, relative_path in sorted(self.REQUIRED_ARTIFACTS.items()):
            exists = (session_dir / relative_path).exists()
            if exists:
                present_count += 1
            descriptor = artifact_registry.get(name, {})
            schema_hint = str(descriptor.get('schema', ''))
            if exists and not descriptor:
                warnings.append(f'artifact_registry_missing:{name}')
            if descriptor and schema_hint and schema_hint not in schema_catalog():
                mismatches.append({
                    'field': f'artifact_schema:{name}',
                    'schema': schema_hint,
                    'severity': 'warn',
                })
            required_artifacts.append({
                'artifact': name,
                'path': relative_path,
                'exists': exists,
                'registered': bool(descriptor),
                'schema': schema_hint,
            })

        if int(event_log_index.get('summary', {}).get('continuity_gap_count', 0)) > 0:
            warnings.append('event_log_continuity_gaps')
            evidence_refs.append({
                'kind': 'event_log_index',
                'continuity_gap_count': int(event_log_index.get('summary', {}).get('continuity_gap_count', 0)),
            })

        if resume_decision and not resume_decision.get('resume_allowed', False):
            warnings.append('resume_blocked')
            evidence_refs.append({
                'kind': 'resume_decision',
                'blocking_reasons': list(resume_decision.get('blocking_reasons', [])),
            })

        summary = {
            'consistent': not any(item.get('severity') == 'error' for item in mismatches),
            'mismatch_count': len(mismatches),
            'warning_count': len(warnings),
            'required_artifact_count': len(required_artifacts),
            'required_artifact_coverage': round(present_count / max(1, len(required_artifacts)), 4),
        }
        return {
            'generated_at': now_text(),
            'session_id': str(manifest.get('session_id', session_dir.name)),
            'summary': summary,
            'version_alignment': {
                'protocol_version': protocol_version,
                'core_protocol_version': core_protocol_version,
                'diagnostics_protocol_version': diagnostics_protocol_version,
                'planner_version': planner_version_manifest,
                'scan_plan_planner_version': planner_version_plan,
            },
            'hash_alignment': {
                'scan_plan_hash_manifest': plan_hash_manifest,
                'scan_plan_hash_computed': plan_hash_computed,
                'scan_plan_template_hash': plan_hash_template,
                'registration_hash_manifest': registration_hash_manifest,
                'registration_hash_scan_plan': registration_hash_plan,
            },
            'required_artifacts': required_artifacts,
            'mismatches': mismatches,
            'warnings': warnings,
            'evidence_refs': evidence_refs,
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding='utf-8'))
