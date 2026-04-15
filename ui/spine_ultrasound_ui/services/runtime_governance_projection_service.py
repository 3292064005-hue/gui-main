from __future__ import annotations

"""Canonical runtime-governance projection helpers.

This service centralizes read-only extraction of runtime-owned authority,
final-verdict, and authoritative-envelope facts. Higher Python layers may use
these projections for rendering, readiness checks, and session summaries, but
must not synthesize or override the underlying runtime truth.
"""

from typing import Any, Mapping

from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService


class RuntimeGovernanceProjectionService:
    """Build a single consumer-facing projection for governance facts.

    The service accepts the heterogeneous payloads already present in desktop,
    headless, and session-summary paths and returns one additive-only
    projection. It intentionally does not invent authoritative data; when the
    runtime omitted a field, the corresponding projection field remains empty or
    degraded.
    """

    def __init__(self, authoritative_service: BackendAuthoritativeContractService | None = None) -> None:
        self._authoritative_service = authoritative_service or BackendAuthoritativeContractService()

    def build_projection(
        self,
        *,
        backend_link: Mapping[str, Any] | None = None,
        control_plane_snapshot: Mapping[str, Any] | None = None,
        model_report: Mapping[str, Any] | None = None,
        sdk_runtime: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the canonical governance projection.

        Args:
            backend_link: Backend-link payload containing ``control_plane``.
            control_plane_snapshot: Unified control-plane snapshot payload.
            model_report: Current runtime-verdict/model-precheck report.
            sdk_runtime: Runtime contract snapshot.

        Returns:
            Projection dictionary with canonical ``control_authority``,
            ``final_verdict``, and ``authoritative_runtime_envelope`` entries.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            - Projection fields are always copied, never returned by reference.
            - Authoritative facts are preferred in this order:
              authoritative runtime envelope -> control-plane projection ->
              release contract -> explicit model report fallback.
            - Missing authoritative facts degrade to empty dictionaries rather
              than compatibility synthesis.
        """
        backend_link_dict = self._as_dict(backend_link)
        control_plane_dict = self._as_dict(control_plane_snapshot)
        model_report_dict = self._as_dict(model_report)
        sdk_runtime_dict = self._as_dict(sdk_runtime)

        authoritative_envelope = self.resolve_authoritative_runtime_envelope(
            backend_link=backend_link_dict,
            control_plane_snapshot=control_plane_dict,
        )
        control_authority = self.resolve_control_authority(
            backend_link=backend_link_dict,
            control_plane_snapshot=control_plane_dict,
            authoritative_runtime_envelope=authoritative_envelope,
        )
        final_verdict = self.resolve_final_verdict(
            backend_link=backend_link_dict,
            control_plane_snapshot=control_plane_dict,
            model_report=model_report_dict,
            sdk_runtime=sdk_runtime_dict,
            authoritative_runtime_envelope=authoritative_envelope,
        )
        authority_source = str(
            authoritative_envelope.get("authority_source")
            or final_verdict.get("source")
            or control_authority.get("authority_source")
            or model_report_dict.get("authority_source")
            or ""
        )
        summary_state = self._derive_summary_state(control_authority=control_authority, final_verdict=final_verdict)
        summary_label = {
            "ready": "治理投影已收敛",
            "degraded": "治理投影降级",
            "blocked": "治理投影阻塞",
        }.get(summary_state, "治理投影")
        detail = str(
            final_verdict.get("detail")
            or final_verdict.get("reason")
            or control_authority.get("detail")
            or authoritative_envelope.get("detail")
            or ""
        )
        model_precheck = dict(model_report_dict)
        if final_verdict and not model_precheck.get("final_verdict"):
            model_precheck["final_verdict"] = dict(final_verdict)
        if authority_source and not model_precheck.get("authority_source"):
            model_precheck["authority_source"] = authority_source
        if final_verdict and not model_precheck.get("verdict_kind"):
            model_precheck["verdict_kind"] = "final"
        return {
            "summary_state": summary_state,
            "summary_label": summary_label,
            "detail": detail,
            "authority_source": authority_source,
            "authoritative_runtime_envelope": authoritative_envelope,
            "control_authority": control_authority,
            "ownership_state": dict(control_authority),
            "final_verdict": final_verdict,
            "model_precheck": model_precheck,
            "authoritative_verdict_available": bool(final_verdict),
            "runtime_doctor": self._resolve_runtime_doctor(control_plane_snapshot=control_plane_dict, sdk_runtime=sdk_runtime_dict),
        }

    def resolve_authoritative_runtime_envelope(
        self,
        *,
        backend_link: Mapping[str, Any] | None = None,
        control_plane_snapshot: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the canonical authoritative runtime envelope when available."""
        backend_link_dict = self._as_dict(backend_link)
        control_plane_dict = self._as_dict(control_plane_snapshot)
        control_plane = self._as_dict(backend_link_dict.get("control_plane"))
        authoritative_projection = self._as_dict(control_plane_dict.get("authoritative_projection"))
        for candidate in (
            control_plane.get("authoritative_runtime_envelope"),
            backend_link_dict.get("authoritative_runtime_envelope"),
            control_plane_dict.get("authoritative_runtime_envelope"),
            authoritative_projection.get("authoritative_runtime_envelope"),
        ):
            candidate_dict = self._as_dict(candidate)
            if not candidate_dict:
                continue
            if candidate_dict.get("control_authority") or candidate_dict.get("final_verdict") or candidate_dict.get("runtime_config_applied"):
                return self._authoritative_service.build(
                    authority_source=str(candidate_dict.get("authority_source") or "governance_projection"),
                    control_authority=self._as_dict(candidate_dict.get("control_authority")),
                    runtime_config_applied=candidate_dict.get("runtime_config_applied") or candidate_dict.get("runtime_config"),
                    session_freeze=candidate_dict.get("session_freeze"),
                    final_verdict=self._as_dict(candidate_dict.get("final_verdict")),
                    plan_digest=self._as_dict(candidate_dict.get("plan_digest")),
                    write_capabilities=self._as_dict(candidate_dict.get("write_capabilities")),
                    protocol_version=candidate_dict.get("protocol_version"),
                    detail=str(candidate_dict.get("detail") or ""),
                    authoritative_runtime_envelope_present=bool(candidate_dict.get("authoritative_runtime_envelope_present", True)),
                    envelope_origin=str(candidate_dict.get("envelope_origin") or "direct_authoritative_runtime_envelope"),
                )
            normalized = self._authoritative_service.normalize_payload(
                candidate_dict,
                authority_source=str(candidate_dict.get("authority_source") or "governance_projection"),
            )
            if normalized:
                return normalized
        return {}

    def resolve_control_authority(
        self,
        *,
        backend_link: Mapping[str, Any] | None = None,
        control_plane_snapshot: Mapping[str, Any] | None = None,
        authoritative_runtime_envelope: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve the single control-authority consumer projection."""
        backend_link_dict = self._as_dict(backend_link)
        control_plane_dict = self._as_dict(control_plane_snapshot)
        control_plane = self._as_dict(backend_link_dict.get("control_plane"))
        projection = self._as_dict(control_plane_dict.get("authoritative_projection"))
        envelope = self._as_dict(authoritative_runtime_envelope)
        authority_source = str(
            envelope.get("authority_source")
            or control_plane.get("authority_source")
            or projection.get("authority_source")
            or "governance_projection"
        )
        for candidate in (
            envelope.get("control_authority"),
            control_plane_dict.get("ownership_state"),
            control_plane_dict.get("control_authority"),
            control_plane.get("control_authority"),
            backend_link_dict.get("control_authority"),
            projection.get("control_authority"),
        ):
            authority = self._authoritative_service.normalize_control_authority(self._as_dict(candidate), authority_source=authority_source)
            if authority and authority.get("summary_state") != "degraded":
                return authority
            if authority and candidate:
                return authority
        return self._authoritative_service.normalize_control_authority({}, authority_source=authority_source)

    def resolve_final_verdict(
        self,
        *,
        backend_link: Mapping[str, Any] | None = None,
        control_plane_snapshot: Mapping[str, Any] | None = None,
        model_report: Mapping[str, Any] | None = None,
        sdk_runtime: Mapping[str, Any] | None = None,
        authoritative_runtime_envelope: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve the canonical authoritative final verdict."""
        backend_link_dict = self._as_dict(backend_link)
        control_plane_dict = self._as_dict(control_plane_snapshot)
        model_report_dict = self._as_dict(model_report)
        sdk_runtime_dict = self._as_dict(sdk_runtime)
        control_plane = self._as_dict(backend_link_dict.get("control_plane"))
        projection = self._as_dict(control_plane_dict.get("authoritative_projection"))
        envelope = self._as_dict(authoritative_runtime_envelope)
        release_contract = self._as_dict(sdk_runtime_dict.get("release_contract"))
        authoritative_candidates = (
            envelope.get("final_verdict"),
            control_plane_dict.get("final_verdict"),
            control_plane.get("final_verdict"),
            release_contract.get("final_verdict"),
            projection.get("final_verdict"),
        )
        for candidate in authoritative_candidates:
            verdict = self._authoritative_service.normalize_final_verdict(self._as_dict(candidate))
            if verdict:
                return verdict
        advisory_fallbacks = (
            self._as_dict(model_report_dict.get("final_verdict")),
            model_report_dict,
        )
        for candidate in advisory_fallbacks:
            verdict = self._authoritative_service.normalize_final_verdict(self._as_dict(candidate))
            if verdict:
                return verdict
        return {}

    @staticmethod
    def _as_dict(payload: Mapping[str, Any] | None) -> dict[str, Any]:
        return dict(payload or {})

    @staticmethod
    def _resolve_runtime_doctor(*, control_plane_snapshot: Mapping[str, Any], sdk_runtime: Mapping[str, Any]) -> dict[str, Any]:
        control_plane_dict = dict(control_plane_snapshot or {})
        sdk_runtime_dict = dict(sdk_runtime or {})
        return dict(control_plane_dict.get("runtime_doctor") or sdk_runtime_dict.get("mainline_runtime_doctor") or {})

    @staticmethod
    def _derive_summary_state(*, control_authority: Mapping[str, Any], final_verdict: Mapping[str, Any]) -> str:
        authority_state = str(control_authority.get("summary_state", "degraded"))
        verdict_state = str(final_verdict.get("summary_state", final_verdict.get("policy_state", "ready" if final_verdict.get("accepted") else "idle")))
        if authority_state == "blocked" or verdict_state == "blocked":
            return "blocked"
        if authority_state in {"degraded", "warning", "unknown"}:
            return "degraded"
        if final_verdict and verdict_state in {"degraded", "warning", "idle", "unknown"}:
            return "degraded"
        if not final_verdict:
            return "degraded"
        return "ready"
