from __future__ import annotations

"""Dedicated surface for authoritative session-product reads."""

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.authoritative_artifact_reader import AuthoritativeArtifactReader


class SessionProductsAuthoritySurface:
    """Read authoritative session products without exposing raw artifact-selection rules."""

    def __init__(self, artifact_reader: AuthoritativeArtifactReader | None = None) -> None:
        self._artifact_reader = artifact_reader or AuthoritativeArtifactReader()

    def read_spine_curve(self, session_dir: Path) -> dict[str, Any]:
        return self._artifact_reader.read_spine_curve(session_dir)

    def read_cobb_measurement(self, session_dir: Path) -> dict[str, Any]:
        return self._artifact_reader.read_cobb_measurement(session_dir)
