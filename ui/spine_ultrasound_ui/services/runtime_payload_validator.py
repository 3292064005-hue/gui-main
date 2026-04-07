from __future__ import annotations

"""Canonical runtime payload validator."""

from typing import Any

from spine_ultrasound_ui.services.runtime_command_catalog import COMMAND_SPECS, COMMANDS


def _matches_expected_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "string":
        return isinstance(value, str) and bool(value.strip())
    return True


def validate_command_payload(command: str, payload: dict[str, Any] | None = None) -> None:
    if command not in COMMANDS:
        raise ValueError(f"unsupported command: {command}")
    payload = payload or {}
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    spec = COMMAND_SPECS[command]
    missing = [field for field in spec.get("required_payload_fields", []) if field not in payload]
    if missing:
        raise ValueError(f"{command} payload missing required fields: {', '.join(missing)}")
    for field_name, expected_type in spec.get("field_types", {}).items():
        if field_name in payload and not _matches_expected_type(payload[field_name], expected_type):
            raise ValueError(f"{command} payload field '{field_name}' must be a non-empty {expected_type}")
    for field_name, required_nested in spec.get("required_nested_fields", {}).items():
        nested_payload = payload.get(field_name)
        if not isinstance(nested_payload, dict):
            raise ValueError(f"{command} payload field '{field_name}' must be an object")
        missing_nested = [nested_field for nested_field in required_nested if nested_field not in nested_payload]
        if missing_nested:
            raise ValueError(f"{command} payload field '{field_name}' missing required fields: {', '.join(missing_nested)}")
