#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.utils.runtime_config_contract import (
    cpp_apply_snapshot_output_path,
    cpp_field_decls_output_path,
    render_cpp_apply_snapshot_macro,
    render_cpp_field_decl_macros,
    runtime_config_contract_schema,
    schema_output_path,
)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    schema_target = schema_output_path(repo_root)
    schema_target.parent.mkdir(parents=True, exist_ok=True)
    schema_target.write_text(json.dumps(runtime_config_contract_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    field_target = cpp_field_decls_output_path(repo_root)
    field_target.parent.mkdir(parents=True, exist_ok=True)
    field_target.write_text(render_cpp_field_decl_macros(), encoding="utf-8")

    apply_target = cpp_apply_snapshot_output_path(repo_root)
    apply_target.parent.mkdir(parents=True, exist_ok=True)
    apply_target.write_text(render_cpp_apply_snapshot_macro(), encoding="utf-8")

    print(f"[PASS] wrote runtime config contract artifacts: {schema_target}, {field_target}, {apply_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
