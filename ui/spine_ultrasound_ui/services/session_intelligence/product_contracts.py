from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SessionIntelligenceProductSpec:
    """Declarative contract for a session-intelligence product."""

    product: str
    output_artifact: str
    dependencies: tuple[str, ...]
    retryable: bool
    performance_budget_ms: int
    owner_domain: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation.

        Returns:
            Dictionary for manifests and diagnostics.

        Raises:
            No exceptions are raised.
        """
        payload = asdict(self)
        payload['dependencies'] = list(self.dependencies)
        return payload
