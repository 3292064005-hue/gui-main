from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.utils import now_text


class ResumeExecutionService:
    def evaluate_attempt_outcomes(
        self,
        *,
        session_id: str,
        resume_decision: dict[str, Any],
        resume_attempts: dict[str, Any],
        contract_consistency: dict[str, Any],
        command_policy_catalog: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        attempts = list(resume_attempts.get('attempts', []))
        required_hash = str(resume_decision.get('required_plan_hash', resume_decision.get('plan_hash', '')))
        hash_ok = bool(contract_consistency.get('hash_alignment', {}).get('scan_plan_hash_match', False))
        policy_map = {str(item.get('command', '')): dict(item) for item in list((command_policy_catalog or {}).get('policies', []))}
        required_policy = list(resume_decision.get('required_command_policy', []))
        outcomes: list[dict[str, Any]] = []
        failures = 0
        for idx, attempt in enumerate(attempts, start=1):
            command_sequence = list(attempt.get('command_sequence') or resume_decision.get('command_sequence', []))
            success = bool(attempt.get('ok', False))
            outcome = str(attempt.get('outcome', 'success' if success else 'failed'))
            if not success:
                failures += 1
            verification = self._verify_sequence(
                command_sequence,
                policy_map=policy_map,
                required_core_state=str(resume_decision.get('required_core_state', 'AUTO_READY')),
                required_contact_state=str(resume_decision.get('required_contact_state', 'NO_CONTACT')),
                required_resume_mode=str(resume_decision.get('resume_mode', 'manual_review')),
            )
            fallback_mode = self._fallback_mode(outcome, failure_count=failures, requested_fallback=str(resume_decision.get('fallback_resume_mode', 'manual_review')))
            outcomes.append({
                'resume_attempt_id': str(attempt.get('resume_attempt_id', f'resume_attempt_{idx:03d}')),
                'resume_token': str(attempt.get('resume_token', resume_decision.get('resume_token', ''))),
                'mode': str(attempt.get('resume_mode', resume_decision.get('resume_mode', 'manual_review'))),
                'required_resume_mode': str(resume_decision.get('resume_mode', 'manual_review')),
                'required_checkpoint_granularity': str(resume_decision.get('required_checkpoint_granularity', resume_decision.get('checkpoint_granularity', 'segment_boundary'))),
                'command_sequence': command_sequence,
                'required_command_policy': required_policy,
                'required_plan_hash': required_hash,
                'plan_hash_verified': hash_ok,
                'sequence_outcome': outcome,
                'sequence_outcome_contract': dict(resume_decision.get('sequence_outcome_contract', {})),
                'fallback_resume_mode': fallback_mode,
                'command_policy_verified': verification['verified'],
                'precondition_failures': verification['failures'],
                'required_core_state': str(resume_decision.get('required_core_state', 'AUTO_READY')),
                'required_contact_state': str(resume_decision.get('required_contact_state', 'NO_CONTACT')),
                'message': str(attempt.get('message', '')),
                'ts_ns': int(attempt.get('ts_ns', 0) or 0),
            })
        return {
            'generated_at': now_text(),
            'session_id': session_id,
            'summary': {
                'attempt_count': len(outcomes),
                'failed_attempt_count': failures,
                'blocked_attempt_count': sum(1 for item in outcomes if item.get('sequence_outcome') == 'blocked'),
                'final_mode': str(resume_decision.get('resume_mode', 'manual_review')),
                'required_plan_hash': required_hash,
                'plan_hash_verified': hash_ok,
                'latest_outcome': outcomes[-1]['sequence_outcome'] if outcomes else 'not_attempted',
            },
            'outcomes': outcomes,
        }

    @staticmethod
    def _verify_sequence(command_sequence: list[dict[str, Any]], *, policy_map: dict[str, dict[str, Any]], required_core_state: str, required_contact_state: str, required_resume_mode: str) -> dict[str, Any]:
        failures: list[str] = []
        for item in command_sequence:
            command = str(item.get('command', ''))
            if not command:
                failures.append('missing_command')
                continue
            policy = policy_map.get(command)
            if policy is None:
                failures.append(f'{command}:missing_policy')
                continue
            step_state = str(item.get('required_state', ''))
            step_contact = str(item.get('required_contact_state', '')) or required_contact_state
            step_resume_mode = str(item.get('required_resume_mode', '')) or required_resume_mode
            allowed_states = set(str(state) for state in policy.get('allowed_states', []))
            if step_state and '*' not in allowed_states and step_state not in allowed_states:
                failures.append(f'{command}:state_mismatch')
            contact_states = set(str(state) for state in policy.get('required_contact_state', ['*']))
            if step_contact and '*' not in contact_states and step_contact not in contact_states:
                failures.append(f'{command}:contact_mismatch')
            resume_modes = set(str(state) for state in policy.get('required_resume_mode', ['*']))
            if step_resume_mode and '*' not in resume_modes and step_resume_mode not in resume_modes:
                failures.append(f'{command}:resume_mode_mismatch')
        return {'verified': not failures, 'failures': failures}

    @staticmethod
    def _fallback_mode(outcome: str, *, failure_count: int, requested_fallback: str) -> str:
        if outcome == 'success':
            return 'none'
        if failure_count >= 2:
            return 'full_restart'
        if outcome == 'blocked':
            return requested_fallback if requested_fallback and requested_fallback != 'manual_review' else 'segment_restart'
        if requested_fallback and requested_fallback != 'manual_review':
            return requested_fallback
        return 'reacquire_contact_then_resume'
