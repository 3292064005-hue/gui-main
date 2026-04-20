from __future__ import annotations

"""Typed runtime-command contract surface.

This module turns the manifest-backed runtime command catalog into a richer,
read-only contract representation that can be consumed by protocol exports,
validation logic, repository gates, documentation tooling, and generated C++
artifacts without each caller manually walking raw JSON dictionaries.
"""

from dataclasses import asdict, dataclass
from typing import Any

from spine_ultrasound_ui.services.runtime_command_catalog import (
    COMMAND_SPECS,
    catalog_schema_version,
    command_alias_kind,
    command_capability_claim,
    command_handler_group,
    command_names,
    command_spec,
    is_write_command,
)


_REPLY_ENVELOPE_FIELDS = ("ok", "message", "request_id", "data", "protocol_version")


@dataclass(frozen=True)
class RuntimeCommandFieldContract:
    """Typed description of one payload or reply field.

    Attributes:
        name: Field name in the JSON payload/reply object.
        required: Whether the field must exist.
        field_type: Optional semantic type token from the manifest.
        nested_required_fields: Required keys when the field is a nested object.
        array_item_type: Optional semantic type token for array elements.
        array_item_required_fields: Required keys when array elements are objects.

    Boundary behavior:
        Type tokens remain additive strings instead of enums so the manifest can
        evolve without breaking consumers that only need a stable descriptive surface.
    """

    name: str
    required: bool
    field_type: str
    nested_required_fields: tuple[str, ...]
    array_item_type: str = ""
    array_item_required_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeCommandRequestContract:
    """Typed request contract for one runtime command."""

    required_fields: tuple[str, ...]
    fields: tuple[RuntimeCommandFieldContract, ...]


_AUTHORITY_CONTEXT_FIELD = RuntimeCommandFieldContract(
    name="_command_context",
    required=False,
    field_type="object",
    nested_required_fields=(),
)


def _command_requires_authority_context(*, command: str, capability_claim: str, write_command: bool) -> bool:
    """Return whether a command contract should expose runtime authority context.

    The context remains additive and optional at the manifest-contract layer so
    compatibility callers do not fail payload validation prematurely. Runtime
    dispatch still consumes the normalized context when present and remains the
    final authority arbiter for write and plan-compile requests.
    """

    if write_command:
        return True
    return capability_claim == "plan_compile"


@dataclass(frozen=True)
class RuntimeCommandResponseContract:
    """Typed response contract for one runtime command."""

    envelope_fields: tuple[str, ...]
    data_contract_token: str
    data_required_fields: tuple[str, ...]
    data_fields: tuple[RuntimeCommandFieldContract, ...]
    read_only: bool


@dataclass(frozen=True)
class RuntimeCommandGuardContract:
    """Manifest-backed guard matrix entry for one runtime command."""

    allowed_states: tuple[str, ...]
    lane: str


@dataclass(frozen=True)
class RuntimeCommandDispatchContract:
    """Generated handler-interface token for one runtime command."""

    canonical_command: str
    handler_group: str


@dataclass(frozen=True)
class RuntimeCommandContract:
    """Typed view of one manifest-backed runtime command contract."""

    name: str
    canonical_command: str
    alias_kind: str
    write_command: bool
    capability_claim: str
    handler_group: str
    state_preconditions: tuple[str, ...]
    fields: tuple[RuntimeCommandFieldContract, ...]
    deprecation_stage: str
    removal_target: str
    replacement_command: str
    compatibility_note: str
    request_contract: RuntimeCommandRequestContract
    response_contract: RuntimeCommandResponseContract
    guard_contract: RuntimeCommandGuardContract
    dispatch_contract: RuntimeCommandDispatchContract


@dataclass(frozen=True)
class RuntimeCommandContractsDocument:
    """Serializable document for the full typed contract catalog."""

    schema_version: int
    commands: tuple[RuntimeCommandContract, ...]


def _lane_for_capability_claim(capability_claim: str) -> str:
    if capability_claim == "rt_motion_write":
        return "rt_control"
    if capability_claim in {"runtime_read", "runtime_validation", "plan_compile"}:
        return "query"
    return "command"




