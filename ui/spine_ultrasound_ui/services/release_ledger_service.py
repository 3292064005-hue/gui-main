from __future__ import annotations

"""Aggregate release/readiness evidence into one machine-readable ledger.

The repository already emits multiple claim-safe reports (verification report,
runtime readiness manifest, build evidence report, acceptance summary). This
service collects those artifacts into a single ledger without overstating the
claim boundary, and it fails closed when required upstream reports are missing
or malformed.
"""

import json
import os
from pathlib import Path
from typing import Any


class ReleaseLedgerEvidenceError(RuntimeError):
    """Raised when a required linked proof artifact is missing or malformed."""


class ReleaseLedgerService:
    """Build a package-portable release ledger from linked proof artifacts."""

    def __init__(self, *, output_path: Path) -> None:
        self.output_path = output_path
        self.base_dir = output_path.parent

    def build(
        self,
        *,
        build_dir: str,
        verification_report: str,
        readiness_manifest: str = '',
        build_evidence_report: str,
        acceptance_summary: str,
        live_evidence_bundle: str = "",
        requested_bindings: dict[str, bool] | None = None,
        requested_profiles: list[str] | None = None,
        installed_binaries: list[str] | None = None,
    ) -> dict[str, Any]:
        verification_payload = self._load_json_dict(verification_report, label='verification report', required=True)
        readiness_payload = self._load_json_dict(readiness_manifest, label='runtime readiness manifest', required=False)
        build_evidence_payload = self._load_json_dict(build_evidence_report, label='build evidence report', required=True)
        acceptance_payload = self._load_json_dict(acceptance_summary, label='acceptance summary', required=True)

        claim_guardrails = dict(verification_payload.get("claim_guardrails") or {})
        proof_scope = dict(verification_payload.get("proof_scope") or {})
        readiness_verification = dict(readiness_payload.get("verification") or {})
        verification_runtime = dict(verification_payload.get("runtime_readiness") or {})
        acceptance_scope = dict(acceptance_payload.get("acceptance_scope") or {})
        verification_snapshot = dict(acceptance_payload.get("verification_snapshot") or {})
        bundle_validation = dict(((verification_payload.get("real_environment") or {}).get("bundle_validation") or {}))

        requested_profiles_list = [str(item).strip() for item in (requested_profiles or []) if str(item).strip()]
        installed_binary_list = [str(item).strip() for item in (installed_binaries or []) if str(item).strip()]
        requested_bindings = {
            "with_sdk": bool((requested_bindings or {}).get("with_sdk", False)),
            "with_model": bool((requested_bindings or {}).get("with_model", False)),
        }

        return {
            "schema_version": "release.ledger.v1",
            "path_basis": "relative_to_ledger_dir",
            "build_dir": self._portable_path(build_dir),
            "verification_report": self._portable_path(verification_report),
            "readiness_manifest": self._portable_path(readiness_manifest),
            "build_evidence_report": self._portable_path(build_evidence_report),
            "acceptance_summary": self._portable_path(acceptance_summary),
            "live_evidence_bundle": self._portable_path(live_evidence_bundle),
            "requested_bindings": requested_bindings,
            "requested_profiles": requested_profiles_list,
            "installed_binaries": [self._portable_path(item) for item in installed_binary_list],
            "claim_boundary": str(
                verification_snapshot.get("claim_boundary")
                or build_evidence_payload.get("claim_boundary")
                or claim_guardrails.get("safe_summary", "")
            ),
            "verification_boundary": str(
                verification_snapshot.get("verification_boundary")
                or readiness_verification.get("verification_boundary", "")
                or verification_runtime.get("verification_boundary", "")
            ),
            "evidence_tier": str(
                verification_snapshot.get("evidence_tier")
                or readiness_verification.get("evidence_tier", "")
                or verification_runtime.get("evidence_tier", "")
            ),
            "reported_tiers": dict(
                verification_snapshot.get("reported_tiers")
                or verification_payload.get("reported_tiers")
                or {}
            ),
            "build_evidence_mode": str(
                verification_snapshot.get("build_evidence_mode")
                or build_evidence_payload.get("evidence_mode", "")
            ),
            "runtime_verification": {
                "summary_state": str(readiness_payload.get("summary_state", "") or verification_runtime.get("summary_state", "")),
                "live_runtime_ready": bool(readiness_verification.get("live_runtime_ready", verification_runtime.get("live_runtime_ready", False))),
                "live_runtime_verified": bool(readiness_verification.get("live_runtime_verified", verification_runtime.get("live_runtime_verified", False))),
                "source": "linked_manifest" if readiness_payload else "verification_report",
                "live_evidence_bundle_validated": bool(bundle_validation.get("valid", False)),
                "live_evidence_bundle_reason": str(bundle_validation.get("reason", "")),
            },
            "proof_scope": {
                "repository_proof": bool(proof_scope.get("repository_proof", False)),
                "profile_gate_proof": bool(proof_scope.get("profile_gate_proof", False)),
                "profile_phases": [str(item) for item in proof_scope.get("profile_phases", []) if str(item).strip()],
                "validated_profiles": [str(item) for item in acceptance_scope.get("validated_profiles", []) if str(item).strip()],
                "unvalidated_requested_profiles": [str(item) for item in acceptance_scope.get("unvalidated_requested_profiles", []) if str(item).strip()],
            },
            "guardrails": {
                "safe_summary": str(claim_guardrails.get("safe_summary", "")),
                "next_required_evidence": list(claim_guardrails.get("next_required_evidence", []) or []),
                "open_gap_rule": "do not claim stronger release readiness than the linked evidence closes",
            },
        }

    def write(self, payload: dict[str, Any]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _portable_path(self, raw: str) -> str:
        if not raw:
            return ""
        original = Path(raw)
        candidate = original if original.is_absolute() else (Path.cwd() / original)
        try:
            return os.path.relpath(candidate.resolve(strict=False), self.base_dir.resolve(strict=False))
        except ValueError:
            return str(original)

    @staticmethod
    def _load_json_dict(raw: str, *, label: str, required: bool) -> dict[str, Any]:
        if not raw:
            if required:
                raise ReleaseLedgerEvidenceError(f'{label} path is required')
            return {}
        candidate = Path(raw)
        if not candidate.is_file():
            if required:
                raise ReleaseLedgerEvidenceError(f'{label} file does not exist: {raw}')
            return {}
        try:
            payload = json.loads(candidate.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise ReleaseLedgerEvidenceError(f'{label} is not valid JSON: {raw} ({exc.msg})') from exc
        except OSError as exc:
            raise ReleaseLedgerEvidenceError(f'{label} could not be read: {raw} ({exc})') from exc
        if not isinstance(payload, dict):
            raise ReleaseLedgerEvidenceError(f'{label} must be a JSON object: {raw}')
        return payload
