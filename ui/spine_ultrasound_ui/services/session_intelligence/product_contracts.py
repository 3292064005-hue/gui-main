from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SessionIntelligenceProductSpec:
    """Declarative contract for a session-intelligence product.

    Attributes:
        product: Stable product identifier exposed to manifests and readers.
        output_artifact: Canonical session-relative artifact path.
        dependencies: Session-relative upstream inputs required to materialize
            the product.
        retryable: Whether the product may be regenerated after a transient
            failure without invalidating the surrounding session state.
        performance_budget_ms: Soft rendering budget used by diagnostics and
            stage manifests.
        owner_domain: Domain owning the product contract.
        materialization_phase: Lifecycle phase responsible for materializing the
            product. Read APIs must not generate artifacts outside this phase.
        read_policy: Contract governing read-side behavior for missing
            artifacts.
        stale_policy: Contract describing how callers recover from stale or
            missing materialized products.
    """

    product: str
    output_artifact: str
    dependencies: tuple[str, ...]
    retryable: bool
    performance_budget_ms: int
    owner_domain: str
    materialization_phase: str
    read_policy: str
    stale_policy: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['dependencies'] = list(self.dependencies)
        return payload
