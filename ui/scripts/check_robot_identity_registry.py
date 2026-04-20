#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REGISTRY_PATH = ROOT / "configs" / "robot_identity_mainline.json"
TEXT_TARGETS = {
    "README.md": ("robot_model", "sdk_robot_class", "axis_count", "preferred_link", "clinical_mainline_mode"),
    "docs/04_profiles_and_release/PROFILE_MATRIX.md": ("robot_model", "sdk_robot_class", "axis_count", "preferred_link", "clinical_mainline_mode"),
}


def _load_registry() -> dict[str, Any]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("robot identity registry must be a JSON object")
    return data


def _expect_text_literals(registry: dict[str, Any], failures: list[str]) -> None:
    for relative_path, keys in TEXT_TARGETS.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for key in keys:
            expected = str(registry[key])
            if expected not in text:
                failures.append(f"{relative_path} missing {key}={expected}")


def _parse_markdown_family_section(text: str, family_key: str) -> dict[str, str]:
    pattern = rf'^## {re.escape(family_key)}$'
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return {}
    tail = text[match.end():]
    next_header = re.search(r'^##\s+', tail, flags=re.MULTILINE)
    section = tail[: next_header.start()] if next_header else tail
    parsed: dict[str, str] = {}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith('- ') or ': ' not in line:
            continue
        key, value = line[2:].split(': ', 1)
        parsed[key.strip()] = value.strip().strip('`')
    return parsed


def _expect_doc_matrix(registry: dict[str, Any], failures: list[str]) -> None:
    matrix = (ROOT / 'docs' / '04_profiles_and_release' / 'PROFILE_MATRIX.md').read_text(encoding='utf-8')
    parsed = _parse_markdown_family_section(matrix, str(registry['family_key']))
    expected = {
        'sdk class': str(registry['sdk_robot_class']),
        'robot model': str(registry['robot_model']),
        'axis count': str(registry['axis_count']),
        'preferred link': str(registry['preferred_link']),
        'realtime mainline': str(registry['clinical_mainline_mode']),
    }
    if not parsed:
        failures.append(f"docs/04_profiles_and_release/PROFILE_MATRIX.md missing section for {registry['family_key']}")
        return
    for key, value in expected.items():
        actual = parsed.get(key)
        if actual != value:
            failures.append(f"docs/04_profiles_and_release/PROFILE_MATRIX.md expected {key}={value!r} but found {actual!r}")


def _import_robot_identity_module():
    path = ROOT / 'spine_ultrasound_ui' / 'services' / 'robot_identity_service.py'
    spec = importlib.util.spec_from_file_location('robot_identity_service_registry_audit', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'failed to import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _expect_python_identity_contract(registry: dict[str, Any], failures: list[str]) -> None:
    module = _import_robot_identity_module()
    identity = module.XMATE3_IDENTITY.to_dict()
    service = module.RobotIdentityService(default_model=str(registry['robot_model']))
    resolved = service.resolve().to_dict()
    family = service.build_family_contract()
    expected_identity = {
        'robot_model': str(registry['robot_model']),
        'sdk_robot_class': str(registry['sdk_robot_class']),
        'axis_count': int(registry['axis_count']),
        'preferred_link': str(registry['preferred_link']),
        'rt_mode': str(registry['clinical_mainline_mode']),
        'family_key': str(registry['family_key']),
    }
    for key, value in expected_identity.items():
        actual = identity.get(key)
        if actual != value:
            failures.append(f'spine_ultrasound_ui/services/robot_identity_service.py XMATE3_IDENTITY expected {key}={value!r} but found {actual!r}')
        resolved_actual = resolved.get(key)
        if resolved_actual != value:
            failures.append(f'RobotIdentityService.resolve() expected {key}={value!r} but found {resolved_actual!r}')
    if service.default_model != str(registry['robot_model']):
        failures.append(f'RobotIdentityService.default_model expected {registry["robot_model"]!r} but found {service.default_model!r}')
    family_expectations = {
        'family_key': str(registry['family_key']),
        'robot_model': str(registry['robot_model']),
        'sdk_robot_class': str(registry['sdk_robot_class']),
        'axis_count': int(registry['axis_count']),
        'preferred_link': str(registry['preferred_link']),
        'clinical_rt_mode': str(registry['clinical_mainline_mode']),
    }
    for key, value in family_expectations.items():
        actual = family.get(key)
        if actual != value:
            failures.append(f'RobotIdentityService.build_family_contract() expected {key}={value!r} but found {actual!r}')


def main() -> int:
    registry = _load_registry()
    failures: list[str] = []
    _expect_text_literals(registry, failures)
    _expect_doc_matrix(registry, failures)
    _expect_python_identity_contract(registry, failures)
    if failures:
        for item in failures:
            print(f'[FAIL] {item}')
        return 1
    print('[PASS] robot identity registry is synchronized with canonical code and docs')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
