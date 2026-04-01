from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.services.command_state_policy import CommandStatePolicyService
from spine_ultrasound_ui.utils import now_text


class CommandPolicySnapshotService:
    def __init__(self, policy_service: CommandStatePolicyService | None = None) -> None:
        self.policy_service = policy_service or CommandStatePolicyService()

    def build(
        self,
        *,
        session_id: str,
        manifest: dict[str, Any],
        scan_plan: dict[str, Any],
        recovery_report: dict[str, Any],
        resume_decision: dict[str, Any],
        resume_attempts: dict[str, Any],
        read_only: bool = False,
        role: str = 'operator',
    ) -> dict[str, Any]:
        execution_state = self._derive_execution_state(recovery_report)
        contact_state = self._derive_contact_state(recovery_report, resume_decision)
        plan_state = 'execution_plan_loaded' if scan_plan else 'preview_plan_ready'
        resume_mode = str(
            resume_decision.get('resume_mode')
            or resume_attempts.get('summary', {}).get('latest_mode')
            or ('initial_start' if scan_plan else '*')
        )
        snapshot = self.policy_service.snapshot(
            execution_state,
            role=role,
            read_only=read_only,
            contact_state=contact_state,
            plan_state=plan_state,
            resume_mode=resume_mode,
        )
        decisions = dict(snapshot.get('decisions', {}))
        return {
            'generated_at': now_text(),
            'session_id': session_id,
            'policy_version': str(snapshot.get('policy_version', self.policy_service.catalog().get('policy_version', 'command_state_policy_v2'))),
            'execution_state': execution_state,
            'contact_state': contact_state,
            'plan_state': plan_state,
            'resume_mode': resume_mode,
            'role': role,
            'read_only': read_only,
            'source_artifacts': {
                'manifest': 'meta/manifest.json',
                'scan_plan': 'meta/scan_plan.json',
                'resume_decision': 'meta/resume_decision.json',
                'resume_attempts': 'derived/session/resume_attempts.json',
                'recovery_report': 'export/recovery_report.json',
            },
            'decision_count': len(decisions),
            'decisions': decisions,
            'plan_hash': str(scan_plan.get('plan_hash') or manifest.get('scan_plan_hash', '')),
            'schema': 'session/command_policy_snapshot_v1.schema.json',
        }

    @staticmethod
    def _derive_execution_state(recovery_report: dict[str, Any]) -> str:
        latest = str(recovery_report.get('summary', {}).get('latest_recovery_state', 'IDLE'))
        if latest == 'ESTOP_LATCHED':
            return 'ESTOP_LATCHED'
        if latest == 'CONTROLLED_RETRACT':
            return 'RECOVERY_RETRACT'
        if latest == 'HOLDING':
            return 'PAUSED_HOLD'
        return 'PATH_VALIDATED'

    @staticmethod
    def _derive_contact_state(recovery_report: dict[str, Any], resume_decision: dict[str, Any]) -> str:
        required = str(resume_decision.get('required_contact_state', ''))
        if required:
            return required
        latest = str(recovery_report.get('summary', {}).get('latest_recovery_state', 'IDLE'))
        if latest in {'CONTROLLED_RETRACT', 'HOLDING'}:
            return 'CONTACT_UNSTABLE'
        if latest == 'ESTOP_LATCHED':
            return 'CONTACT_LOST'
        return 'CONTACT_STABLE'
