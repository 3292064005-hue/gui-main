#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services.runtime_command_contracts import export_contract_document

MANIFEST_PATH = ROOT / "schemas" / "runtime_command_manifest.json"
CPP_MANIFEST_INC_PATH = ROOT / "cpp_robot_core" / "include" / "robot_core" / "generated_command_manifest.inc"
CPP_TYPED_CONTRACTS_INC_PATH = ROOT / "cpp_robot_core" / "include" / "robot_core" / "generated_runtime_command_contracts.inc"
CPP_TYPED_REQUEST_TYPES_PATH = ROOT / "cpp_robot_core" / "include" / "robot_core" / "generated_runtime_command_request_types.h"
CPP_TYPED_REQUEST_PARSERS_INC_PATH = ROOT / "cpp_robot_core" / "include" / "robot_core" / "generated_runtime_command_request_parsers.inc"
CPP_TYPED_HANDLER_DECLS_INC_PATH = ROOT / "cpp_robot_core" / "include" / "robot_core" / "generated_runtime_command_typed_handler_decls.inc"
CPP_TYPED_HANDLER_ADAPTERS_INC_PATH = ROOT / "cpp_robot_core" / "include" / "robot_core" / "generated_runtime_command_typed_handlers.inc"
PY_TYPED_CONTRACTS_PATH = ROOT / "spine_ultrasound_ui" / "contracts" / "generated" / "runtime_command_contracts.json"


def _state_signature(states: list[str]) -> str:
    return "|".join(str(item) for item in states)


def _field_type_token(field_type: str) -> str:
    normalized = str(field_type or "").strip().lower()
    if normalized == "string":
        return "RuntimeContractFieldType::String"
    if normalized == "object":
        return "RuntimeContractFieldType::Object"
    if normalized in {"integer", "int"}:
        return "RuntimeContractFieldType::Integer"
    if normalized in {"double", "float", "number"}:
        return "RuntimeContractFieldType::Double"
    if normalized in {"boolean", "bool"}:
        return "RuntimeContractFieldType::Boolean"
    if normalized in {"array", "list"}:
        return "RuntimeContractFieldType::Array"
    return "RuntimeContractFieldType::Any"


def _cpp_struct_name(command_name: str) -> str:
    return "".join(part.capitalize() for part in command_name.split("_")) + "Request"


def _cpp_base_type(field_type: str) -> str:
    normalized = str(field_type or "").strip().lower()
    if normalized in {"string", "object", "any", ""}:
        return "std::string"
    if normalized in {"integer", "int"}:
        return "int"
    if normalized in {"double", "float", "number"}:
        return "double"
    if normalized in {"boolean", "bool"}:
        return "bool"
    return "std::string"


def _cpp_default_value(field_type: str) -> str:
    normalized = str(field_type or "").strip().lower()
    if normalized in {"string", "object", "any", ""}:
        return '{}' 
    if normalized in {"integer", "int"}:
        return '{0}'
    if normalized in {"double", "float", "number"}:
        return '{0.0}'
    if normalized in {"boolean", "bool"}:
        return '{false}'
    return '{}'


def _cpp_getter_has(field_type: str, field_name: str) -> tuple[str, str]:
    normalized = str(field_type or "").strip().lower()
    if normalized == "string":
        return f'request.hasStringField("{field_name}")', f'request.stringField("{field_name}")'
    if normalized == "object":
        return f'request.hasObjectField("{field_name}")', f'request.objectFieldJson("{field_name}")'
    if normalized in {"integer", "int"}:
        return f'request.hasIntegerField("{field_name}")', f'request.intField("{field_name}")'
    if normalized in {"double", "float", "number"}:
        return f'request.hasDoubleField("{field_name}")', f'request.doubleField("{field_name}")'
    if normalized in {"boolean", "bool"}:
        return f'request.hasBooleanField("{field_name}")', f'request.boolField("{field_name}")'
    return f'false /* unsupported field type for {field_name} */', '{}'



def _cpp_typed_handler_method_name(command_name: str) -> str:
    return "handle" + "".join(part.capitalize() for part in command_name.split("_")) + "Typed"

