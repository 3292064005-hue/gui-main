from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.services.runtime_command_catalog import capability_claims, command_capability_claim, is_shim_only_alias


@dataclass(frozen=True)
class RolePolicy:
    name: str
    runtime_read: bool
    session_read: bool
    command_groups: tuple[str, ...]
    export_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "runtime_read": self.runtime_read,
            "session_read": self.session_read,
            "command_groups": list(self.command_groups),
            "export_allowed": self.export_allowed,
        }


class RoleMatrix:
    """Role-to-command and role-to-capability policy matrix.

    The matrix keeps command-level compatibility while also exposing explicit
    capability-claim groups used by control-authority enforcement.
    """

    COMMAND_GROUPS: dict[str, set[str]] = {
        "control": {"connect_robot", "disconnect_robot", "power_on", "power_off", "set_auto_mode", "set_manual_mode", "validate_setup", "acquire_control_lease", "renew_control_lease", "release_control_lease", "lock_session", "load_scan_plan", "approach_prescan", "seek_contact", "start_procedure", "go_home", "run_rl_project", "pause_rl_project", "enable_drag", "disable_drag", "replay_path", "start_record_path", "stop_record_path", "cancel_record_path", "save_record_path", "validate_scan_plan"},
        "recovery": {"pause_scan", "resume_scan", "stop_scan", "safe_retreat", "clear_fault", "emergency_stop", "inject_fault", "clear_injected_faults"},
        "review": set(),
        "export": set(),
    }
    CLAIM_GROUPS: dict[str, set[str]] = {
        "control": {"control_authority_write", "hardware_lifecycle_write", "runtime_validation", "plan_compile", "session_freeze_write", "nrt_motion_write", "rt_motion_write"},
        "recovery": {"recovery_write", "fault_injection_write"},
        "review": {"plan_compile"},
        "export": set(),
    }

    def __init__(self) -> None:
        self._roles = {
            "operator": RolePolicy("operator", True, True, ("control", "recovery", "export"), True),
            "researcher": RolePolicy("researcher", True, True, ("review",), True),
            "qa": RolePolicy("qa", True, True, ("review",), True),
            "review": RolePolicy("review", True, True, ("review",), True),
            "reviewer": RolePolicy("reviewer", False, True, tuple(), True),
            "service": RolePolicy("service", True, True, ("control", "recovery"), False),
            "admin": RolePolicy("admin", True, True, ("control", "recovery", "export"), True),
            "read_only": RolePolicy("read_only", False, True, tuple(), False),
        }

    def catalog(self) -> dict[str, Any]:
        return {
            "roles": {name: policy.to_dict() for name, policy in sorted(self._roles.items())},
            "command_groups": {name: sorted(commands) for name, commands in self.COMMAND_GROUPS.items()},
            "claim_groups": {name: sorted(claims) for name, claims in self.CLAIM_GROUPS.items()},
            "command_capability_claims": capability_claims(),
        }

    def policy_for(self, role: str) -> RolePolicy:
        return self._roles.get(role.strip().lower(), self._roles["read_only"])

    def allowed_capability_claims(self, role: str) -> set[str]:
        policy = self.policy_for(role)
        allowed: set[str] = set()
        for group in policy.command_groups:
            allowed.update(self.CLAIM_GROUPS.get(group, set()))
        return allowed

    def can_claim(self, role: str, claim: str) -> bool:
        cleaned_claim = str(claim or "").strip()
        if not cleaned_claim:
            return True
        return cleaned_claim in self.allowed_capability_claims(role)

    def can_issue_command(self, role: str, command: str) -> bool:
        if is_shim_only_alias(command):
            return False
        policy = self.policy_for(role)
        allowed = set().union(*(self.COMMAND_GROUPS.get(group, set()) for group in policy.command_groups))
        if command in allowed:
            return True
        claim = command_capability_claim(command)
        return bool(claim) and self.can_claim(role, claim)

    def can_read_category(self, role: str, category: str) -> bool:
        policy = self.policy_for(role)
        if category == "runtime":
            return policy.runtime_read
        if category == "session":
            return policy.session_read
        return False
