from __future__ import annotations

"""Canonical runtime command catalog.

This module centralizes command metadata that must stay aligned across the
Python validation layer, headless/API entrypoints, and the C++ runtime command
surface. The exported structures intentionally preserve the legacy compatibility
surface used by higher layers.
"""

from copy import deepcopy
from typing import Any

COMMAND_SPECS: dict[str, dict[str, Any]] = {
    "connect_robot": {"required_payload_fields": [], "state_preconditions": ["BOOT", "DISCONNECTED"], "capability_claim": "hardware_lifecycle_write"},
    "disconnect_robot": {"required_payload_fields": [], "state_preconditions": ["BOOT", "DISCONNECTED", "CONNECTED", "POWERED", "AUTO_READY", "FAULT", "ESTOP"], "capability_claim": "hardware_lifecycle_write"},
    "power_on": {"required_payload_fields": [], "state_preconditions": ["CONNECTED", "POWERED", "AUTO_READY"], "capability_claim": "hardware_lifecycle_write"},
    "power_off": {"required_payload_fields": [], "state_preconditions": ["CONNECTED", "POWERED", "AUTO_READY", "SESSION_LOCKED", "PATH_VALIDATED"], "capability_claim": "hardware_lifecycle_write"},
    "set_auto_mode": {"required_payload_fields": [], "state_preconditions": ["POWERED", "AUTO_READY"], "capability_claim": "hardware_lifecycle_write"},
    "set_manual_mode": {"required_payload_fields": [], "state_preconditions": ["CONNECTED", "POWERED", "AUTO_READY"], "capability_claim": "hardware_lifecycle_write"},
    "validate_setup": {"required_payload_fields": [], "state_preconditions": ["CONNECTED", "POWERED", "AUTO_READY", "SESSION_LOCKED", "PATH_VALIDATED"], "capability_claim": "runtime_validation"},
    "validate_scan_plan": {
        "required_payload_fields": ["scan_plan"],
        "required_nested_fields": {"scan_plan": ["plan_id", "segments", "plan_hash"]},
        "field_types": {"scan_plan": "object", "config_snapshot": "object"},
        "state_preconditions": ["AUTO_READY", "SESSION_LOCKED", "PATH_VALIDATED", "SCAN_COMPLETE"],
        "write_command": False,
        "capability_claim": "plan_compile",
        "legacy_aliases": ["compile_scan_plan"],
    },
    "compile_scan_plan": {
        "required_payload_fields": ["scan_plan"],
        "required_nested_fields": {"scan_plan": ["plan_id", "segments", "plan_hash"]},
        "field_types": {"scan_plan": "object", "config_snapshot": "object"},
        "state_preconditions": ["AUTO_READY", "SESSION_LOCKED", "PATH_VALIDATED", "SCAN_COMPLETE"],
        "write_command": False,
        "capability_claim": "plan_compile",
        "canonical_command": "validate_scan_plan",
    },
    "query_final_verdict": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "query_controller_log": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "query_rl_projects": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "query_path_lists": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_io_snapshot": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_safety_config": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_motion_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_register_snapshot": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_runtime_alignment": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_xmate_model_summary": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_sdk_runtime_config": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_identity_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_robot_family_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_vendor_boundary_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_clinical_mainline_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_session_freeze": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_authoritative_runtime_envelope": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_session_drift_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_hardware_lifecycle_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_rt_kernel_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_control_governance_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_controller_evidence": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_dual_state_machine_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_mainline_executor_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_recovery_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_safety_recovery_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_capability_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_model_authority_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_release_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_deployment_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "get_fault_injection_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False, "capability_claim": "runtime_read"},
    "inject_fault": {"required_payload_fields": ["fault_name"], "field_types": {"fault_name": "string"}, "state_preconditions": ["*"], "capability_claim": "fault_injection_write"},
    "clear_injected_faults": {"required_payload_fields": [], "state_preconditions": ["*"], "capability_claim": "fault_injection_write"},
    "lock_session": {
        "required_payload_fields": ["session_id", "session_dir", "config_snapshot", "device_roster", "scan_plan_hash"],
        "field_types": {"session_id": "string", "session_dir": "string", "config_snapshot": "object", "device_roster": "object", "scan_plan_hash": "string"},
        "state_preconditions": ["AUTO_READY"],
        "capability_claim": "session_freeze_write",
    },
    "load_scan_plan": {"required_payload_fields": ["scan_plan"], "required_nested_fields": {"scan_plan": ["plan_id", "segments"]}, "field_types": {"scan_plan": "object"}, "state_preconditions": ["SESSION_LOCKED", "PATH_VALIDATED", "SCAN_COMPLETE"], "capability_claim": "session_freeze_write"},
    "approach_prescan": {"required_payload_fields": [], "state_preconditions": ["PATH_VALIDATED"], "capability_claim": "rt_motion_write"},
    "seek_contact": {"required_payload_fields": [], "state_preconditions": ["PATH_VALIDATED", "APPROACHING", "PAUSED_HOLD", "RECOVERY_RETRACT"], "capability_claim": "rt_motion_write"},
    "start_scan": {"required_payload_fields": [], "state_preconditions": ["CONTACT_STABLE", "PAUSED_HOLD"], "capability_claim": "rt_motion_write"},
    "pause_scan": {"required_payload_fields": [], "state_preconditions": ["SCANNING"], "capability_claim": "rt_motion_write"},
    "resume_scan": {"required_payload_fields": [], "state_preconditions": ["PAUSED_HOLD"], "capability_claim": "rt_motion_write"},
    "safe_retreat": {"required_payload_fields": [], "state_preconditions": ["PATH_VALIDATED", "APPROACHING", "CONTACT_SEEKING", "CONTACT_STABLE", "SCANNING", "PAUSED_HOLD", "RECOVERY_RETRACT", "FAULT"], "capability_claim": "rt_motion_write"},
    "go_home": {"required_payload_fields": [], "state_preconditions": ["CONNECTED", "POWERED", "AUTO_READY", "PATH_VALIDATED", "SCAN_COMPLETE", "SEGMENT_ABORTED", "PLAN_ABORTED"], "capability_claim": "nrt_motion_write"},
    "run_rl_project": {"required_payload_fields": [], "state_preconditions": ["AUTO_READY", "SESSION_LOCKED", "PATH_VALIDATED", "SCAN_COMPLETE"], "capability_claim": "nrt_motion_write"},
    "pause_rl_project": {"required_payload_fields": [], "state_preconditions": ["AUTO_READY", "SCANNING", "PAUSED_HOLD", "SESSION_LOCKED", "PATH_VALIDATED", "SCAN_COMPLETE"], "capability_claim": "nrt_motion_write"},
    "enable_drag": {"required_payload_fields": [], "state_preconditions": ["CONNECTED"], "capability_claim": "nrt_motion_write"},
    "disable_drag": {"required_payload_fields": [], "state_preconditions": ["CONNECTED"], "capability_claim": "nrt_motion_write"},
    "replay_path": {"required_payload_fields": [], "state_preconditions": ["AUTO_READY", "PATH_VALIDATED", "SCAN_COMPLETE"], "capability_claim": "nrt_motion_write"},
    "start_record_path": {"required_payload_fields": [], "state_preconditions": ["CONNECTED"], "capability_claim": "nrt_motion_write"},
    "stop_record_path": {"required_payload_fields": [], "state_preconditions": ["CONNECTED"], "capability_claim": "nrt_motion_write"},
    "cancel_record_path": {"required_payload_fields": [], "state_preconditions": ["CONNECTED"], "capability_claim": "nrt_motion_write"},
    "save_record_path": {"required_payload_fields": [], "state_preconditions": ["CONNECTED"], "capability_claim": "nrt_motion_write"},
    "clear_fault": {"required_payload_fields": [], "state_preconditions": ["FAULT"], "capability_claim": "recovery_write"},
    "emergency_stop": {"required_payload_fields": [], "state_preconditions": ["*"], "capability_claim": "recovery_write"},
}

