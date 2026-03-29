from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    target = SCHEMA_ROOT / name
    return json.loads(target.read_text(encoding="utf-8"))


def schema_catalog() -> dict[str, dict[str, Any]]:
    return {
        str(path.relative_to(SCHEMA_ROOT)).replace('\\', '/'): json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(SCHEMA_ROOT.rglob("*.schema.json"))
    }
