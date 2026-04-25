from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.services.ipc_protocol import COMMAND_SPECS
from spine_ultrasound_ui.services.role_matrix import RoleMatrix
from spine_ultrasound_ui.utils import now_text


@dataclass(frozen=True)
class CommandStatePolicy:
    command: str
    allowed_states: tuple[str, ...]
    blocked_states: tuple[str, ...]
    reject_reason_code: str
    fallback_action: str
    recovery_escalation: str
    ui_visibility: str
    role_write_gate: tuple[str, ...]
    required_contact_state: tuple[str, ...] = ('*',)
    required_plan_state: tuple[str, ...] = ('*',)
    required_resume_mode: tuple[str, ...] = ('*',)
    policy_version: str = 'command_state_policy_v2'

    def to_dict(self) -> dict[str, Any]:
        return {
            'command': self.command,
            'allowed_states': list(self.allowed_states),
            'blocked_states': list(self.blocked_states),
            'reject_reason_code': self.reject_reason_code,
            'fallback_action': self.fallback_action,
            'recovery_escalation': self.recovery_escalation,
            'ui_visibility': self.ui_visibility,
            'role_write_gate': list(self.role_write_gate),
            'required_contact_state': list(self.required_contact_state),
            'required_plan_state': list(self.required_plan_state),
            'required_resume_mode': list(self.required_resume_mode),
            'policy_version': self.policy_version,
        }