_RESPONSE_REQUIRED_FIELDS_BY_COMMAND: dict[str, tuple[str, ...]] = {
    "query_controller_log": ("logs",),
    "query_rl_projects": ("projects", "status"),
    "query_path_lists": ("paths", "drag"),
    "query_final_verdict": ("final_verdict",),
    "validate_scan_plan": ("final_verdict",),
    "compile_scan_plan": ("final_verdict",),
    "get_authoritative_runtime_envelope": ("authoritative_runtime_envelope_present", "control_authority", "final_verdict"),
    "acquire_control_lease": ("summary_state", "detail", "lease"),
    "renew_control_lease": ("summary_state", "detail", "lease"),
    "release_control_lease": ("summary_state", "detail"),
    "get_io_snapshot": ("di", "do", "ai", "ao", "registers", "xpanel_vout_mode"),
    "get_register_snapshot": ("registers",),
    "get_safety_config": ("collision_detection_enabled", "soft_limit_enabled"),
    "get_motion_contract": ("rt_mode", "sdk_boundary_units", "rt_contract", "nrt_contract"),
    "get_runtime_alignment": ("runtime_source", "sdk_available", "robot_family"),
    "get_xmate_model_summary": ("model_source", "kinematics_ready", "dynamics_ready"),
    "get_sdk_runtime_config": ("remote_ip", "local_ip", "rt_mode", "runtime_config_contract_digest", "runtime_config_schema_version", "rt_phase_contract"),
    "get_identity_contract": ("robot_model", "sdk_robot_class", "axis_count"),
    "get_clinical_mainline_contract": ("robot_model", "clinical_mainline_mode", "required_sequence"),
    "get_session_freeze": ("session_locked", "session_id", "plan_hash", "freeze_consistent", "strict_runtime_freeze_gate"),
    "get_controller_evidence": ("runtime_source", "last_event", "last_transition"),
    "get_fault_injection_contract": ("summary_state", "detail", "active_faults"),
}


def _response_required_fields(name: str, data_contract_token: str) -> tuple[str, ...]:
    explicit = _RESPONSE_REQUIRED_FIELDS_BY_COMMAND.get(name)
    if explicit is not None:
        return explicit
    if name.startswith("get_") and data_contract_token.endswith("_contract"):
        return ("summary_state", "detail")
    return tuple(filter(None, (data_contract_token,)))




