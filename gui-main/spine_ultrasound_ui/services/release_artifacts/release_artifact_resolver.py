from __future__ import annotations

from pathlib import Path
from typing import Any


class ReleaseArtifactResolver:
    """Resolve canonical release artifacts against a session directory."""

    def resolve(self, session_dir: Path, required_artifacts: dict[str, str], artifact_registry: dict[str, Any]) -> list[dict[str, Any]]:
        """Resolve release artifacts into stable descriptors.

        Args:
            session_dir: Session directory containing artifacts.
            required_artifacts: Canonical artifact-name to relative-path map.
            artifact_registry: Manifest artifact-registry payload.

        Returns:
            Ordered artifact descriptors with existence/registration metadata.

        Raises:
            No exceptions are raised.
        """
        items: list[dict[str, Any]] = []
        for name, relative in sorted(required_artifacts.items()):
            descriptor = dict(artifact_registry.get(name, {}))
            items.append({
                "artifact": name,
                "path": relative,
                "exists": (session_dir / relative).exists(),
                "registered": bool(descriptor),
                "checksum": str(descriptor.get("checksum", "")),
                "schema": str(descriptor.get("schema", "")),
            })
        return items
