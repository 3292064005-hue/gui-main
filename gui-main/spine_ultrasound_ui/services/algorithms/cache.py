from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class PluginCache:
    def cache_path(self, session_dir: Path, stage: str, cache_key: str) -> Path:
        digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
        return session_dir / "derived" / ".plugin_cache" / stage / f"{digest}.json"

    def load(self, session_dir: Path, stage: str, cache_key: str) -> dict[str, Any] | None:
        target = self.cache_path(session_dir, stage, cache_key)
        if not target.exists():
            return None
        return json.loads(target.read_text(encoding="utf-8"))

    def save(self, session_dir: Path, stage: str, cache_key: str, payload: dict[str, Any]) -> None:
        target = self.cache_path(session_dir, stage, cache_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