def _write_cpp_manifest_include(manifest: dict) -> None:
    commands = list(manifest.get("commands", []))
    lines = [
        "// Generated from schemas/runtime_command_manifest.json. Do not edit manually.",
        "",
    ]
    for item in commands:
        lines.append(
            '      {{"{name}", {write_flag}, "{states}", "{claim}", "{canonical}", "{alias_kind}", "{handler_group}", "{deprecation_stage}", "{removal_target}", "{replacement_command}", "{compatibility_note}"}},'.format(
                name=str(item["name"]),
                write_flag="true" if bool(item.get("write_command", True)) else "false",
                states=_state_signature(list(item.get("state_preconditions", []))),
                claim=str(item.get("capability_claim", "")),
                canonical=str(item.get("canonical_command", item["name"])),
                alias_kind=str(item.get("alias_kind", "canonical")),
                handler_group=str(item.get("handler_group", "")),
                deprecation_stage=str(item.get("deprecation_stage", "")),
                removal_target=str(item.get("removal_target", "")),
                replacement_command=str(item.get("replacement_command", "")),
                compatibility_note=str(item.get("compatibility_note", "")),
            )
        )
    CPP_MANIFEST_INC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_cpp_typed_contracts_include(contract_document: dict) -> None:
    lines = [
        "// Generated from schemas/runtime_command_manifest.json via runtime_command_contracts.py. Do not edit manually.",
        "",
    ]
    for command in contract_document["commands"]:
        name = str(command["name"])
        fields = list(command.get("request_contract", {}).get("fields", []))
        response = dict(command.get("response_contract", {}))
        guard = dict(command.get("guard_contract", {}))
        dispatch = dict(command.get("dispatch_contract", {}))
        field_entries = []
        for field in fields:
            nested_signature = "|".join(str(item) for item in field.get("nested_required_fields", []))
            field_entries.append(
                '          {{"{name}", {required}, {field_type}, "{nested}", {array_item_type}, "{array_nested}"}}'.format(
                    name=str(field["name"]),
                    required="true" if bool(field.get("required", False)) else "false",
                    field_type=_field_type_token(str(field.get("field_type", ""))),
                    nested=nested_signature,
                    array_item_type=_field_type_token(str(field.get("array_item_type", ""))),
                    array_nested="|".join(str(item) for item in field.get("array_item_required_fields", [])),
                )
            )
        fields_block = "{\n" + (",\n".join(field_entries) + "\n" if field_entries else "") + "        }"
        envelope_fields = "|".join(str(item) for item in response.get("envelope_fields", []))
        allowed_states = "|".join(str(item) for item in guard.get("allowed_states", []))
        data_required_fields = "|".join(str(item) for item in response.get("data_required_fields", []))
        response_fields = list(response.get("data_fields", []))
        response_field_entries = []
        for field in response_fields:
            nested_signature = "|".join(str(item) for item in field.get("nested_required_fields", []))
            response_field_entries.append(
                '          {{"{name}", {required}, {field_type}, "{nested}", {array_item_type}, "{array_nested}"}}'.format(
                    name=str(field["name"]),
                    required="true" if bool(field.get("required", False)) else "false",
                    field_type=_field_type_token(str(field.get("field_type", ""))),
                    nested=nested_signature,
                    array_item_type=_field_type_token(str(field.get("array_item_type", ""))),
                    array_nested="|".join(str(item) for item in field.get("array_item_required_fields", [])),
                )
            )
        response_fields_block = "{\n" + (",\n".join(response_field_entries) + "\n" if response_field_entries else "") + "        }"
        lines.append(
            '      {{"{name}", RuntimeCommandRequestContract{{"{name}", {fields_block}}}, RuntimeCommandResponseContract{{"{name}", "{data_token}", "{data_required_fields}", {response_fields_block}, {read_only}, "{envelope_fields}"}}, RuntimeCommandGuardContract{{"{name}", "{allowed_states}", CommandRuntimeLane::{lane_enum}}}, RuntimeCommandDispatchContract{{"{name}", "{canonical}", "{handler_group}"}}}},'.format(
                name=name,
                fields_block=fields_block,
                data_token=str(response.get("data_contract_token", "")),
                data_required_fields=data_required_fields,
                response_fields_block=response_fields_block,
                read_only="true" if bool(response.get("read_only", False)) else "false",
                envelope_fields=envelope_fields,
                allowed_states=allowed_states,
                lane_enum={"command": "Command", "query": "Query", "rt_control": "RtControl"}.get(str(guard.get("lane", "command")), "Command"),
                canonical=str(dispatch.get("canonical_command", name)),
                handler_group=str(dispatch.get("handler_group", "")),
            )
        )
    CPP_TYPED_CONTRACTS_INC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_cpp_typed_request_types(contract_document: dict) -> None:
    lines = [
        "// Generated from schemas/runtime_command_manifest.json via runtime_command_contracts.py. Do not edit manually.",
        "#pragma once",
        "",
        "#include <optional>",
        "#include <string>",
        "#include <variant>",
        "",
        "namespace robot_core {",
        "",
    ]
    struct_names: list[str] = []
    for command in contract_document["commands"]:
        name = str(command["name"])
        struct_name = _cpp_struct_name(name)
        struct_names.append(struct_name)
        lines.append(f"struct {struct_name} {{")
        lines.append(f'  static constexpr const char* kCommand = "{name}";')
        fields = list(command.get("request_contract", {}).get("fields", []))
        required_fields = set(command.get("request_contract", {}).get("required_fields", []))
        if not fields:
            lines.append("};")
            lines.append("")
            continue
        for field in fields:
            field_name = str(field["name"])
            field_type = str(field.get("field_type", ""))
            base_type = _cpp_base_type(field_type)
            if field_name in required_fields:
                lines.append(f"  {base_type} {field_name}{_cpp_default_value(field_type)};")
            else:
                lines.append(f"  std::optional<{base_type}> {field_name};")
        lines.append("};")
        lines.append("")
    lines.append("using RuntimeTypedRequestVariant = std::variant<")
    for index, name in enumerate(struct_names):
        suffix = "," if index + 1 != len(struct_names) else ""
        lines.append(f"    {name}{suffix}")
    lines.append(">;")
    lines.append("")
    lines.append("}  // namespace robot_core")
    CPP_TYPED_REQUEST_TYPES_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_cpp_typed_request_parsers(contract_document: dict) -> None:
    lines = [
        "// Generated from schemas/runtime_command_manifest.json via runtime_command_contracts.py. Do not edit manually.",
        "",
    ]
    for command in contract_document["commands"]:
        name = str(command["name"])
        struct_name = _cpp_struct_name(name)
        lines.append(f'  if (command == "{name}") {{')
        lines.append(f'    {struct_name} typed{{}};')
        fields = list(command.get("request_contract", {}).get("fields", []))
        required_fields = set(command.get("request_contract", {}).get("required_fields", []))
        for field in fields:
            field_name = str(field["name"])
            field_type = str(field.get("field_type", ""))
            has_expr, value_expr = _cpp_getter_has(field_type, field_name)
            if field_name in required_fields:
                lines.append(f'    typed.{field_name} = {value_expr};')
            else:
                lines.append(f'    if ({has_expr}) typed.{field_name} = {value_expr};')
        lines.append('    if (typed_request != nullptr) *typed_request = std::move(typed);')
        lines.append('    return true;')
        lines.append('  }')
        lines.append('')
    CPP_TYPED_REQUEST_PARSERS_INC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")