_RESPONSE_FIELD_SPECS_BY_COMMAND: dict[str, tuple[RuntimeCommandFieldContract, ...]] = {
    "query_controller_log": (RuntimeCommandFieldContract("logs", True, "array", (), array_item_type="object", array_item_required_fields=("level", "source", "message")),),
    "query_rl_projects": (
        RuntimeCommandFieldContract("projects", True, "array", (), array_item_type="object", array_item_required_fields=("name", "tasks")),
        RuntimeCommandFieldContract("status", True, "string", ()),
    ),
    "query_path_lists": (
        RuntimeCommandFieldContract("paths", True, "array", (), array_item_type="object", array_item_required_fields=("name", "rate", "points")),
        RuntimeCommandFieldContract("drag", True, "object", ("enabled", "space", "type")),
    ),
    "query_final_verdict": (RuntimeCommandFieldContract("final_verdict", True, "object", ("accepted", "authoritative", "reason")),),
    "validate_scan_plan": (RuntimeCommandFieldContract("final_verdict", True, "object", ("accepted", "authoritative", "reason")),),
    "compile_scan_plan": (RuntimeCommandFieldContract("final_verdict", True, "object", ("accepted", "authoritative", "reason")),),
    "get_authoritative_runtime_envelope": (
        RuntimeCommandFieldContract("authoritative_runtime_envelope_present", True, "boolean", ()),
        RuntimeCommandFieldContract("control_authority", True, "object", ("summary_state", "detail")),
        RuntimeCommandFieldContract("final_verdict", True, "object", ("accepted", "authoritative", "reason")),
    ),
    "acquire_control_lease": (
        RuntimeCommandFieldContract("summary_state", True, "string", ()),
        RuntimeCommandFieldContract("detail", True, "string", ()),
        RuntimeCommandFieldContract("lease", True, "object", ("lease_id", "actor_id", "workspace", "role")),
        RuntimeCommandFieldContract("control_authority", False, "object", ("summary_state", "detail")),
    ),
    "renew_control_lease": (
        RuntimeCommandFieldContract("summary_state", True, "string", ()),
        RuntimeCommandFieldContract("detail", True, "string", ()),
        RuntimeCommandFieldContract("lease", True, "object", ("lease_id", "actor_id", "workspace", "role")),
        RuntimeCommandFieldContract("control_authority", False, "object", ("summary_state", "detail")),
    ),
    "release_control_lease": (
        RuntimeCommandFieldContract("summary_state", True, "string", ()),
        RuntimeCommandFieldContract("detail", True, "string", ()),
        RuntimeCommandFieldContract("control_authority", False, "object", ("summary_state", "detail")),
    ),
    "get_io_snapshot": (
        RuntimeCommandFieldContract("di", True, "object", ()),
        RuntimeCommandFieldContract("do", True, "object", ()),
        RuntimeCommandFieldContract("ai", True, "object", ()),
        RuntimeCommandFieldContract("ao", True, "object", ()),
        RuntimeCommandFieldContract("registers", True, "object", ()),
        RuntimeCommandFieldContract("xpanel_vout_mode", True, "string", ()),
    ),
    "get_register_snapshot": (RuntimeCommandFieldContract("registers", True, "object", ()),),
    "get_safety_config": (
        RuntimeCommandFieldContract("collision_detection_enabled", True, "boolean", ()),
        RuntimeCommandFieldContract("soft_limit_enabled", True, "boolean", ()),
    ),
    "get_motion_contract": (
        RuntimeCommandFieldContract("rt_mode", True, "string", ()),
        RuntimeCommandFieldContract("sdk_boundary_units", True, "object", ()),
        RuntimeCommandFieldContract("rt_contract", True, "object", ()),
        RuntimeCommandFieldContract("nrt_contract", True, "object", ()),
    ),
    "get_runtime_alignment": (
        RuntimeCommandFieldContract("runtime_source", True, "string", ()),
        RuntimeCommandFieldContract("sdk_available", True, "boolean", ()),
        RuntimeCommandFieldContract("robot_family", True, "string", ()),
    ),
    "get_xmate_model_summary": (
        RuntimeCommandFieldContract("model_source", True, "string", ()),
        RuntimeCommandFieldContract("kinematics_ready", True, "boolean", ()),
        RuntimeCommandFieldContract("dynamics_ready", True, "boolean", ()),
    ),
    "get_sdk_runtime_config": (
        RuntimeCommandFieldContract("remote_ip", True, "string", ()),
        RuntimeCommandFieldContract("local_ip", True, "string", ()),
        RuntimeCommandFieldContract("rt_mode", True, "string", ()),
        RuntimeCommandFieldContract("runtime_config_contract_digest", True, "string", ()),
        RuntimeCommandFieldContract("runtime_config_schema_version", True, "string", ()),
        RuntimeCommandFieldContract("rt_phase_contract", True, "object", ()),
    ),
    "get_identity_contract": (
        RuntimeCommandFieldContract("robot_model", True, "string", ()),
        RuntimeCommandFieldContract("sdk_robot_class", True, "string", ()),
        RuntimeCommandFieldContract("axis_count", True, "integer", ()),
    ),
    "get_clinical_mainline_contract": (
        RuntimeCommandFieldContract("robot_model", True, "string", ()),
        RuntimeCommandFieldContract("clinical_mainline_mode", True, "boolean", ()),
        RuntimeCommandFieldContract("required_sequence", True, "array", (), array_item_type="string"),
    ),
    "get_session_freeze": (
        RuntimeCommandFieldContract("session_locked", True, "boolean", ()),
        RuntimeCommandFieldContract("session_id", True, "string", ()),
        RuntimeCommandFieldContract("plan_hash", True, "string", ()),
        RuntimeCommandFieldContract("freeze_consistent", True, "boolean", ()),
        RuntimeCommandFieldContract("strict_runtime_freeze_gate", True, "string", ()),
        RuntimeCommandFieldContract("session_freeze_policy", False, "string", ()),
        RuntimeCommandFieldContract("frozen_execution_critical_fields", False, "array", (), array_item_type="string"),
        RuntimeCommandFieldContract("frozen_evidence_only_fields", False, "array", (), array_item_type="string"),
        RuntimeCommandFieldContract("recheck_on_start_procedure", False, "boolean", ()),
        RuntimeCommandFieldContract("live_binding_established", False, "boolean", ()),
        RuntimeCommandFieldContract("control_source_exclusive", False, "boolean", ()),
        RuntimeCommandFieldContract("network_healthy", False, "boolean", ()),
    ),
    "get_controller_evidence": (
        RuntimeCommandFieldContract("runtime_source", True, "string", ()),
        RuntimeCommandFieldContract("last_event", True, "string", ()),
        RuntimeCommandFieldContract("last_transition", True, "string", ()),
    ),
    "get_fault_injection_contract": (
        RuntimeCommandFieldContract("summary_state", True, "string", ()),
        RuntimeCommandFieldContract("detail", True, "string", ()),
        RuntimeCommandFieldContract("active_faults", True, "array", (), array_item_type="string"),
    ),
}


