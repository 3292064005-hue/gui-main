from __future__ import annotations

from typing import Any
from uuid import uuid4

from spine_ultrasound_ui.utils import now_ns, now_text


class SessionResumeService:
    def evaluate(
        self,
        *,
        session_id: str,
        manifest: dict[str, Any],
        resume_state: dict[str, Any],
        recovery_report: dict[str, Any],
        incidents: dict[str, Any],
        integrity: dict[str, Any],
    ) -> dict[str, Any]:
        blockers: list[str] = []
        evidence_refs: list[dict[str, Any]] = []
        verification_checks = [
            'validate_integrity', 'check_contract_consistency', 'verify_plan_hash', 'verify_execution_state', 'verify_contact_state'
        ]
        pre_resume_actions: list[str] = ['validate_integrity', 'reload_plan', 'check_contract_consistency']

        integrity_ok = bool(integrity.get('summary', {}).get('integrity_ok', False))
        if not integrity_ok:
            blockers.append('artifact_integrity_failed')
            evidence_refs.append({'kind': 'integrity', 'warnings': integrity.get('warnings', [])})

        latest_recovery = str(recovery_report.get('summary', {}).get('latest_recovery_state', 'IDLE'))
        if latest_recovery == 'ESTOP_LATCHED':
            blockers.append('estop_latched')

        incident_items = list(incidents.get('incidents', []))
        risky_types = {str(item.get('incident_type', '')) for item in incident_items}
        recommended_patch_segments = sorted({int(item.get('segment_id', 0) or 0) for item in incident_items if int(item.get('segment_id', 0) or 0) > 0})
        patch_candidate_windows = self._patch_candidate_windows(incident_items)
        if 'force_excursion_incident' in risky_types:
            evidence_refs.append({'kind': 'incident', 'incident_type': 'force_excursion_incident'})
            pre_resume_actions.append('seek_contact')
        if 'contact_instability_incident' in risky_types:
            pre_resume_actions.extend(['seek_contact', 'probe_patch'])

        cursor = {'segment_id': int(resume_state.get('last_successful_segment', 0) or 0), 'waypoint_index': int(resume_state.get('last_successful_waypoint', 0) or 0)}
        if cursor['segment_id'] <= 0:
            blockers.append('no_resume_checkpoint')
        if cursor['waypoint_index'] <= 0 and cursor['segment_id'] > 0:
            pre_resume_actions.append('rewind_segment_boundary')

        allowed = not blockers and bool(resume_state.get('resume_ready', False))
        if not allowed:
            mode = 'full_restart' if blockers else 'manual_review'
        elif patch_candidate_windows:
            mode = 'patch_before_resume'
        elif 'force_excursion_incident' in risky_types or latest_recovery in {'CONTROLLED_RETRACT', 'HOLDING'}:
            mode = 'reacquire_contact_then_resume'
        elif cursor['waypoint_index'] > 1:
            mode = 'exact_waypoint_resume'
        else:
            mode = 'segment_restart'

        required_core_state = self._required_core_state(mode, allowed=allowed)
        required_contact_state = self._required_contact_state(mode)
        checkpoint_granularity = str(resume_state.get('resume_checkpoint_policy', 'segment_boundary'))
        restore_scope = checkpoint_granularity if mode not in {'full_restart', 'manual_review'} else 'session'
        if mode == 'patch_before_resume':
            pre_resume_actions.extend(['apply_patch_plan', 'seek_contact'])
        elif mode == 'reacquire_contact_then_resume':
            pre_resume_actions.append('seek_contact')

        required_plan_hash = str(resume_state.get('plan_hash', manifest.get('scan_plan_hash', '')))
        command_sequence = self._command_sequence(
            mode=mode,
            cursor=cursor,
            required_core_state=required_core_state,
            required_contact_state=required_contact_state,
            plan_hash=required_plan_hash,
            patch_candidate_windows=patch_candidate_windows,
        )
        command_preconditions = {
            'required_core_state': required_core_state,
            'required_contact_state': required_contact_state,
            'required_plan_hash': required_plan_hash,
            'resume_checkpoint_policy': checkpoint_granularity,
        }
        if not allowed:
            verification_checks.append('manual_review_required')
        risk_level = 'high' if blockers or latest_recovery == 'ESTOP_LATCHED' else ('medium' if risky_types else 'low')
        resume_token = f'resume_{session_id}_{uuid4().hex[:10]}' if allowed else ''
        resume_attempt_id = f'resume_attempt_{uuid4().hex[:8]}' if allowed else ''
        required_command_policy = [str(step.get('command', '')) for step in command_sequence if str(step.get('command', ''))]
        fallback_resume_mode = self._fallback_mode(mode, allowed=allowed, blockers=blockers)
        deadline_ns = now_ns() + 300_000_000_000 if allowed else 0
        sequence_outcome_contract = {
            'success_terminal_states': ['SCANNING', 'PAUSED_HOLD'],
            'blocked_terminal_states': ['PAUSED_HOLD', 'RECOVERY_RETRACT', 'FAULT'],
            'failure_terminal_states': ['FAULT', 'ESTOP_LATCHED', 'PLAN_ABORTED'],
            'required_acknowledgements': ['plan_hash_verified', 'command_policy_verified', 'contact_state_verified'],
        }
        return {
            'generated_at': now_text(),
            'session_id': session_id,
            'resume_allowed': allowed,
            'mode': mode,
            'resume_mode': mode,
            'blocking_reasons': blockers,
            'resume_from': cursor,
            'resume_cursor': cursor,
            'pre_resume_actions': list(dict.fromkeys(pre_resume_actions)),
            'verification_checks': verification_checks,
            'recommended_patch_segments': recommended_patch_segments,
            'patch_candidate_windows': patch_candidate_windows,
            'risk_level': risk_level,
            'resume_risk': risk_level,
            'plan_hash': required_plan_hash,
            'required_plan_hash': required_plan_hash,
            'resume_checkpoint_policy': checkpoint_granularity,
            'required_checkpoint_granularity': checkpoint_granularity,
            'checkpoint_granularity': checkpoint_granularity,
            'restore_scope': restore_scope,
            'required_core_state': required_core_state,
            'required_contact_state': required_contact_state,
            'required_command_policy': required_command_policy,
            'command_preconditions': command_preconditions,
            'command_sequence': command_sequence,
            'resume_token': resume_token,
            'resume_attempt_id': resume_attempt_id,
            'resume_deadline_ns': deadline_ns,
            'fallback_resume_mode': fallback_resume_mode,
            'sequence_outcome_contract': sequence_outcome_contract,
            'evidence_refs': evidence_refs,
        }

    @staticmethod
    def _required_core_state(mode: str, *, allowed: bool) -> str:
        if not allowed:
            return 'AUTO_READY'
        if mode == 'exact_waypoint_resume':
            return 'PAUSED_HOLD'
        if mode in {'segment_restart', 'patch_before_resume', 'reacquire_contact_then_resume'}:
            return 'PATH_VALIDATED'
        return 'AUTO_READY'

    @staticmethod
    def _required_contact_state(mode: str) -> str:
        if mode in {'reacquire_contact_then_resume', 'patch_before_resume', 'exact_waypoint_resume', 'segment_restart'}:
            return 'CONTACT_STABLE'
        return 'NO_CONTACT'

    @staticmethod
    def _fallback_mode(mode: str, *, allowed: bool, blockers: list[str]) -> str:
        if blockers:
            return 'full_restart'
        if not allowed:
            return 'manual_review'
        if mode == 'exact_waypoint_resume':
            return 'segment_restart'
        if mode == 'segment_restart':
            return 'reacquire_contact_then_resume'
        if mode == 'reacquire_contact_then_resume':
            return 'patch_before_resume'
        if mode == 'patch_before_resume':
            return 'full_restart'
        return 'manual_review'

    @staticmethod
    def _command_sequence(*, mode: str, cursor: dict[str, int], required_core_state: str, required_contact_state: str, plan_hash: str, patch_candidate_windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        base = [{'command': 'validate_setup', 'required_state': required_core_state, 'required_plan_hash': plan_hash}]
        if mode in {'segment_restart', 'patch_before_resume', 'reacquire_contact_then_resume'}:
            base.append({'command': 'load_scan_plan', 'required_state': 'SESSION_LOCKED', 'required_plan_hash': plan_hash})
        if mode in {'reacquire_contact_then_resume', 'patch_before_resume'}:
            base.append({'command': 'seek_contact', 'required_contact_state': required_contact_state})
        if mode == 'patch_before_resume' and patch_candidate_windows:
            base.append({'command': 'load_scan_plan', 'payload_hint': {'patch_window_count': len(patch_candidate_windows)}, 'required_plan_hash': plan_hash})
            base.append({'command': 'start_scan', 'payload_hint': {'resume_from_segment': cursor.get('segment_id', 0)}, 'required_contact_state': 'CONTACT_STABLE'})
        elif mode == 'exact_waypoint_resume':
            base.append({'command': 'resume_scan', 'required_state': 'PAUSED_HOLD', 'payload_hint': {'segment_id': cursor.get('segment_id', 0), 'waypoint_index': cursor.get('waypoint_index', 0)}, 'required_contact_state': 'CONTACT_STABLE'})
        elif mode == 'segment_restart':
            base.append({'command': 'start_scan', 'payload_hint': {'segment_id': cursor.get('segment_id', 0)}, 'required_contact_state': 'CONTACT_STABLE'})
        elif mode == 'reacquire_contact_then_resume':
            base.append({'command': 'resume_scan', 'required_state': 'PAUSED_HOLD', 'payload_hint': {'segment_id': cursor.get('segment_id', 0)}, 'required_contact_state': 'CONTACT_STABLE'})
        return base

    @staticmethod
    def _patch_candidate_windows(incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        windows: list[dict[str, Any]] = []
        for idx, item in enumerate(incidents, start=1):
            segment_id = int(item.get('segment_id', 0) or 0)
            reason = str(item.get('incident_type', ''))
            if segment_id <= 0 or reason not in {'contact_instability_incident', 'force_excursion_incident', 'recording_degradation_incident'}:
                continue
            windows.append({
                'window_id': f'patch_{idx:03d}',
                'segment_id': segment_id,
                'source_reason': reason,
                'recommended_patch_mode': 'short_overlap_patch' if reason == 'recording_degradation_incident' else 'contact_reprobe_patch',
                'ts_ns': int(item.get('ts_ns', 0) or 0),
            })
        return windows
