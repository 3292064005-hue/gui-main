#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.utils.runtime_config_contract import (
    cpp_apply_snapshot_output_path,
    cpp_field_decls_output_path,
    render_cpp_apply_snapshot_macro,
    render_cpp_field_decl_macros,
    runtime_config_contract_digest,
    runtime_config_contract_schema,
    schema_output_path,
)




def _syntax_only_compile_session_runtime(repo_root: Path) -> None:
    cpp_root = repo_root / "cpp_robot_core"
    with tempfile.TemporaryDirectory(prefix="runtime_config_contract_") as build_dir_str:
        build_dir = Path(build_dir_str)
        subprocess.run(
            [
                "cmake",
                "-S", str(cpp_root),
                "-B", str(build_dir),
                "-DROBOT_CORE_PROFILE=mock",
                "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
            ],
            check=True,
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        compile_db = build_dir / "compile_commands.json"
        commands = json.loads(compile_db.read_text(encoding="utf-8"))
        entry = next((item for item in commands if str(item.get("file", "")).endswith("src/session_runtime.cpp")), None)
        if entry is None:
            raise SystemExit("[FAIL] compile_commands.json missing session_runtime.cpp entry")
        if "arguments" in entry:
            args = list(entry["arguments"])
        else:
            args = shlex.split(entry["command"])
        filtered: list[str] = []
        skip_next = False
        for arg in args:
            if skip_next:
                skip_next = False
                continue
            if arg == "-o":
                skip_next = True
                continue
            filtered.append(arg)
        if "-fsyntax-only" not in filtered:
            insert_at = 1 if filtered else 0
            filtered.insert(insert_at, "-fsyntax-only")
        subprocess.run(
            filtered,
            check=True,
            cwd=entry.get("directory") or str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=dict(os.environ),
        )

def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    schema_target = schema_output_path(repo_root)
    field_target = cpp_field_decls_output_path(repo_root)
    apply_target = cpp_apply_snapshot_output_path(repo_root)
    runtime_types = repo_root / "cpp_robot_core/include/robot_core/runtime_types.h"
    session_runtime = repo_root / "cpp_robot_core/src/session_runtime.cpp"

    if not schema_target.exists():
        print(f"[FAIL] missing runtime config contract schema: {schema_target}")
        return 1
    if not field_target.exists() or not apply_target.exists():
        print("[FAIL] missing generated C++ runtime config includes")
        return 1

    expected = runtime_config_contract_schema()
    current = json.loads(schema_target.read_text(encoding="utf-8"))
    if current != expected:
        print(f"[FAIL] runtime config contract schema drift: {schema_target}")
        return 1
    if field_target.read_text(encoding="utf-8") != render_cpp_field_decl_macros():
        print(f"[FAIL] generated runtime config field declarations drift: {field_target}")
        return 1
    if apply_target.read_text(encoding="utf-8") != render_cpp_apply_snapshot_macro():
        print(f"[FAIL] generated runtime config apply snapshot drift: {apply_target}")
        return 1

    digest = runtime_config_contract_digest()
    if len(digest) != 64:
        print("[FAIL] runtime config contract digest malformed")
        return 1

    runtime_types_text = runtime_types.read_text(encoding="utf-8")
    session_runtime_text = session_runtime.read_text(encoding="utf-8")
    if '#include "robot_core/generated_runtime_config_field_decls.inc"' not in runtime_types_text:
        print("[FAIL] runtime_types.h does not consume generated runtime config field declarations")
        return 1
    if '#include "robot_core/generated_runtime_config_apply_snapshot.inc"' not in session_runtime_text:
        print("[FAIL] session_runtime.cpp does not consume generated runtime config apply snapshot include")
        return 1
    for needle in [
        'config_.robot_model = ROBOT_CORE_DEFAULT_ROBOT_MODEL;',
        'config_.axis_count = ROBOT_CORE_DEFAULT_AXIS_COUNT;',
        'config_.sdk_robot_class = ROBOT_CORE_DEFAULT_SDK_CLASS;',
        'config_.preferred_link = ROBOT_CORE_DEFAULT_PREFERRED_LINK;',
    ]:
        if needle in session_runtime_text:
            print(f"[FAIL] session_runtime.cpp still hard-resets mainline identity: {needle}")
            return 1

    _syntax_only_compile_session_runtime(repo_root)

    print(f"[PASS] runtime config contract schema/generation stable and compile-smoke clean: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
