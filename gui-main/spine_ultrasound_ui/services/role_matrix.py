from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    COMMAND_GROUPS: dict[str, set[str]] = {
        "control": {"connect_robot", "disconnect_robot", "power_on", "power_off", "set_auto_mode", "set_manual_mode", "validate_setup", "lock_session", "load_scan_plan", "approach_prescan", "seek_contact", "start_scan", "go_home"},
        "recovery": {"pause_scan", "resume_scan", "safe_retreat", "clear_fault", "emergency_stop"},
        "review": set(),
        "export": set(),
    }

    def __init__(self) -> None:
        self._roles = {
            "operator": RolePolicy("operator", True, True, ("control", "recovery", "export"), True),
            "researcher": RolePolicy("researcher", True, True, tuple(), True),
            "reviewer": RolePolicy("reviewer", False, True, tuple(), True),
            "service": RolePolicy("service", True, True, ("control", "recovery"), False),
            "admin": RolePolicy("admin", True, True, ("control", "recovery", "export"), True),
            "read_only": RolePolicy("read_only", False, True, tuple(), False),
        }

    def catalog(self) -> dict[str, Any]:
        return {
            "roles": {name: policy.to_dict() for name, policy in sorted(self._roles.items())},
            "command_groups": {name: sorted(commands) for name, commands in self.COMMAND_GROUPS.items()},
        }

    def policy_for(self, role: str) -> RolePolicy:
        return self._roles.get(role.strip().lower(), self._roles["read_only"])

    def can_issue_command(self, role: str, command: str) -> bool:
        policy = self.policy_for(role)
        allowed = set().union(*(self.COMMAND_GROUPS.get(group, set()) for group in policy.command_groups))
        return command in allowed

    def can_read_category(self, role: str, category: str) -> bool:
        policy = self.policy_for(role)
        if category == "runtime":
            return policy.runtime_read
        if category == "session":
            return policy.session_read
        return False