class CommandStatePolicyService:
    _KNOWN_STATES = (
        'BOOT', 'DISCONNECTED', 'CONNECTED', 'POWERED', 'AUTO_READY', 'SESSION_LOCKED', 'PATH_VALIDATED',
        'APPROACHING', 'CONTACT_SEEKING', 'CONTACT_STABLE', 'SCANNING', 'PAUSED_HOLD', 'RECOVERY_RETRACT',
        'RETREATING', 'SCAN_COMPLETE', 'FAULT', 'ESTOP_LATCHED',
    )

    _FALLBACKS = {
        'validate_setup': ('retry_validation', 'monitor'),
        'seek_contact': ('safe_retreat', 'reacquire_contact'),
        'start_procedure': ('seek_contact', 'resume_gate'),
        'resume_scan': ('seek_contact', 'resume_gate'),
        'stop_scan': ('post_scan_home', 'scan_stop'),
        'safe_retreat': ('safe_retreat', 'recovery_retract'),
        'clear_fault': ('manual_review', 'fault_clearance'),
        'emergency_stop': ('estop_latched', 'estop'),
        'load_scan_plan': ('reload_plan', 'plan_integrity_gate'),
    }

    _REQUIREMENTS = {
        'lock_session': {'required_plan_state': ('preview_plan_ready',)},
        'load_scan_plan': {'required_plan_state': ('selected_execution_plan', 'validated_plan')},
        'seek_contact': {
            'required_contact_state': ('NO_CONTACT', 'CONTACT_LOST', 'CONTACT_DEGRADED', 'CONTACT_UNSTABLE', 'CONTACT_STABLE'),
            'required_plan_state': ('execution_plan_loaded',),
        },
        'start_procedure': {
            'contact_states': {'CONTACT_STABLE'},
            'plan_states': {'PATH_VALIDATED', 'PLAN_LOADED'},
            'resume_modes': {'FRESH_START', 'RESUME_ALLOWED'},
            'roles': {'operator'},
            'write_command': True,
            'blocked_reason_code': 'start_procedure_blocked',
        },
        'resume_scan': {
            'required_contact_state': ('CONTACT_STABLE',),
            'required_plan_state': ('execution_plan_loaded',),
            'required_resume_mode': ('exact_waypoint_resume', 'segment_restart', 'reacquire_contact_then_resume'),
        },
        'stop_scan': {
            'required_plan_state': ('execution_plan_loaded', 'validated_plan'),
        },
        'safe_retreat': {'required_plan_state': ('execution_plan_loaded', 'validated_plan')},
    }

    def __init__(self, role_matrix: RoleMatrix | None = None) -> None:
        self.role_matrix = role_matrix or RoleMatrix()

    def catalog(self) -> dict[str, Any]:
        policies = [self._policy_for(command).to_dict() for command in sorted(COMMAND_SPECS)]
        return {
            'generated_at': now_text(),
            'schema': 'runtime/command_state_policy_v1.schema.json',
            'policy_version': 'command_state_policy_v2',
            'policies': policies,
            'known_states': list(self._KNOWN_STATES),
        }

    def policy_map(self) -> dict[str, dict[str, Any]]:
        return {item['command']: item for item in self.catalog()['policies']}

    def allowed(self, command: str, execution_state: str, *, role: str = 'operator', read_only: bool = False) -> bool:
        return self.decision(command, execution_state, role=role, read_only=read_only)['allowed']

    def decision(
        self,
        command: str,
        execution_state: str,
        *,
        role: str = 'operator',
        read_only: bool = False,
        contact_state: str = '*',
        plan_state: str = '*',
        resume_mode: str = '*',
    ) -> dict[str, Any]:
        policy = self._policy_for(command)
        if read_only:
            return {'allowed': False, 'reason': 'read_only_mode', 'policy': policy.to_dict()}
        if role not in policy.role_write_gate:
            return {'allowed': False, 'reason': 'role_gate', 'policy': policy.to_dict()}
        if '*' not in policy.allowed_states and execution_state not in policy.allowed_states:
            return {'allowed': False, 'reason': policy.reject_reason_code, 'policy': policy.to_dict()}
        if '*' not in policy.required_contact_state and contact_state not in policy.required_contact_state:
            return {'allowed': False, 'reason': 'contact_state_gate', 'policy': policy.to_dict()}
        if '*' not in policy.required_plan_state and plan_state not in policy.required_plan_state:
            return {'allowed': False, 'reason': 'plan_state_gate', 'policy': policy.to_dict()}
        if '*' not in policy.required_resume_mode and resume_mode not in policy.required_resume_mode:
            return {'allowed': False, 'reason': 'resume_mode_gate', 'policy': policy.to_dict()}
        return {'allowed': True, 'reason': 'allowed', 'policy': policy.to_dict()}

    def snapshot(
        self,
        execution_state: str,
        *,
        role: str = 'operator',
        read_only: bool = False,
        contact_state: str = '*',
        plan_state: str = '*',
        resume_mode: str = '*',
    ) -> dict[str, Any]:
        decisions = {
            command: self.decision(
                command,
                execution_state,
                role=role,
                read_only=read_only,
                contact_state=contact_state,
                plan_state=plan_state,
                resume_mode=resume_mode,
            )
            for command in sorted(COMMAND_SPECS)
        }
        return {
            'generated_at': now_text(),
            'execution_state': execution_state,
            'contact_state': contact_state,
            'plan_state': plan_state,
            'resume_mode': resume_mode,
            'role': role,
            'read_only': read_only,
            'decisions': decisions,
        }

    def _policy_for(self, command: str) -> CommandStatePolicy:
        spec = COMMAND_SPECS[command]
        allowed_states = tuple(str(item) for item in spec.get('state_preconditions', [])) or ('*',)
        blocked_states = tuple(sorted(state for state in self._KNOWN_STATES if '*' not in allowed_states and state not in allowed_states))
        fallback_action, recovery_escalation = self._FALLBACKS.get(command, ('manual_review', 'none'))
        role_gate = tuple(sorted(role for role in self.role_matrix.catalog()['roles'] if self.role_matrix.can_issue_command(role, command)))
        requirements = self._REQUIREMENTS.get(command, {})
        return CommandStatePolicy(
            command=command,
            allowed_states=allowed_states,
            blocked_states=blocked_states,
            reject_reason_code=f'{command}_state_gate',
            fallback_action=fallback_action,
            recovery_escalation=recovery_escalation,
            ui_visibility='shim_only' if str(spec.get('alias_kind', '')).strip() == 'shim_only' else 'write_control',
            role_write_gate=role_gate,
            required_contact_state=tuple(requirements.get('required_contact_state', ('*',))),
            required_plan_state=tuple(requirements.get('required_plan_state', ('*',))),
            required_resume_mode=tuple(requirements.get('required_resume_mode', ('*',))),
        )
