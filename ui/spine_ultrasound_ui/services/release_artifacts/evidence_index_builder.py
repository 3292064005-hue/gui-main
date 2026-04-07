from __future__ import annotations

from typing import Any


class EvidenceIndexBuilder:
    """Build an evidence index and its missing-artifact gap list."""

    def build(self, resolved_artifacts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        """Build evidence-index rows and hard gaps.

        Args:
            resolved_artifacts: Resolved artifact descriptors.

        Returns:
            Tuple of evidence-index rows and missing-artifact gap labels.

        Raises:
            No exceptions are raised.
        """
        gaps = [f"missing:{row['artifact']}" for row in resolved_artifacts if not bool(row.get("exists", False))]
        return list(resolved_artifacts), gaps
