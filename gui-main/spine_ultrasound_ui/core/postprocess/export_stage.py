from __future__ import annotations

from pathlib import Path
from typing import Any


class ExportStage:
    """Refresh all postprocess stages in deterministic order."""

    def run(self, service, session_dir: Path | None) -> dict[str, Any]:
        """Execute all postprocess stages.

        Args:
            service: ``PostprocessService`` façade instance.
            session_dir: Session directory or ``None`` when unavailable.

        Returns:
            Stage-name to ``CapabilityStatus`` mapping.

        Raises:
            RuntimeError: Propagated from the façade when any stage fails.
        """
        return {
            "preprocess": service.preprocess(session_dir),
            "reconstruction": service.reconstruct(session_dir),
            "assessment": service.assess(session_dir),
        }
