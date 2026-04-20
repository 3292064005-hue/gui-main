from __future__ import annotations

import hashlib
import json
from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

SCHEMA_VERSION = "runtime_config_contract.v1"
SCHEMA_RELATIVE_PATH = "schemas/runtime/runtime_config_v1.schema.json"
CPP_FIELD_DECLS_RELATIVE_PATH = "cpp_robot_core/include/robot_core/generated_runtime_config_field_decls.inc"
CPP_APPLY_SNAPSHOT_RELATIVE_PATH = "cpp_robot_core/include/robot_core/generated_runtime_config_apply_snapshot.inc"

_PRIMITIVE_TYPE_MAP = {
    int: "integer",
    float: "number",
    bool: "boolean",
    str: "string",
}

_CPP_TYPE_MAP = {
    int: "int",
    float: "double",
    bool: "bool",
    str: "std::string",
}

_CPP_STRUCT_NAME_MAP = {
    "ContactControlConfig": "ContactControlConfig",
    "ForceEstimatorConfig": "ForceEstimatorRuntimeConfig",
    "OrientationTrimConfig": "OrientationTrimRuntimeConfig",
}


def _config_model_module():
    from spine_ultrasound_ui.models import config_model

    return config_model


def _field_type_schema(annotation: Any) -> dict[str, Any]:
    origin = get_origin(annotation)
    if origin in {list, tuple}:
        args = get_args(annotation)
        item_schema = _field_type_schema(args[0]) if args else {"type": "object"}
        return {"type": "array", "items": item_schema}
    if origin is dict:
        return {"type": "object"}
    if origin is None and annotation in _PRIMITIVE_TYPE_MAP:
        return {"type": _PRIMITIVE_TYPE_MAP[annotation]}
    if is_dataclass(annotation):
        return _dataclass_contract(annotation)
    return {"type": "object"}