def _response_field_contracts(name: str, data_required_fields: tuple[str, ...]) -> tuple[RuntimeCommandFieldContract, ...]:
    explicit = _RESPONSE_FIELD_SPECS_BY_COMMAND.get(name)
    if explicit is not None:
        return explicit
    return tuple(RuntimeCommandFieldContract(field, True, "", ()) for field in data_required_fields)


_DATA_CONTRACT_BY_COMMAND: dict[str, str] = {
    "query_final_verdict": "final_verdict",
    "validate_scan_plan": "final_verdict",
    "compile_scan_plan": "final_verdict",
    "get_authoritative_runtime_envelope": "authoritative_runtime_envelope",
    "acquire_control_lease": "control_authority",
    "renew_control_lease": "control_authority",
    "release_control_lease": "control_authority",
    "get_session_freeze": "session_freeze",
    "get_control_governance_contract": "control_governance_contract",
    "get_controller_evidence": "controller_evidence",
    "get_deployment_contract": "deployment_contract",
    "get_release_contract": "release_contract",
    "get_rt_kernel_contract": "rt_kernel_contract",
    "get_hardware_lifecycle_contract": "hardware_lifecycle_contract",
    "get_capability_contract": "capability_contract",
    "get_model_authority_contract": "model_authority_contract",
    "get_fault_injection_contract": "fault_injection_contract",
}


def _response_contract_token(name: str, capability_claim: str, handler_group: str) -> str:
    explicit = _DATA_CONTRACT_BY_COMMAND.get(name)
    if explicit:
        return explicit
    if capability_claim == "runtime_read":
        if name.startswith("get_"):
            return name.removeprefix("get_")
        if name.startswith("query_"):
            return name.removeprefix("query_")
        return "runtime_read"
    if capability_claim in {"plan_compile", "runtime_validation"}:
        return "validation_report"
    if capability_claim == "rt_motion_write":
        return "rt_command_ack"
    if handler_group == "handleSessionCommand":
        return "session_command_ack"
    if handler_group == "handleExecutionCommand":
        return "execution_command_ack"
    return "command_ack"


