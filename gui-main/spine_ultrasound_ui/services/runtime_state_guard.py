from __future__ import annotations

from spine_ultrasound_ui.services.runtime_command_catalog import COMMAND_SPECS


def allowed_states_for(command: str) -> list[str]:
    return list(COMMAND_SPECS.get(command, {}).get("state_preconditions", []))


def is_state_allowed(command: str, state: str) -> bool:
    allowed = allowed_states_for(command)
    if not allowed or "*" in allowed:
        return True
    return str(state) in allowed
