from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PostprocessStageSpec:
    """Declarative contract for a postprocess stage.

    Attributes:
        stage: Stable stage identifier used in manifests and logs.
        label: Operator-facing stage label.
        input_artifacts: Canonical relative artifact paths consumed by the stage.
        output_artifacts: Canonical relative artifact paths produced by the stage.
        retryable: Whether the stage may be retried without relocking the session.
        performance_budget_ms: Target upper bound for a typical run on the mainline
            workstation profile.
        owner_domain: Repository/domain gate owning this stage.
    """

    stage: str
    label: str
    input_artifacts: tuple[str, ...]
    output_artifacts: tuple[str, ...]
    retryable: bool
    performance_budget_ms: int
    owner_domain: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation.

        Returns:
            Dictionary suitable for manifests and diagnostics.

        Raises:
            No exceptions are raised.
        """
        payload = asdict(self)
        payload['input_artifacts'] = list(self.input_artifacts)
        payload['output_artifacts'] = list(self.output_artifacts)
        return payload


@dataclass(frozen=True)
class PostprocessStageStatusBundle:
    preprocess: Any
    reconstruction: Any
    assessment: Any

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "PostprocessStageStatusBundle":
        return cls(
            preprocess=payload.get("preprocess"),
            reconstruction=payload.get("reconstruction"),
            assessment=payload.get("assessment"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "preprocess": self.preprocess,
            "reconstruction": self.reconstruction,
            "assessment": self.assessment,
        }

    def ordered_items(self) -> tuple[tuple[str, Any], ...]:
        return (("preprocess", self.preprocess), ("reconstruction", self.reconstruction), ("assessment", self.assessment))