def _normalize_default(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: _normalize_default(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_normalize_default(item) for item in value]
    if isinstance(value, list):
        return [_normalize_default(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_default(item) for key, item in value.items()}
    return value


def _field_default(field_obj) -> Any:
    if field_obj.default is not MISSING:
        return field_obj.default
    if field_obj.default_factory is not MISSING:  # type: ignore[attr-defined]
        try:
            return field_obj.default_factory()  # type: ignore[misc]
        except Exception:
            return None
    return None


def _dataclass_contract(cls: type[Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    type_hints = get_type_hints(cls)
    for field_obj in fields(cls):
        annotation = type_hints.get(field_obj.name, field_obj.type)
        schema = _field_type_schema(annotation)
        default = _field_default(field_obj)
        if default is not None:
            schema["default"] = _normalize_default(default)
        properties[field_obj.name] = schema
        required.append(field_obj.name)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def build_runtime_config_contract() -> dict[str, Any]:
    config_model = _config_model_module()
    return {
        "schema_version": SCHEMA_VERSION,
        "schema_path": SCHEMA_RELATIVE_PATH,
        "nested_contracts": {
            "contact_control": _dataclass_contract(config_model.ContactControlConfig),
            "force_estimator": _dataclass_contract(config_model.ForceEstimatorConfig),
            "orientation_trim": _dataclass_contract(config_model.OrientationTrimConfig),
        },
        "runtime_config": _dataclass_contract(config_model.RuntimeConfig),
    }


def runtime_config_contract_schema() -> dict[str, Any]:
    contract = build_runtime_config_contract()
    nested = contract["nested_contracts"]
    root = dict(contract["runtime_config"])
    root.update(
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Runtime config v1",
            "description": "Canonical single-source runtime config contract shared by Python and C++ runtime boundaries.",
            "$defs": {
                "ContactControlConfig": nested["contact_control"],
                "ForceEstimatorConfig": nested["force_estimator"],
                "OrientationTrimConfig": nested["orientation_trim"],
            },
        }
    )
    for field_name, ref_name in {
        "contact_control": "ContactControlConfig",
        "force_estimator": "ForceEstimatorConfig",
        "orientation_trim": "OrientationTrimConfig",
    }.items():
        if field_name in root["properties"]:
            root["properties"][field_name] = {"$ref": f"#/$defs/{ref_name}"}
    return root


def runtime_config_contract_digest() -> str:
    schema = runtime_config_contract_schema()
    blob = json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def runtime_config_contract_metadata() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "schema_path": SCHEMA_RELATIVE_PATH,
        "digest": runtime_config_contract_digest(),
        "field_names": list(runtime_config_contract_schema().get("properties", {}).keys()),
    }


def schema_output_path(root: Path | None = None) -> Path:
    base = root if root is not None else Path(__file__).resolve().parents[2]
    return base / SCHEMA_RELATIVE_PATH


def cpp_field_decls_output_path(root: Path | None = None) -> Path:
    base = root if root is not None else Path(__file__).resolve().parents[2]
    return base / CPP_FIELD_DECLS_RELATIVE_PATH


def cpp_apply_snapshot_output_path(root: Path | None = None) -> Path:
    base = root if root is not None else Path(__file__).resolve().parents[2]
    return base / CPP_APPLY_SNAPSHOT_RELATIVE_PATH


def _cpp_string_literal(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _cpp_initializer(value: Any) -> str:
    if isinstance(value, str):
        return _cpp_string_literal(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "{" + ", ".join(_cpp_initializer(item) for item in value) + "}"
    if value is None:
        return "{}"
    return "{}"


def _cpp_decl_type(annotation: Any) -> str:
    origin = get_origin(annotation)
    if origin in {list, tuple}:
        args = get_args(annotation)
        inner = _cpp_decl_type(args[0] if args else float)
        return f"std::vector<{inner}>"
    if is_dataclass(annotation):
        return _CPP_STRUCT_NAME_MAP.get(annotation.__name__, annotation.__name__)
    return _CPP_TYPE_MAP.get(annotation, "std::string")


def _cpp_extract_lines(source_expr: str, annotation: Any, field_name: str, target_expr: str) -> list[str]:
    origin = get_origin(annotation)
    if origin in {list, tuple}:
        return [
            f"const auto {field_name}__arr = json::extractDoubleArray({source_expr}, \"{field_name}\", {target_expr});",
            f"if (!{field_name}__arr.empty()) {target_expr} = {field_name}__arr;",
        ]
    if annotation is bool:
        return [f"{target_expr} = json::extractBool({source_expr}, \"{field_name}\", {target_expr});"]
    if annotation is int:
        return [f"{target_expr} = json::extractInt({source_expr}, \"{field_name}\", {target_expr});"]
    if annotation is float:
        return [f"{target_expr} = json::extractDouble({source_expr}, \"{field_name}\", {target_expr});"]
    if annotation is str:
        return [f"{target_expr} = json::extractString({source_expr}, \"{field_name}\", {target_expr});"]
    if is_dataclass(annotation):
        nested_var = f"{field_name}__obj"
        lines = [f"const auto {nested_var} = json::extractObject({source_expr}, \"{field_name}\", \"{{}}\");"]
        nested_hints = get_type_hints(annotation)
        for sub_field in fields(annotation):
            sub_annotation = nested_hints.get(sub_field.name, sub_field.type)
            lines.extend(_cpp_extract_lines(nested_var, sub_annotation, sub_field.name, f"{target_expr}.{sub_field.name}"))
        return lines
    return [f"{target_expr} = json::extractString({source_expr}, \"{field_name}\", {target_expr});"]


def _render_struct_macro(cls: type[Any], macro_name: str) -> str:
    body: list[str] = []
    type_hints = get_type_hints(cls)
    for field_obj in fields(cls):
        default = _normalize_default(_field_default(field_obj))
        annotation = type_hints.get(field_obj.name, field_obj.type)
        body.append(f"  {_cpp_decl_type(annotation)} {field_obj.name}{{{_cpp_initializer(default)}}};")
    return f"#define {macro_name} \\\n" + " \\\n".join(body) + "\n"


def render_cpp_field_decl_macros() -> str:
    config_model = _config_model_module()
    return "\n".join(
        [
            "// Auto-generated by scripts/generate_runtime_config_contract.py. Do not edit manually.",
            "#pragma once",
            "",
            _render_struct_macro(config_model.ContactControlConfig, "ROBOT_CORE_CONTACT_CONTROL_CONFIG_FIELDS").rstrip(),
            "",
            _render_struct_macro(config_model.ForceEstimatorConfig, "ROBOT_CORE_FORCE_ESTIMATOR_CONFIG_FIELDS").rstrip(),
            "",
            _render_struct_macro(config_model.OrientationTrimConfig, "ROBOT_CORE_ORIENTATION_TRIM_CONFIG_FIELDS").rstrip(),
            "",
            _render_struct_macro(config_model.RuntimeConfig, "ROBOT_CORE_RUNTIME_CONFIG_FIELDS").rstrip(),
            "",
        ]
    )


def render_cpp_apply_snapshot_macro() -> str:
    config_model = _config_model_module()
    body: list[str] = []
    type_hints = get_type_hints(config_model.RuntimeConfig)
    for field_obj in fields(config_model.RuntimeConfig):
        annotation = type_hints.get(field_obj.name, field_obj.type)
        body.extend(_cpp_extract_lines("SOURCE_EXPR", annotation, field_obj.name, f"CONFIG_EXPR.{field_obj.name}"))
    rendered = " \\\n".join(f"  {line}" for line in body)
    return "\n".join(
        [
            "// Auto-generated by scripts/generate_runtime_config_contract.py. Do not edit manually.",
            "#pragma once",
            "",
            "#define ROBOT_CORE_APPLY_RUNTIME_CONFIG_SNAPSHOT(CONFIG_EXPR, SOURCE_EXPR) \\",
            rendered,
            "",
        ]
    )
