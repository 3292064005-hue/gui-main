from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.utils import now_text


class ReleaseGatePolicyEvaluator:
    """Evaluate release-gate policy from normalized inputs."""

    def __init__(self, gate_version: str) -> None:
        self.gate_version = gate_version

    def evaluate(self, session_dir, payloads: dict[str, Any]) -> dict[str, Any]:
        """Evaluate release eligibility.

        Args:
            session_dir: Session directory used only for fallback session id.
            payloads: Normalized gate inputs loaded by ``ReleaseGateInputLoader``.

        Returns:
            Stable release-gate decision payload.

        Raises:
            No exceptions are raised.
        """
        contract = dict(payloads.get("contract", {}))
        release_evidence = dict(payloads.get("release_evidence", {}))
        diagnostics = dict(payloads.get("diagnostics", {}))
        integrity = dict(payloads.get("integrity", {}))
        event_delivery = dict(payloads.get("event_delivery", {}))
        resume_outcomes = dict(payloads.get("resume_outcomes", {}))
        selected_execution = dict(payloads.get("selected_execution", {}))
        command_policy_snapshot = dict(payloads.get("command_policy_snapshot", {}))
        contract_kernel_diff = dict(payloads.get("contract_kernel_diff", {}))
        evidence_seal = dict(payloads.get("evidence_seal", {}))
        control_plane_snapshot = dict(payloads.get("control_plane_snapshot", {}))
        manifest = dict(payloads.get("manifest", {}))
        deployment_profile = dict(manifest.get("deployment_profile", {}))
        seal_required = bool(deployment_profile.get("requires_session_evidence_seal", False))
        evaluated_artifacts = [
            "meta/manifest.json",
            "derived/session/contract_consistency.json",
            "export/release_evidence_pack.json",
            "export/diagnostics_pack.json",
            "export/session_integrity.json",
            "derived/events/event_delivery_summary.json",
            "derived/session/resume_attempt_outcomes.json",
            "derived/planning/selected_execution_rationale.json",
            "derived/session/command_policy_snapshot.json",
            "derived/session/contract_kernel_diff.json",
            "meta/session_evidence_seal.json",
            "derived/session/control_plane_snapshot.json",
        ]
        runtime_doctor = dict(control_plane_snapshot.get("runtime_doctor", {}))
        check_results = [
            self._check("contract_alignment", bool(contract.get("summary", {}).get("consistent", False)), blocking_reason="contract_alignment_failed", remediation="repair_contract_consistency", evidence=["derived/session/contract_consistency.json"]),
            self._check("artifact_integrity", bool(integrity.get("summary", {}).get("integrity_ok", False)), blocking_reason="artifact_integrity_failed", remediation="repair_session_integrity", evidence=["export/session_integrity.json"]),
            self._check("release_candidate", bool(release_evidence.get("release_candidate", False)), warning_reason="release_evidence_not_candidate", evidence=["export/release_evidence_pack.json"]),
            self._check("event_continuity", int(event_delivery.get("summary", {}).get("continuity_gap_count", 0) or 0) == 0, blocking_reason="event_continuity_failed", remediation="rebuild_event_delivery_summary", evidence=["derived/events/event_delivery_summary.json"]),
            self._check("resume_viability", str(resume_outcomes.get("summary", {}).get("latest_outcome", "not_attempted")) not in {"failed", "blocked"}, warning_reason="resume_viability_failed", evidence=["derived/session/resume_attempt_outcomes.json"]),
            self._check("execution_rationale", bool(selected_execution.get("selected_candidate_id") or selected_execution.get("selected_plan_id")), blocking_reason="selected_execution_rationale_missing", remediation="materialize_selected_execution_rationale", evidence=["derived/planning/selected_execution_rationale.json"]),
            self._check("command_policy_snapshot", bool(command_policy_snapshot.get("decision_count", 0)) and bool(command_policy_snapshot.get("policy_version")), warning_reason="command_policy_snapshot_missing", remediation="materialize_command_policy_snapshot", evidence=["derived/session/command_policy_snapshot.json"]),
            self._check("contract_kernel_diff", bool(contract_kernel_diff.get("summary", {}).get("consistent", False)), blocking_reason="contract_kernel_diff_failed", remediation="repair_contract_kernel_alignment", evidence=["derived/session/contract_kernel_diff.json"]),
            self._check("session_evidence_seal", bool(evidence_seal.get("seal_digest", "")), blocking_reason="session_evidence_seal_missing" if seal_required else "", warning_reason="" if seal_required else "session_evidence_seal_missing", remediation="materialize_session_evidence_seal", evidence=["meta/session_evidence_seal.json"]),
            self._check("control_plane_snapshot", bool(control_plane_snapshot.get("summary_state")), warning_reason="control_plane_snapshot_missing", remediation="materialize_control_plane_snapshot", evidence=["derived/session/control_plane_snapshot.json"]),
            self._check("runtime_doctor", str(runtime_doctor.get("summary_state", "ready")) != "blocked", blocking_reason="runtime_doctor_blocked", remediation="repair_runtime_doctor_alignment", evidence=["derived/session/control_plane_snapshot.json"]),
            self._check("hard_freeze", int(dict(control_plane_snapshot.get("runtime_doctor", {})).get("session_freeze_drift_count", 0) or 0) == 0, blocking_reason="hard_freeze_drift_detected", remediation="relock_session_with_current_runtime_profile", evidence=["derived/session/control_plane_snapshot.json"]),
        ]
        blocking_reasons = [item["blocking_reason"] for item in check_results if item["status"] == "failed" and item.get("blocking_reason")]
        warning_reasons = [item["warning_reason"] for item in check_results if item["status"] == "failed" and item.get("warning_reason")]
        required_remediations = sorted({item["remediation"] for item in check_results if item["status"] == "failed" and item.get("remediation")})
        checks = {item["name"]: item["status"] == "passed" for item in check_results}
        release_allowed = not blocking_reasons and checks.get("release_candidate", False)
        return {
            "generated_at": now_text(),
            "evaluated_ts": now_text(),
            "session_id": str(manifest.get("session_id", session_dir.name)),
            "gate_version": self.gate_version,
            "release_allowed": release_allowed,
            "blocking_reasons": blocking_reasons,
            "warning_reasons": warning_reasons,
            "required_remediations": required_remediations,
            "checks": checks,
            "check_results": check_results,
            "evaluated_artifacts": evaluated_artifacts,
            "diagnostics_summary": dict(diagnostics.get("summary", {})),
            "release_candidate": checks.get("release_candidate", False),
            "schema": "runtime/release_gate_decision_v1.schema.json",
            "contract_kernel_diff": contract_kernel_diff,
            "control_plane_snapshot": {"summary_state": control_plane_snapshot.get("summary_state", ""), "release_mode": dict(control_plane_snapshot.get("release_mode", {}))},
            "evidence_seal": {"seal_digest": evidence_seal.get("seal_digest", ""), "artifact_count": int(evidence_seal.get("artifact_count", 0) or 0)},
        }

    @staticmethod
    def _check(name: str, passed: bool, *, blocking_reason: str = "", warning_reason: str = "", remediation: str = "", evidence: list[str] | None = None) -> dict[str, Any]:
        return {
            "name": name,
            "status": "passed" if passed else "failed",
            "blocking_reason": blocking_reason,
            "warning_reason": warning_reason,
            "remediation": remediation,
            "evidence": list(evidence or []),
        }
