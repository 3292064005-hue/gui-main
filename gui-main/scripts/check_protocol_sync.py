#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

PROTO_PATH = ROOT / 'cpp_robot_core' / 'proto' / 'ipc_messages.proto'
CPP_HEADER_PATH = ROOT / 'cpp_robot_core' / 'include' / 'ipc_messages.pb.h'
CPP_SOURCE_PATH = ROOT / 'cpp_robot_core' / 'src' / 'ipc_messages.pb.cpp'
PY_PB2_PATH = ROOT / 'spine_ultrasound_ui' / 'services' / 'ipc_messages_pb2.py'
PY_COMMAND_CATALOG_PATH = ROOT / 'spine_ultrasound_ui' / 'services' / 'runtime_command_catalog.py'
CPP_COMMAND_REGISTRY_PATH = ROOT / 'cpp_robot_core' / 'src' / 'command_registry.cpp'


@dataclass(frozen=True)
class FieldSpec:
    label: str
    type_name: str
    name: str
    number: int


@dataclass(frozen=True)
class MessageSpec:
    name: str
    fields: tuple[FieldSpec, ...]


def parse_proto_specs(source: str) -> dict[str, MessageSpec]:
    message_pattern = re.compile(r'message\s+(\w+)\s*\{(.*?)\}', re.DOTALL)
    field_pattern = re.compile(r'\s*(repeated\s+)?([A-Za-z0-9_]+)\s+(\w+)\s*=\s*(\d+)\s*;')
    specs: dict[str, MessageSpec] = {}
    for match in message_pattern.finditer(source):
        name = match.group(1)
        body = match.group(2)
        fields: list[FieldSpec] = []
        for field_match in field_pattern.finditer(body):
            label = 'repeated' if field_match.group(1) else 'optional'
            fields.append(FieldSpec(label=label, type_name=field_match.group(2), name=field_match.group(3), number=int(field_match.group(4))))
        specs[name] = MessageSpec(name=name, fields=tuple(fields))
    return specs


def descriptor_specs(ipc_messages_pb2) -> dict[str, MessageSpec]:
    file_desc = ipc_messages_pb2.DESCRIPTOR
    specs: dict[str, MessageSpec] = {}
    label_map = {
        1: 'optional',
        3: 'repeated',
    }
    type_map = {
        1: 'double',
        3: 'int64',
        5: 'int32',
        8: 'bool',
        9: 'string',
    }
    for msg_desc in file_desc.message_types_by_name.values():
        fields = []
        for field in msg_desc.fields:
            fields.append(
                FieldSpec(
                    label=label_map.get(getattr(field, 'label', getattr(field, '_label', None)), 'optional'),
                    type_name=type_map.get(getattr(field, 'type', getattr(field, '_type', None)), getattr(field, 'type_name', '')),
                    name=field.name,
                    number=field.number,
                )
            )
        specs[msg_desc.name] = MessageSpec(name=msg_desc.name, fields=tuple(fields))
    return specs


def check_cpp_header(header: str, spec: MessageSpec) -> list[str]:
    issues: list[str] = []
    class_body_match = re.search(rf'class\s+{re.escape(spec.name)}\s+final\s*:\s*public\s+google::protobuf::Message\s*\{{(.*?)\n\}};', header, re.DOTALL)
    if not class_body_match:
        return [f'C++ header missing class {spec.name}']
    body = class_body_match.group(1)
    for field in spec.fields:
        if field.label == 'repeated':
            if not re.search(rf'\b{re.escape(field.name)}\(\)\s+const\b', body):
                issues.append(f'C++ header missing repeated getter for {spec.name}.{field.name}')
            if not re.search(rf'\bmutable_{re.escape(field.name)}\(\)', body):
                issues.append(f'C++ header missing repeated mutable accessor for {spec.name}.{field.name}')
            if not re.search(rf'\badd_{re.escape(field.name)}\(', body):
                issues.append(f'C++ header missing repeated add accessor for {spec.name}.{field.name}')
        else:
            if not re.search(rf'\b{re.escape(field.name)}\(\)\s+const\b', body):
                issues.append(f'C++ header missing getter for {spec.name}.{field.name}')
            if not re.search(rf'\bset_{re.escape(field.name)}\(', body):
                issues.append(f'C++ header missing setter for {spec.name}.{field.name}')
    if 'SerializeToString' not in body or 'ParseFromString' not in body:
        issues.append(f'C++ header missing serialize/parse contract for {spec.name}')
    return issues


def _cleanup_generated_python_artifacts() -> None:
    for root, dirs, files in os.walk(ROOT, topdown=False):
        root_path = Path(root)
        if '.git' in root_path.parts:
            continue
        for filename in files:
            if filename.endswith(('.pyc', '.pyo')):
                (root_path / filename).unlink(missing_ok=True)
        for dirname in dirs:
            if dirname in {'.pytest_cache', '__pycache__'}:
                shutil.rmtree(root_path / dirname, ignore_errors=True)