def _write_cpp_typed_handler_declarations(contract_document: dict) -> None:
    lines = [
        "// Generated from schemas/runtime_command_manifest.json via runtime_command_contracts.py. Do not edit manually.",
        "",
    ]
    for command in contract_document["commands"]:
        name = str(command["name"])
        struct_name = _cpp_struct_name(name)
        handler_group = str(command.get("dispatch_contract", {}).get("handler_group", ""))
        if not handler_group:
            continue
        method_name = _cpp_typed_handler_method_name(name)
        lines.append(f'  std::string {method_name}(const RuntimeCommandContext& context, const {struct_name}& request);')
    CPP_TYPED_HANDLER_DECLS_INC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_cpp_typed_handler_adapters(contract_document: dict) -> None:
    lines = [
        "// Generated from schemas/runtime_command_manifest.json via runtime_command_contracts.py. Do not edit manually.",
        "",
    ]
    for command in contract_document["commands"]:
        name = str(command["name"])
        struct_name = _cpp_struct_name(name)
        handler_group = str(command.get("dispatch_contract", {}).get("handler_group", ""))
        if not handler_group:
            continue
        method_name = _cpp_typed_handler_method_name(name)
        lines.append(f'inline std::string CoreRuntime::{method_name}(const RuntimeCommandContext& context, const {struct_name}& request) {{')
        lines.append('  RuntimeCommandInvocation invocation{};')
        lines.append('  invocation.request_id = context.request_id;')
        lines.append(f'  invocation.command = {struct_name}::kCommand;')
        lines.append('  invocation.envelope_json = context.envelope_json;')
        lines.append('  invocation.typed_request = request;')
        lines.append(f'  invocation.typed_contract = findRuntimeCommandTypedContract({struct_name}::kCommand);')
        lines.append(f'  return {handler_group}(invocation);')
        lines.append('}')
        lines.append('')
        lines.append(f'template <> inline std::string CoreRuntime::handleTypedCommand<{struct_name}>(const RuntimeCommandContext& context, const {struct_name}& request) {{')
        lines.append(f'  return {method_name}(context, request);')
        lines.append('}')
        lines.append('')
    CPP_TYPED_HANDLER_ADAPTERS_INC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    contract_document = export_contract_document()
    _write_cpp_manifest_include(manifest)
    _write_cpp_typed_contracts_include(contract_document)
    _write_cpp_typed_request_types(contract_document)
    _write_cpp_typed_request_parsers(contract_document)
    _write_cpp_typed_handler_declarations(contract_document)
    _write_cpp_typed_handler_adapters(contract_document)
    PY_TYPED_CONTRACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PY_TYPED_CONTRACTS_PATH.write_text(
        json.dumps(contract_document, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
