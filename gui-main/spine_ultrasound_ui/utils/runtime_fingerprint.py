from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def payload_hash(payload: Any) -> str:
    blob = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(blob).hexdigest() if blob else ""


def short_hash(payload: Any, *, length: int = 16) -> str:
    return payload_hash(payload)[:length]