def _load_pb2():
    try:
        from spine_ultrasound_ui.services import ipc_messages_pb2
    except Exception as exc:
        return None, f'failed to import Python pb2 runtime: {exc}'
    return ipc_messages_pb2, ''



def parse_python_command_catalog(source: str) -> dict[str, dict[str, object]]:
    import ast

    def literal(node: ast.AST):
        return ast.literal_eval(node)

    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "COMMAND_SPECS" and isinstance(node.value, ast.Dict):
                    return literal(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "COMMAND_SPECS" and isinstance(node.value, ast.Dict):
            return literal(node.value)
    return {}


def parse_cpp_command_registry(source: str) -> dict[str, dict[str, object]]:
    pattern = re.compile(r'\{"([a-z_]+)",\s*(true|false),\s*"([^"]*)"\}')
    registry: dict[str, dict[str, object]] = {}
    for command, write_flag, state_signature in pattern.findall(source):
        registry[command] = {
            "write_command": write_flag == "true",
            "state_preconditions": [item for item in state_signature.split('|') if item],
        }
    return registry

def main() -> int:
    issues: list[str] = []
    try:
        for path in (PROTO_PATH, CPP_HEADER_PATH, CPP_SOURCE_PATH, PY_PB2_PATH, PY_COMMAND_CATALOG_PATH, CPP_COMMAND_REGISTRY_PATH):
            if not path.exists():
                issues.append(f'missing required protocol asset: {path}')
        if issues:
            for issue in issues:
                print(f'[FAIL] {issue}')
            return 1

        proto_text = PROTO_PATH.read_text(encoding='utf-8')
        header_text = CPP_HEADER_PATH.read_text(encoding='utf-8')
        source_text = CPP_SOURCE_PATH.read_text(encoding='utf-8')
        py_pb2_text = PY_PB2_PATH.read_text(encoding='utf-8')
        py_command_catalog_text = PY_COMMAND_CATALOG_PATH.read_text(encoding='utf-8')
        cpp_command_registry_text = CPP_COMMAND_REGISTRY_PATH.read_text(encoding='utf-8')

        proto_specs = parse_proto_specs(proto_text)
        ipc_messages_pb2, pb2_error = _load_pb2()
        if ipc_messages_pb2 is None:
            print(f'[FAIL] {pb2_error}')
            return 1
        python_specs = descriptor_specs(ipc_messages_pb2)

        if set(proto_specs) != set(python_specs):
            issues.append(f'Python protobuf messages do not match proto source: proto={sorted(proto_specs)}, python={sorted(python_specs)}')

        for name, proto_spec in proto_specs.items():
            py_spec = python_specs.get(name)
            if py_spec is None:
                continue
            if proto_spec.fields != py_spec.fields:
                issues.append(f'Python protobuf field contract mismatch for {name}: proto={proto_spec.fields}, python={py_spec.fields}')
            issues.extend(check_cpp_header(header_text, proto_spec))
            if f'bool {name}::SerializeToString' not in source_text or f'bool {name}::ParseFromString' not in source_text:
                issues.append(f'C++ wire codec missing serialize/parse implementation for {name}')

        if 'Generated by the protocol buffer compiler' not in py_pb2_text:
            issues.append('Python pb2 file no longer advertises generated contract header')

        python_catalog = parse_python_command_catalog(py_command_catalog_text)
        cpp_catalog = parse_cpp_command_registry(cpp_command_registry_text)
        python_commands = set(python_catalog)
        cpp_commands = set(cpp_catalog)
        if python_commands != cpp_commands:
            issues.append(f'command catalog mismatch: python={sorted(python_commands)} cpp={sorted(cpp_commands)}')
        for command in sorted(python_commands & cpp_commands):
            py_spec = dict(python_catalog.get(command, {}))
            cpp_spec = dict(cpp_catalog.get(command, {}))
            py_write = bool(py_spec.get("write_command", True))
            cpp_write = bool(cpp_spec.get("write_command", True))
            if py_write != cpp_write:
                issues.append(f'command write flag mismatch for {command}: python={py_write} cpp={cpp_write}')
            py_states = list(py_spec.get("state_preconditions", []))
            cpp_states = list(cpp_spec.get("state_preconditions", []))
            if py_states != cpp_states:
                issues.append(f'command state preconditions mismatch for {command}: python={py_states} cpp={cpp_states}')

        if issues:
            for issue in issues:
                print(f'[FAIL] {issue}')
            return 1

        print('[PASS] protocol source, Python pb2, and C++ wire codec remain aligned')
        return 0
    finally:
        _cleanup_generated_python_artifacts()


if __name__ == '__main__':
    raise SystemExit(main())
