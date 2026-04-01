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
    "connect_robot": {"required_payload_fields": [], "state_preconditions": ["BOOT", "DISCONNECTED"]},
    "disconnect_robot": {"required_payload_fields": [], "state_preconditions": ["BOOT", "DISCONNECTED", "CONNECTED", "POWERED", "AUTO_READY", "FAULT", "ESTOP"]},
    "power_on": {"required_payload_fields": [], "state_preconditions": ["CONNECTED", "POWERED", "AUTO_READY"]},
    "power_off": {"required_payload_fields": [], "state_preconditions": ["CONNECTED", "POWERED", "AUTO_READY", "SESSION_LOCKED", "PATH_VALIDATED"]},
    "set_auto_mode": {"required_payload_fields": [], "state_preconditions": ["POWERED", "AUTO_READY"]},
    "set_manual_mode": {"required_payload_fields": [], "state_preconditions": ["CONNECTED", "POWERED", "AUTO_READY"]},
    "validate_setup": {"required_payload_fields": [], "state_preconditions": ["CONNECTED", "POWERED", "AUTO_READY", "SESSION_LOCKED", "PATH_VALIDATED"]},
    "compile_scan_plan": {
        "required_payload_fields": ["scan_plan"],
        "required_nested_fields": {"scan_plan": ["plan_id", "segments", "plan_hash"]},
        "field_types": {"scan_plan": "object", "config_snapshot": "object"},
        "state_preconditions": ["AUTO_READY", "SESSION_LOCKED", "PATH_VALIDATED", "SCAN_COMPLETE"],
        "write_command": False,
    },
    "query_final_verdict": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "query_controller_log": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "query_rl_projects": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "query_path_lists": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_io_snapshot": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_safety_config": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_motion_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_register_snapshot": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_runtime_alignment": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_xmate_model_summary": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_sdk_runtime_config": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_identity_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_robot_family_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_vendor_boundary_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_clinical_mainline_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_session_freeze": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_authoritative_runtime_envelope": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_session_drift_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_hardware_lifecycle_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_rt_kernel_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_control_governance_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_controller_evidence": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_dual_state_machine_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_mainline_executor_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_recovery_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_safety_recovery_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_capability_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_model_authority_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_release_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_deployment_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "get_fault_injection_contract": {"required_payload_fields": [], "state_preconditions": ["*"], "write_command": False},
    "inject_fault": {"required_payload_fields": ["fault_name"], "field_types": {"fault_name": "string"}, "state_preconditions": ["*"]},
    "clear_injected_faults": {"required_payload_fields": [], "state_preconditions": ["*"]},
    "lock_session": {
        "required_payload_fields": ["session_id", "session_dir", "config_snapshot", "device_roster", "scan_plan_hash"],
        "field_types": {"session_id": "string", "session_dir": "string", "config_snapshot": "object", "device_roster": "object", "scan_plan_hash": "string"},
        "state_preconditions": ["AUTO_READY"],
    },
    "load_scan_plan": {"required_payload_fields": ["scan_plan"], "required_nested_fields": {"scan_plan": ["plan_id", "segments"]}, "field_types": {"scan_plan": "object"}, "state_preconditions": ["SESSION_LOCKED", "PATH_VALIDATED", "SCAN_COMPLETE"]},
    "approach_prescan": {"required_payload_fields": [], "state_preconditions": ["PATH_VALIDATED"]},
    "seek_contact": {"required_payload_fields": [], "state_preconditions": ["PATH_VALIDATED", "APPROACHING", "PAUSED_HOLD", "RECOVERY_RETRACT"]},
    "start_scan": {"required_payload_fields": [], "state_preconditions": ["CONTACT_STABLE", "PAUSED_HOLD"]},
    "pause_scan": {"required_payload_fields": [], "state_preconditions": ["SCANNING"]},
    "resume_scan": {"required_payload_fields": [], "state_preconditions": ["PAUSED_HOLD"]},
    "safe_retreat": {"required_payload_fields": [], "state_preconditions": ["PATH_VALIDATED", "APPROACHING", "CONTACT_SEEKING", "CONTACT_STABLE", "SCANNING", "PAUSED_HOLD", "RECOVERY_RETRACT", "FAULT"]},
    "go_home": {"required_payload_fields": [], "state_preconditions": ["CONNECTED", "POWERED", "AUTO_READY", "PATH_VALIDATED", "SCAN_COMPLETE", "SEGMENT_ABORTED", "PLAN_ABORTED"]},
    "clear_fault": {"required_payload_fields": [], "state_preconditions": ["FAULT"]},
    "emergency_stop": {"required_payload_fields": [], "state_preconditions": ["*"]},
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
