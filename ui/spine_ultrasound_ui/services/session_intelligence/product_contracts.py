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


@dataclass(frozen=True)
class SessionIntelligenceInputBundle:
    manifest: dict[str, Any]
    scan_plan: dict[str, Any]
    command_journal: list[dict[str, Any]]
    annotations: list[dict[str, Any]]
    alarms: dict[str, Any]
    quality: dict[str, Any]
    report: dict[str, Any]
    summary: dict[str, Any]
    evidence_seal: dict[str, Any]
    integrity: dict[str, Any]
    session_id: str


@dataclass(frozen=True)
class SessionIntelligenceProductBundle:
    lineage: dict[str, Any]
    resume_state: dict[str, Any]
    resume_decision: dict[str, Any]
    recovery_report: dict[str, Any]
    recovery_decision_timeline: dict[str, Any]
    operator_incident_report: dict[str, Any]
    session_incidents: dict[str, Any]
    event_log_index: dict[str, Any]
    event_delivery_summary: dict[str, Any]
    selected_execution_rationale: dict[str, Any]
    release_gate_decision: dict[str, Any]
    control_plane_snapshot: dict[str, Any]
    control_authority_snapshot: dict[str, Any]
    bridge_observability_report: dict[str, Any]
    artifact_registry_snapshot: dict[str, Any]
    session_evidence_seal: dict[str, Any]
    resume_attempts: dict[str, Any]
    resume_attempt_outcomes: dict[str, Any]
    command_state_policy: dict[str, Any]
    command_policy_snapshot: dict[str, Any]
    contract_kernel_diff: dict[str, Any]
    contract_consistency: dict[str, Any]
    release_evidence_pack: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