def contract_for(command: str) -> RuntimeCommandContract:
    """Return the typed contract for a runtime command.

    Args:
        command: Registered runtime command name.

    Returns:
        Typed runtime-command contract.

    Raises:
        KeyError: If the command is not registered.
    """

    spec = command_spec(command)
    required_fields = tuple(str(item) for item in spec.get("required_payload_fields", []))
    nested_required = {
        str(key): tuple(str(item) for item in value)
        for key, value in dict(spec.get("required_nested_fields", {})).items()
    }
    field_types = {str(key): str(value) for key, value in dict(spec.get("field_types", {})).items()}
    field_names = sorted(set(required_fields) | set(nested_required) | set(field_types))
    fields = tuple(
        RuntimeCommandFieldContract(
            name=field_name,
            required=field_name in required_fields,
            field_type=field_types.get(field_name, ""),
            nested_required_fields=nested_required.get(field_name, ()),
        )
        for field_name in field_names
    )
    capability_claim = command_capability_claim(command)
    handler_group = command_handler_group(command)
    write_command = bool(spec.get("write_command", True))
    request_fields = list(fields)
    if _command_requires_authority_context(command=command, capability_claim=capability_claim, write_command=write_command) and all(field.name != "_command_context" for field in request_fields):
        request_fields.append(_AUTHORITY_CONTEXT_FIELD)
    request_contract = RuntimeCommandRequestContract(
        required_fields=required_fields,
        fields=tuple(request_fields),
    )
    data_contract_token = _response_contract_token(command, capability_claim, handler_group)
    response_required_fields = _response_required_fields(command, data_contract_token)
    response_contract = RuntimeCommandResponseContract(
        envelope_fields=_REPLY_ENVELOPE_FIELDS,
        data_contract_token=data_contract_token,
        data_required_fields=response_required_fields,
        data_fields=_response_field_contracts(command, response_required_fields),
        read_only=not is_write_command(command),
    )
    guard_contract = RuntimeCommandGuardContract(
        allowed_states=tuple(str(item) for item in spec.get("state_preconditions", [])),
        lane=_lane_for_capability_claim(capability_claim),
    )
    dispatch_contract = RuntimeCommandDispatchContract(
        canonical_command=str(spec.get("canonical_command", command)).strip() or command,
        handler_group=handler_group,
    )
    return RuntimeCommandContract(
        name=command,
        canonical_command=str(spec.get("canonical_command", command)).strip() or command,
        alias_kind=command_alias_kind(command) or "canonical",
        write_command=write_command,
        capability_claim=capability_claim,
        handler_group=handler_group,
        state_preconditions=guard_contract.allowed_states,
        fields=fields,
        deprecation_stage=str(spec.get("deprecation_stage", "")).strip(),
        removal_target=str(spec.get("removal_target", "")).strip(),
        replacement_command=str(spec.get("replacement_command", "")).strip(),
        compatibility_note=str(spec.get("compatibility_note", "")).strip(),
        request_contract=request_contract,
        response_contract=response_contract,
        guard_contract=guard_contract,
        dispatch_contract=dispatch_contract,
    )


def contract_document() -> RuntimeCommandContractsDocument:
    """Return the full typed runtime-command contract document."""

    return RuntimeCommandContractsDocument(
        schema_version=catalog_schema_version(),
        commands=tuple(contract_for(command) for command in sorted(command_names())),
    )


def export_contract_document() -> dict[str, Any]:
    """Return a JSON-serializable dictionary for the typed contract catalog."""

    document = contract_document()
    commands: list[dict[str, Any]] = []
    for command_contract in document.commands:
        payload = {
            **asdict(command_contract),
            "state_preconditions": list(command_contract.state_preconditions),
            "fields": [
                {
                    **asdict(field_contract),
                    "nested_required_fields": list(field_contract.nested_required_fields),
                    "array_item_required_fields": list(field_contract.array_item_required_fields),
                }
                for field_contract in command_contract.fields
            ],
            "request_contract": {
                "required_fields": list(command_contract.request_contract.required_fields),
                "fields": [
                    {
                        **asdict(field_contract),
                        "nested_required_fields": list(field_contract.nested_required_fields),
                        "array_item_required_fields": list(field_contract.array_item_required_fields),
                    }
                    for field_contract in command_contract.request_contract.fields
                ],
            },
            "response_contract": {
                "envelope_fields": list(command_contract.response_contract.envelope_fields),
                "data_contract_token": command_contract.response_contract.data_contract_token,
                "data_required_fields": list(command_contract.response_contract.data_required_fields),
                "data_fields": [
                    {
                        **asdict(field_contract),
                        "nested_required_fields": list(field_contract.nested_required_fields),
                        "array_item_required_fields": list(field_contract.array_item_required_fields),
                    }
                    for field_contract in command_contract.response_contract.data_fields
                ],
                "read_only": command_contract.response_contract.read_only,
            },
            "guard_contract": {
                "allowed_states": list(command_contract.guard_contract.allowed_states),
                "lane": command_contract.guard_contract.lane,
            },
            "dispatch_contract": {
                "canonical_command": command_contract.dispatch_contract.canonical_command,
                "handler_group": command_contract.dispatch_contract.handler_group,
            },
        }
        commands.append(payload)
    return {
        "schema_version": document.schema_version,
        "commands": commands,
    }


__all__ = [
    "RuntimeCommandFieldContract",
    "RuntimeCommandRequestContract",
    "RuntimeCommandResponseContract",
    "RuntimeCommandGuardContract",
    "RuntimeCommandDispatchContract",
    "RuntimeCommandContract",
    "RuntimeCommandContractsDocument",
    "contract_for",
    "contract_document",
    "export_contract_document",
]
