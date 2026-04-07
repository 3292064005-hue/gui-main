from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class TlsMaterialPolicy:
    def __init__(self, env: dict[str, str] | None = None) -> None:
        self._env = env if env is not None else os.environ

    def runtime_tls_dir(self, *, repo_root: Path) -> Path:
        override = self._env.get("SPINE_TLS_DIR", "").strip()
        if override:
            return Path(override).expanduser().resolve()
        return (repo_root / "configs" / "tls" / "runtime").resolve()

    def describe(self, *, repo_root: Path) -> dict[str, Any]:
        root = self.runtime_tls_dir(repo_root=repo_root)
        return {"tls_dir": str(root), "exists": root.exists(), "material_present": any(root.glob("*.crt")) or any(root.glob("*.pem")) or any(root.glob("*.key"))}