COMMANDS: set[str] = set(COMMAND_SPECS)


def command_specs() -> dict[str, dict[str, Any]]:
    return deepcopy(COMMAND_SPECS)


def command_names() -> set[str]:
    return set(COMMANDS)


def command_spec(command: str) -> dict[str, Any]:
    return deepcopy(COMMAND_SPECS[command])


def is_write_command(command: str) -> bool:
    spec = COMMAND_SPECS.get(command, {})
    return bool(spec.get("write_command", True))



def command_capability_claim(command: str) -> str:
    """Return the canonical capability claim for a runtime command.

    Args:
        command: Canonical runtime command name.

    Returns:
        Capability-claim token. Unknown commands map to an empty string.

    Raises:
        No exceptions are raised.
    """
    spec = COMMAND_SPECS.get(command, {})
    return str(spec.get("capability_claim", "")).strip()


def capability_claims() -> dict[str, list[str]]:
    """Build a reverse index of capability claims to commands.

    Returns:
        Mapping from capability-claim token to the sorted list of commands that
        require the claim.

    Raises:
        No exceptions are raised.
    """
    mapping: dict[str, list[str]] = {}
    for command, spec in COMMAND_SPECS.items():
        claim = str(spec.get("capability_claim", "")).strip()
        if not claim:
            continue
        mapping.setdefault(claim, []).append(command)
    return {claim: sorted(commands) for claim, commands in sorted(mapping.items())}


PLAN_COMPILE_COMMANDS: frozenset[str] = frozenset({"validate_scan_plan", "compile_scan_plan"})


def is_plan_compile_command(command: str) -> bool:
    """Return True when the command resolves to the runtime preflight/validate alias set."""
    return command in PLAN_COMPILE_COMMANDS
