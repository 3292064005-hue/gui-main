from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.live_evidence_bundle_service import LiveEvidenceBundleService


@dataclass(frozen=True)
class VerificationExecutionReportService:
    """Build a claim-safe verification execution report.

    The report records which repository/profile phases actually ran and keeps
    live-controller validation opt-in only when a real evidence bundle closes
    the controller-side proof chain. Supplying a path string alone is not
    sufficient to claim live validation.
    """

    root_dir: Path

    SCHEMA_VERSION = "verification.execution_report.v1"
    VERIFICATION_BOUNDARY_REF = "docs/05_verification/VERIFICATION_POLICY.md"

    def build(
        self,
        *,
        executed_phases: Iterable[str],
        sdk_binding_requested: bool,
        model_binding_requested: bool,
        readiness_manifest_path: str = "",
        readiness_manifest: Mapping[str, Any] | None = None,
        live_evidence_bundle: str = "",
    ) -> dict[str, Any]:
        phases = self._normalize_phases(executed_phases)
        binding_mode = "live_candidate" if sdk_binding_requested and model_binding_requested else "contract_shell"
        repository_proof = "python" in phases
        profile_phases = [phase for phase in phases if phase in {"dev", "research", "clinical"}]
        readiness_snapshot = dict(readiness_manifest or {})
        inspection = LiveEvidenceBundleService(self.root_dir).inspect(
            str(live_evidence_bundle or ""),
            sdk_binding_requested=bool(sdk_binding_requested),
            model_binding_requested=bool(model_binding_requested),
        )
        live_controller_validation = bool(inspection.valid)
        live_reason = inspection.reason
        runtime_readiness_payload = readiness_snapshot
        runtime_readiness_path = str(readiness_manifest_path or '')
        if live_evidence_bundle:
            runtime_readiness_payload = {
                'summary_state': inspection.readiness_summary_state,
                'verification': {
                    'verification_boundary': inspection.readiness_verification_boundary,
                    'evidence_tier': inspection.readiness_evidence_tier,
                    'sandbox_validation_possible': inspection.readiness_evidence_tier in {'static_and_sandbox', 'sandbox'},
                    'live_runtime_ready': inspection.readiness_live_runtime_ready,
                    'live_runtime_verified': inspection.readiness_live_runtime_verified,
                },
            } if inspection.readiness_summary_state or inspection.readiness_verification_boundary or inspection.readiness_evidence_tier or inspection.readiness_live_runtime_ready or inspection.readiness_live_runtime_verified else {}
            runtime_readiness_path = ''
        readiness_verification = dict((runtime_readiness_payload or {}).get('verification') or {})
        sandbox_validation_possible = bool(readiness_verification.get('sandbox_validation_possible', False)) or str(readiness_verification.get('evidence_tier', '')) in {'static_and_sandbox', 'sandbox'}
        profile_gate_proof = bool(profile_phases and sandbox_validation_possible)
        safe_summary = self._build_safe_summary(
            phases=phases,
            repository_proof=repository_proof,
            profile_gate_proof=profile_gate_proof,
            live_controller_validation=live_controller_validation,
            binding_mode=binding_mode,
            live_reason=live_reason,
        )
        return {
            "schema_version": self.SCHEMA_VERSION,
            "verification_boundary_ref": self.VERIFICATION_BOUNDARY_REF,
            "executed_phases": phases,
            "reported_tiers": {
                "已静态确认": bool(repository_proof),
                "已沙箱验证": bool(profile_gate_proof),
                "未真实环境验证": not live_controller_validation,
            },
            "proof_scope": {
                "repository_proof": repository_proof,
                "profile_gate_proof": profile_gate_proof,
                "profile_phases": profile_phases,
                "live_controller_validation": live_controller_validation,
                "sandbox_validation_possible": sandbox_validation_possible,
            },
            "bindings": {
                "sdk_binding_requested": bool(sdk_binding_requested),
                "model_binding_requested": bool(model_binding_requested),
                "binding_mode": binding_mode,
            },
            "runtime_readiness": {
                "manifest_path": runtime_readiness_path,
                "source": "embedded_live_bundle" if live_evidence_bundle else "linked_manifest",
                "summary_state": str((runtime_readiness_payload or {}).get("summary_state", "")),
                "verification_boundary": str(((runtime_readiness_payload or {}).get("verification") or {}).get("verification_boundary", "")),
                "evidence_tier": str(((runtime_readiness_payload or {}).get("verification") or {}).get("evidence_tier", "")),
                "sandbox_validation_possible": bool(((runtime_readiness_payload or {}).get("verification") or {}).get("sandbox_validation_possible", False)),
                "live_runtime_ready": bool(((runtime_readiness_payload or {}).get("verification") or {}).get("live_runtime_ready", False)),
                "live_runtime_verified": bool(((runtime_readiness_payload or {}).get("verification") or {}).get("live_runtime_verified", False)),
            },
            "real_environment": {
                "validated": live_controller_validation,
                "evidence_bundle": inspection.bundle_path,
                "reason": live_reason,
                "bundle_validation": inspection.to_dict(),
            },
            "claim_guardrails": {
                "forbidden_claims": [
                    "fully deliverable",
                    "production-ready based only on repository/profile gates",
                    "HIL validated without the controller evidence bundle",
                    "live SDK verified when SDK/model bindings were disabled",
                    "real-time validated without measured controller-side RT evidence",
                ],
                "safe_summary": safe_summary,
            },
        }

    def _normalize_phases(self, executed_phases: Iterable[str]) -> list[str]:
        """Normalize verification phases to canonical deployment-profile tokens.

        Accepted external phase tokens are:
        - python
        - dev / mock
        - research / hil
        - clinical / prod

        Legacy aliases remain accepted so old scripts and archived reports do not
        break, but emitted reports always use canonical deployment profile names.
        """
        normalized: list[str] = []
        phase_aliases = {
            'python': 'python',
            'mock': 'dev',
            'dev': 'dev',
            'hil': 'research',
            'research': 'research',
            'prod': 'clinical',
            'clinical': 'clinical',
        }
        for raw in executed_phases:
            token = str(raw).strip().lower()
            if not token:
                continue
            canonical = phase_aliases.get(token)
            if canonical is None:
                canonical = DeploymentProfileService.normalize_profile_name(token)
            if not canonical:
                continue
            if canonical not in normalized:
                normalized.append(canonical)
        return normalized

    def _build_safe_summary(
        self,
        *,
        phases: list[str],
        repository_proof: bool,
        profile_gate_proof: bool,
        live_controller_validation: bool,
        binding_mode: str,
        live_reason: str,
    ) -> str:
        phase_text = ", ".join(phases) if phases else "none"
        parts = [f"executed phases: {phase_text}"]
        if repository_proof:
            parts.append("repository proof closed")
        if profile_gate_proof:
            parts.append("artifact-backed sandbox proof closed")
        parts.append(f"binding mode: {binding_mode}")
        if live_controller_validation:
            parts.append("live-controller validation closed by archived controller evidence bundle")
        else:
            parts.append(f"treat result as artifact-backed 已静态确认/已沙箱验证 only when readiness evidence exists; 未真实环境验证 remains true ({live_reason})")
        return "; ".join(parts)
