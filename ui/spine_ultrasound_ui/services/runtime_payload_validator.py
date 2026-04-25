from __future__ import annotations

"""Canonical runtime payload validator."""

from typing import Any

from spine_ultrasound_ui.services.runtime_command_catalog import COMMANDS, retired_alias_rejection
from spine_ultrasound_ui.services.runtime_command_contracts import contract_for


def _matches_expected_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "string":
        return isinstance(value, str) and bool(value.strip())
    if expected_type in {"integer", "int"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type in {"double", "float", "number"}:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type in {"boolean", "bool"}:
        return isinstance(value, bool)
    return True


def validate_command_payload(command: str, payload: dict[str, Any] | None = None) -> None:
    if command not in COMMANDS:
        raise ValueError(retired_alias_rejection(command))
    payload = payload or {}
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    contract = contract_for(command)
    missing = [field.name for field in contract.fields if field.required and field.name not in payload]
    if missing:
        raise ValueError(f"{command} payload missing required fields: {', '.join(missing)}")
    for field in contract.fields:
        if field.name in payload and field.field_type and not _matches_expected_type(payload[field.name], field.field_type):
            raise ValueError(f"{command} payload field '{field.name}' must be a non-empty {field.field_type}")
        if field.nested_required_fields:
            nested_payload = payload.get(field.name)
            if not isinstance(nested_payload, dict):
                raise ValueError(f"{command} payload field '{field.name}' must be an object")
            missing_nested = [nested_field for nested_field in field.nested_required_fields if nested_field not in nested_payload]
            if missing_nested:
                raise ValueError(f"{command} payload field '{field.name}' missing required fields: {', '.join(missing_nested)}")
