from __future__ import annotations

"""Canonical runtime command catalog backed by a shared manifest.

The JSON manifest under ``schemas/runtime_command_manifest.json`` is the single
source of truth for runtime command metadata consumed by Python validation,
headless/API policy checks, and generated C++ registry artifacts. This module
keeps the historical ``COMMAND_SPECS``/``COMMANDS`` API stable while exposing
additional helpers for canonical-command and alias resolution.
"""

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

_SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"
_MANIFEST_PATH = _SCHEMA_ROOT / "runtime_command_manifest.json"
_COMPAT_MANIFEST_PATH = _SCHEMA_ROOT / "runtime_command_compat_manifest.json"


class RuntimeCommandCatalogError(RuntimeError):
    """Raised when the shared runtime command manifest is malformed."""


def _load_compat_manifest() -> dict[str, dict[str, Any]]:
    """Load retired alias metadata kept outside the active command surface.

    Retired aliases are intentionally not merged into ``COMMAND_SPECS``. The
    returned mapping exists only for migration diagnostics and explicit retired
    command errors; it must not be used for dispatch, role policy, payload
    validation, generated C++ contracts, or capability claims.
    """
    try:
        payload = json.loads(_COMPAT_MANIFEST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:  # pragma: no cover - configuration error
        raise RuntimeCommandCatalogError(f"runtime command compat manifest is not valid JSON: {_COMPAT_MANIFEST_PATH}") from exc
    aliases = payload.get("retired_aliases", [])
    if not isinstance(aliases, list):  # pragma: no cover - configuration error
        raise RuntimeCommandCatalogError("runtime command compat manifest must contain a retired_aliases list")
    resolved: dict[str, dict[str, Any]] = {}
    for item in aliases:
        if not isinstance(item, dict):  # pragma: no cover - configuration error
            raise RuntimeCommandCatalogError("each retired alias entry must be a JSON object")
        name = str(item.get("name", "")).strip()
        if not name:  # pragma: no cover - configuration error
            raise RuntimeCommandCatalogError("retired alias entries require a non-empty name")
        alias = {str(key): deepcopy(value) for key, value in item.items() if key != "name"}
        alias.setdefault("deprecation_stage", "retired")
        alias.setdefault("alias_kind", "retired")
        alias.setdefault("retired_from_active_manifest", True)
        resolved[name] = alias
    return resolved


def _load_manifest() -> dict[str, Any]:
    try:
        payload = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - configuration error
        raise RuntimeCommandCatalogError(f"runtime command manifest not found: {_MANIFEST_PATH}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - configuration error
        raise RuntimeCommandCatalogError(f"runtime command manifest is not valid JSON: {_MANIFEST_PATH}") from exc
    if not isinstance(payload, dict):  # pragma: no cover - configuration error
        raise RuntimeCommandCatalogError("runtime command manifest root must be a JSON object")
    commands = payload.get("commands")
    if not isinstance(commands, list):  # pragma: no cover - configuration error
        raise RuntimeCommandCatalogError("runtime command manifest must contain a 'commands' list")
    specs: dict[str, dict[str, Any]] = {}
    for item in commands:
        if not isinstance(item, dict):  # pragma: no cover - configuration error
            raise RuntimeCommandCatalogError("each runtime command entry must be a JSON object")
        name = str(item.get("name", "")).strip()
        if not name:  # pragma: no cover - configuration error
            raise RuntimeCommandCatalogError("runtime command entries require a non-empty 'name'")
        spec = {str(key): deepcopy(value) for key, value in item.items() if key != "name"}
        spec.setdefault("required_payload_fields", [])
        spec.setdefault("required_nested_fields", {})
        spec.setdefault("field_types", {})
        spec.setdefault("state_preconditions", [])
        spec.setdefault("write_command", True)
        spec.setdefault("capability_claim", "")
        spec.setdefault("canonical_command", name)
        spec.setdefault("alias_kind", "canonical")
        spec.setdefault("legacy_aliases", [])
        spec.setdefault("handler_group", "")
        spec.setdefault("deprecation_stage", "")
        spec.setdefault("removal_target", "")
        spec.setdefault("replacement_command", "")
        spec.setdefault("compatibility_note", "")
        specs[name] = spec
    return {
        "schema_version": int(payload.get("schema_version", 1) or 1),
        "commands": specs,
    }


_MANIFEST = _load_manifest()
SCHEMA_VERSION: int = int(_MANIFEST["schema_version"])
COMMAND_SPECS: dict[str, dict[str, Any]] = _MANIFEST["commands"]
COMMANDS: set[str] = set(COMMAND_SPECS)
RETIRED_ALIAS_SPECS: dict[str, dict[str, Any]] = _load_compat_manifest()
RETIRED_ALIASES: set[str] = set(RETIRED_ALIAS_SPECS)
_CANONICAL_TO_ALIASES: dict[str, list[str]] = {}
for _command_name, _command_spec in COMMAND_SPECS.items():
    canonical = str(_command_spec.get("canonical_command", _command_name)).strip() or _command_name
    if canonical != _command_name:
        _CANONICAL_TO_ALIASES.setdefault(canonical, []).append(_command_name)
for _aliases in _CANONICAL_TO_ALIASES.values():
    _aliases.sort()


def catalog_schema_version() -> int:
    """Return the schema version of the shared runtime command manifest."""
    return SCHEMA_VERSION


def catalog_copy() -> dict[str, dict[str, Any]]:
    """Return a deep copy of the resolved runtime command specs."""
    return deepcopy(COMMAND_SPECS)


def command_names() -> set[str]:
    """Return the registered active runtime command names."""
    return set(COMMANDS)


def retired_alias_names() -> set[str]:
    """Return retired command aliases kept only for migration diagnostics."""
    return set(RETIRED_ALIASES)


def is_retired_command_alias(command: str) -> bool:
    """Return whether ``command`` is a retired alias outside active dispatch."""
    return command in RETIRED_ALIAS_SPECS


def is_retired_alias(command: str) -> bool:
    """Backward-compatible alias for retired command checks."""
    return is_retired_command_alias(command)


def retired_alias_spec(command: str) -> dict[str, Any]:
    """Return retired alias metadata for migration and error reporting.

    Raises:
        KeyError: If ``command`` is not a retired alias.
    """
    return deepcopy(RETIRED_ALIAS_SPECS[command])


def retired_alias_rejection(command: str) -> str:
    """Build a deterministic rejection message for an active-surface alias.

    The function does not translate or dispatch retired aliases. It only gives
    callers a stable diagnostic that points to the canonical replacement.
    """
    spec = RETIRED_ALIAS_SPECS.get(command)
    if spec is None:
        return f"unsupported command: {command}"
    replacement = str(spec.get("replacement_command") or spec.get("canonical_command") or "").strip()
    if replacement:
        return f"retired command alias: {command}; use {replacement}"
    return f"retired command alias: {command}"


def command_spec(command: str) -> dict[str, Any]:
    """Return a deep copy of one command spec.

    Args:
        command: Runtime command name.

    Returns:
        Deep-copied command specification dictionary.

    Raises:
        KeyError: If the command is not registered.
    """
    return deepcopy(COMMAND_SPECS[command])


def canonical_command_name(command: str) -> str:
    """Return the canonical command name for ``command``.

    Unknown commands are returned unchanged so callers can report the original
    token in error paths without synthesizing a new alias.
    """
    spec = COMMAND_SPECS.get(command, {})
    return str(spec.get("canonical_command", command)).strip() or command


def command_alias_kind(command: str) -> str:
    """Return the alias classification for ``command``.

    Returns one of ``canonical``, ``deprecated_alias``, or ``shim_only`` for
    known commands and an empty string for unknown commands.
    """
    spec = COMMAND_SPECS.get(command, {})
    return str(spec.get("alias_kind", "")).strip()


def canonical_aliases(command: str) -> tuple[str, ...]:
    """Return active compatibility aliases registered for a canonical command.

    Retired aliases are excluded by design. Use ``retired_aliases_for`` when a
    migration report needs to enumerate removed names.
    """
    canonical = canonical_command_name(command)
    return tuple(_CANONICAL_TO_ALIASES.get(canonical, ()))


def retired_aliases_for(command: str) -> tuple[str, ...]:
    """Return retired aliases whose replacement resolves to ``command``."""
    normalized = canonical_command_name(command)
    matches = []
    for alias, spec in RETIRED_ALIAS_SPECS.items():
        replacement = str(spec.get("replacement_command") or spec.get("canonical_command") or "").strip()
        if replacement == normalized:
            matches.append(alias)
    return tuple(sorted(matches))


def command_handler_group(command: str) -> str:
    """Return the generated handler-group token for a runtime command."""
    spec = COMMAND_SPECS.get(command, {})
    return str(spec.get("handler_group", "")).strip()


def command_deprecation_metadata(command: str) -> dict[str, str]:
    """Return structured deprecation metadata for a runtime command.

    Empty strings are returned for canonical commands or unknown commands.
    """
    spec = COMMAND_SPECS.get(command, {})
    return {
        "deprecation_stage": str(spec.get("deprecation_stage", "")).strip(),
        "removal_target": str(spec.get("removal_target", "")).strip(),
        "replacement_command": str(spec.get("replacement_command", "")).strip(),
        "compatibility_note": str(spec.get("compatibility_note", "")).strip(),
    }


def is_deprecated_alias(command: str) -> bool:
    """Return ``True`` when a command entry is a deprecated compatibility alias."""
    return command_alias_kind(command) == "deprecated_alias"


def is_shim_only_alias(command: str) -> bool:
    """Return ``True`` when a command entry is retained only as a transport shim."""
    return command_alias_kind(command) == "shim_only"


def active_command_names() -> set[str]:
    """Return the active dispatchable runtime command names.

    The active manifest is already canonical-only for retired aliases, so this
    helper is an explicit mirror of ``command_names`` rather than a filtered
    compatibility view.
    """
    return set(COMMANDS)


def is_write_command(command: str) -> bool:
    """Return whether ``command`` mutates the runtime control plane.

    Retired aliases keep the compatibility-manifest value so diagnostics can
    distinguish read-only migration aliases from unknown fail-closed commands.
    Unknown commands remain fail-closed as write-like commands.
    """
    if command in RETIRED_ALIAS_SPECS:
        return bool(RETIRED_ALIAS_SPECS[command].get("write_command", False))
    spec = COMMAND_SPECS.get(command)
    if spec is None:
        return True
    return bool(spec.get("write_command", True))


def command_capability_claim(command: str) -> str:
    """Return the capability-claim token for ``command``."""
    spec = COMMAND_SPECS.get(command, {})
    return str(spec.get("capability_claim", "")).strip()


def capability_claims(*, include_shims: bool = False) -> dict[str, list[str]]:
    """Build a reverse index of capability claims to active commands.

    Args:
        include_shims: Include transport-only compatibility aliases when true.

    Returns:
        Capability-claim mapping. By default, shim-only aliases are excluded so
        active role, readiness, and UI surfaces do not re-promote retired names.
    """
    mapping: dict[str, list[str]] = {}
    for command, spec in COMMAND_SPECS.items():
        if not include_shims and str(spec.get("alias_kind", "canonical")).strip() == "shim_only":
            continue
        claim = str(spec.get("capability_claim", "")).strip()
        if not claim:
            continue
        mapping.setdefault(claim, []).append(command)
    return {claim: sorted(commands) for claim, commands in sorted(mapping.items())}


PLAN_COMPILE_COMMANDS: frozenset[str] = frozenset(
    command for command in COMMAND_SPECS if canonical_command_name(command) == "validate_scan_plan"
)


def is_plan_compile_command(command: str) -> bool:
    """Return ``True`` when a command resolves to the scan-plan validation family."""
    return command in PLAN_COMPILE_COMMANDS
