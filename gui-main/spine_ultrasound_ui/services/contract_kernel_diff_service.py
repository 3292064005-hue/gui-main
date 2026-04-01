from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.command_state_policy import CommandStatePolicyService
from spine_ultrasound_ui.services.ipc_protocol import COMMAND_SPECS, PROTOCOL_VERSION
from spine_ultrasound_ui.utils import now_text


class ContractKernelDiffService:
    SERVICE_VERSION = 'contract_kernel_diff_v1'

    def __init__(self) -> None:
        self.command_policy = CommandStatePolicyService()

    def build(self, session_dir: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        scan_plan = self._read_json(session_dir / 'meta' / 'scan_plan.json')
        selected = self._read_json(session_dir / 'derived' / 'planning' / 'selected_execution_rationale.json')
        policy_snapshot = self._read_json(session_dir / 'derived' / 'session' / 'command_policy_snapshot.json')
        contract_consistency = self._read_json(session_dir / 'derived' / 'session' / 'contract_consistency.json')
        release_gate = self._read_json(session_dir / 'export' / 'release_gate_decision.json')

        catalog = self.command_policy.catalog()
        catalog_policies = {item['command']: item for item in catalog.get('policies', [])}
        snapshot_decisions = dict(policy_snapshot.get('decisions', {}))

        diffs: list[dict[str, Any]] = []
        checks: dict[str, bool] = {}

        checks['policy_command_coverage'] = set(catalog_policies) == set(COMMAND_SPECS)
        if not checks['policy_command_coverage']:
            diffs.append({'name': 'policy_command_coverage', 'reason': 'policy_command_set_mismatch', 'expected_count': len(COMMAND_SPECS), 'actual_count': len(catalog_policies)})

        checks['policy_snapshot_coverage'] = set(snapshot_decisions) == set(catalog_policies)
        if not checks['policy_snapshot_coverage']:
            diffs.append({'name': 'policy_snapshot_coverage', 'reason': 'policy_snapshot_missing_commands', 'expected_count': len(catalog_policies), 'actual_count': len(snapshot_decisions)})

        checks['policy_version_alignment'] = policy_snapshot.get('policy_version', '') == catalog.get('policy_version', '')
        if not checks['policy_version_alignment']:
            diffs.append({'name': 'policy_version_alignment', 'reason': 'policy_version_mismatch', 'catalog_version': catalog.get('policy_version', ''), 'snapshot_version': policy_snapshot.get('policy_version', '')})

        selected_plan_id = str(selected.get('selected_plan_id', ''))
        plan_id = str(scan_plan.get('plan_id', ''))
        checks['selected_plan_alignment'] = not selected_plan_id or selected_plan_id == plan_id
        if not checks['selected_plan_alignment']:
            diffs.append({'name': 'selected_plan_alignment', 'reason': 'selected_plan_id_mismatch', 'selected_plan_id': selected_plan_id, 'scan_plan_id': plan_id})

        selected_plan_hash = str(selected.get('selected_plan_hash', selected.get('plan_hash', '')))
        manifest_plan_hash = str(manifest.get('scan_plan_hash', ''))
        checks['selected_plan_hash_alignment'] = not selected_plan_hash or selected_plan_hash == manifest_plan_hash
        if not checks['selected_plan_hash_alignment']:
            diffs.append({'name': 'selected_plan_hash_alignment', 'reason': 'selected_plan_hash_mismatch', 'selected_plan_hash': selected_plan_hash, 'manifest_plan_hash': manifest_plan_hash})

        artifact_registry = dict(manifest.get('artifact_registry', {}))
        required_artifacts = {
            'selected_execution_rationale': 'derived/planning/selected_execution_rationale.json',
            'command_policy_snapshot': 'derived/session/command_policy_snapshot.json',
            'release_gate_decision': 'export/release_gate_decision.json',
            'contract_consistency': 'derived/session/contract_consistency.json',
        }
        registry_ok = True
        for key, expected_path in required_artifacts.items():
            actual_path = str(dict(artifact_registry.get(key, {})).get('path', ''))
            if actual_path != expected_path:
                registry_ok = False
                diffs.append({'name': 'artifact_registry_path_alignment', 'reason': 'artifact_registry_path_mismatch', 'artifact': key, 'expected_path': expected_path, 'actual_path': actual_path})
        checks['artifact_registry_alignment'] = registry_ok

        checks['protocol_version_alignment'] = int(manifest.get('core_protocol_version', PROTOCOL_VERSION) or 0) == int(PROTOCOL_VERSION)
        if not checks['protocol_version_alignment']:
            diffs.append({'name': 'protocol_version_alignment', 'reason': 'protocol_version_mismatch', 'manifest_protocol_version': manifest.get('core_protocol_version'), 'runtime_protocol_version': PROTOCOL_VERSION})

        expected_release_gate_schema = 'runtime/release_gate_decision_v1.schema.json'
        checks['schema_version_alignment'] = (not release_gate) or str(release_gate.get('schema', '')) == expected_release_gate_schema
        if not checks['schema_version_alignment']:
            diffs.append({'name': 'schema_version_alignment', 'reason': 'release_gate_schema_missing', 'release_gate_schema': release_gate.get('schema', ''), 'expected_release_gate_schema': expected_release_gate_schema})

        checks['contract_consistency_pass_through'] = bool(contract_consistency.get('summary', {}).get('consistent', False))
        if not checks['contract_consistency_pass_through']:
            diffs.append({'name': 'contract_consistency_pass_through', 'reason': 'contract_consistency_failed', 'summary': contract_consistency.get('summary', {})})

        consistent = all(checks.values())
        return {
            'generated_at': now_text(),
            'session_id': str(manifest.get('session_id', session_dir.name)),
            'service_version': self.SERVICE_VERSION,
            'schema': 'session/contract_kernel_diff_v1.schema.json',
            'checks': checks,
            'summary': {'consistent': consistent, 'diff_count': len(diffs), 'checked_object_count': len(checks)},
            'diffs': diffs,
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding='utf-8'))
