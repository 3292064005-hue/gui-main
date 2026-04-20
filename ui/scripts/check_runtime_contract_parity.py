#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST_PATH = ROOT / "schemas" / "runtime_command_manifest.json"
PY_CONTRACTS_PATH = ROOT / "spine_ultrasound_ui" / "contracts" / "generated" / "runtime_command_contracts.json"
CPP_CONTRACTS_PATH = ROOT / "cpp_robot_core" / "include" / "robot_core" / "generated_runtime_command_contracts.inc"

VALID_HANDLER_GROUPS = {
    "handleConnectionCommand",
    "handlePowerModeCommand",
    "handleValidationCommand",
    "handleQueryCommand",
    "handleFaultInjectionCommand",
    "handleSessionCommand",
    "handleExecutionCommand",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise SystemExit(f"[runtime-contract-parity] {message}")


def main() -> int:
    manifest = load_json(MANIFEST_PATH)
    py_contracts = load_json(PY_CONTRACTS_PATH)
    manifest_commands = {str(item["name"]): item for item in manifest.get("commands", [])}
    python_commands = {str(item["name"]): item for item in py_contracts.get("commands", [])}

    if set(manifest_commands) != set(python_commands):
        missing_py = sorted(set(manifest_commands) - set(python_commands))
        extra_py = sorted(set(python_commands) - set(manifest_commands))
        fail(f"manifest/python command sets diverged missing_py={missing_py} extra_py={extra_py}")

    cpp_contracts_text = CPP_CONTRACTS_PATH.read_text(encoding="utf-8")
    for name, spec in manifest_commands.items():
        if f'{{"{name}",' not in cpp_contracts_text:
            fail(f"C++ generated contracts missing command {name}")
        handler_group = str(spec.get("handler_group", "")).strip()
        if handler_group not in VALID_HANDLER_GROUPS:
            fail(f"command {name} uses unsupported handler_group={handler_group!r}")
        py_contract = python_commands[name]
        if str(py_contract.get("canonical_command", name)).strip() != str(spec.get("canonical_command", name)).strip():
            fail(f"canonical mismatch for {name}")
        if str(py_contract.get("alias_kind", "")).strip() != str(spec.get("alias_kind", "")).strip():
            fail(f"alias_kind mismatch for {name}")
        if str(py_contract.get("handler_group", "")).strip() != handler_group:
            fail(f"handler_group mismatch for {name}")

    print("[runtime-contract-parity] manifest, Python contracts, and C++ generated contracts are aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
