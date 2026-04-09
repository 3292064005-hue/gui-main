from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

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
    VERIFICATION_BOUNDARY_REF = "docs/VERIFICATION_BOUNDARY.md"

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
        profile_phases = [phase for phase in phases if phase in {"mock", "hil", "prod"}]
        profile_gate_proof = bool(profile_phases)
        readiness_snapshot = dict(readiness_manifest or {})
        inspection = LiveEvidenceBundleService(self.root_dir).inspect(
            str(live_evidence_bundle or ""),
            sdk_binding_requested=bool(sdk_binding_requested),
            model_binding_requested=bool(model_binding_requested),
        )
        live_controller_validation = bool(inspection.valid)
        live_reason = inspection.reason
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
                "已静态确认": bool(repository_proof or profile_gate_proof),
                "已沙箱验证": bool(repository_proof or profile_gate_proof),
                "未真实环境验证": not live_controller_validation,
            },
            "proof_scope": {
                "repository_proof": repository_proof,
                "profile_gate_proof": profile_gate_proof,
                "profile_phases": profile_phases,
                "live_controller_validation": live_controller_validation,
            },
            "bindings": {
                "sdk_binding_requested": bool(sdk_binding_requested),
                "model_binding_requested": bool(model_binding_requested),
                "binding_mode": binding_mode,
            },
            "runtime_readiness": {
                "manifest_path": str(readiness_manifest_path or ""),
                "summary_state": str((readiness_snapshot or {}).get("summary_state", "")),
                "verification_boundary": str(((readiness_snapshot or {}).get("verification") or {}).get("verification_boundary", "")),
                "live_runtime_ready": bool(((readiness_snapshot or {}).get("verification") or {}).get("live_runtime_ready", False)),
                "live_runtime_verified": bool(((readiness_snapshot or {}).get("verification") or {}).get("live_runtime_verified", False)),
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
        normalized: list[str] = []
        for raw in executed_phases:
            phase = str(raw).strip()
            if not phase:
                continue
            if phase not in normalized:
                normalized.append(phase)
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
            parts.append("profile gate proof closed")
        parts.append(f"binding mode: {binding_mode}")
        if live_controller_validation:
            parts.append("live-controller validation closed by archived controller evidence bundle")
        else:
            parts.append(f"treat result as 已静态确认 + 已沙箱验证 only; 未真实环境验证 remains true ({live_reason})")
        return "; ".join(parts)
