from __future__ import annotations

"""Shared normalization for authoritative runtime/control-plane facts.

This module centralizes extraction and normalization of the runtime-owned facts
that higher Python layers are allowed to *consume* but not fabricate. The goal
is to keep authority, final verdict, session freeze, and applied runtime config
in a single reusable place across API, direct-core, and mock backends.
"""

from typing import Any, Mapping

from spine_ultrasound_ui.models import RuntimeConfig


class BackendAuthoritativeContractService:
    """Normalize authoritative runtime envelopes and verdict snapshots.

    The service accepts payloads from multiple sources (API control-plane,
    runtime command replies, mock runtime surfaces) and returns a stable,
    additive-only dictionary shape.
    """

    DEFAULT_PROTOCOL_VERSION = 1
    FALLBACK_OWNER = {
        "actor_id": "runtime-authority",
        "workspace": "runtime",
        "role": "runtime",
        "session_id": "",
    }

    def build(
        self,
        *,
        authority_source: str,
        control_authority: Mapping[str, Any] | None,
        runtime_config_applied: Mapping[str, Any] | RuntimeConfig | None,
        desired_runtime_config: Mapping[str, Any] | RuntimeConfig | None = None,
        session_freeze: Mapping[str, Any] | None = None,
        final_verdict: Mapping[str, Any] | None = None,
        plan_digest: Mapping[str, Any] | None = None,
        protocol_version: int | None = None,
        detail: str = "",
        authoritative_runtime_envelope_present: bool = False,
        envelope_origin: str = "unknown",
    ) -> dict[str, Any]:
        """Build a normalized authoritative envelope.

        Args:
            authority_source: Runtime/system that owns the authoritative facts.
            control_authority: Runtime-issued control-authority payload.
            runtime_config_applied: Applied runtime config snapshot.
            desired_runtime_config: Optional desired/local config snapshot.
            session_freeze: Optional frozen session binding snapshot.
            final_verdict: Optional authoritative final verdict payload.
            plan_digest: Optional plan identity/digest information.
            protocol_version: Protocol version for the envelope.
            detail: Human-readable explanatory detail.
            authoritative_runtime_envelope_present: True only when the runtime
                explicitly published an authoritative envelope.
            envelope_origin: Source used to derive this envelope.

        Returns:
            A normalized authoritative envelope dictionary.
        """
        normalized_authority = self.normalize_control_authority(control_authority, authority_source=authority_source)
        applied_config = self._normalize_runtime_config_payload(runtime_config_applied)
        desired_config = self._normalize_runtime_config_payload(desired_runtime_config)
        freeze = self.normalize_session_freeze(session_freeze)
        verdict = self.normalize_final_verdict(final_verdict)
        digest = self.normalize_plan_digest(plan_digest, session_freeze=freeze, final_verdict=verdict)
        summary_state = self._derive_summary_state(
            normalized_authority,
            verdict,
            freeze,
            authoritative_runtime_envelope_present=authoritative_runtime_envelope_present,
        )
        summary_label = {
            "ready": "运行时权威快照可用",
            "degraded": "运行时权威快照降级",
            "blocked": "运行时权威快照阻塞",
        }.get(summary_state, "运行时权威快照")
        synthesized = not bool(authoritative_runtime_envelope_present)
        return {
            "summary_state": summary_state,
            "summary_label": summary_label,
            "detail": detail or self._default_detail(authority_source, normalized_authority, synthesized=synthesized, envelope_origin=envelope_origin),
            "authority_source": authority_source,
            "protocol_version": self._coerce_int(protocol_version, self.DEFAULT_PROTOCOL_VERSION),
            "control_authority": normalized_authority,
            "runtime_config_applied": applied_config,
            "desired_runtime_config": desired_config,
            "session_freeze": freeze,
            "plan_digest": digest,
            "final_verdict": verdict,
            "authoritative_runtime_envelope_present": bool(authoritative_runtime_envelope_present),
            "envelope_origin": envelope_origin,
            "synthesized": synthesized,
        }

    def normalize_payload(
        self,
        payload: Mapping[str, Any] | None,
        *,
        authority_source: str,
        desired_runtime_config: Mapping[str, Any] | RuntimeConfig | None = None,
        fallback_control_authority: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Normalize a raw payload into the authoritative envelope shape.

        Args:
            payload: Raw reply/control-plane payload.
            authority_source: Source label used when the payload omits one.
            desired_runtime_config: Optional desired/local runtime config.
            fallback_control_authority: Explicit fallback authority snapshot.

        Returns:
            Normalized authoritative runtime envelope.
        """
        data = self._as_dict(payload)
        if data.get("authoritative_runtime_envelope"):
            authoritative = self._as_dict(data.get("authoritative_runtime_envelope"))
            return self.build(
                authority_source=str(authoritative.get("authority_source") or authority_source),
                control_authority=self._as_dict(authoritative.get("control_authority")),
                runtime_config_applied=authoritative.get("runtime_config_applied") or authoritative.get("runtime_config"),
                desired_runtime_config=desired_runtime_config,
                session_freeze=authoritative.get("session_freeze"),
                final_verdict=authoritative.get("final_verdict") or authoritative,
                plan_digest=authoritative.get("plan_digest"),
                protocol_version=self._coerce_int(authoritative.get("protocol_version"), self.DEFAULT_PROTOCOL_VERSION),
                detail=str(authoritative.get("detail") or ""),
                authoritative_runtime_envelope_present=True,
                envelope_origin="authoritative_runtime_envelope",
            )
        control_plane = self._extract_control_plane(data)
        if control_plane and control_plane.get("authoritative_runtime_envelope"):
            authoritative = self._as_dict(control_plane.get("authoritative_runtime_envelope"))
            return self.build(
                authority_source=str(authoritative.get("authority_source") or control_plane.get("authority_source") or authority_source),
                control_authority=self._as_dict(authoritative.get("control_authority")),
                runtime_config_applied=authoritative.get("runtime_config_applied") or authoritative.get("runtime_config"),
                desired_runtime_config=desired_runtime_config,
                session_freeze=authoritative.get("session_freeze"),
                final_verdict=authoritative.get("final_verdict") or authoritative,
                plan_digest=authoritative.get("plan_digest"),
                protocol_version=self._coerce_int(authoritative.get("protocol_version") or control_plane.get("protocol_version"), self.DEFAULT_PROTOCOL_VERSION),
                detail=str(authoritative.get("detail") or control_plane.get("detail") or ""),
                authoritative_runtime_envelope_present=True,
                envelope_origin="control_plane.authoritative_runtime_envelope",
            )
        authority = (
            self._as_dict(data.get("control_authority"))
            or self._as_dict(control_plane.get("control_authority"))
            or self._as_dict(fallback_control_authority)
        )
        runtime_config = (
            data.get("runtime_config_applied")
            or data.get("runtime_config")
            or control_plane.get("runtime_config_applied")
            or control_plane.get("runtime_config")
        )
        origin = "payload_control_plane_synthesized" if control_plane else "payload_synthesized"
        return self.build(
            authority_source=str(data.get("authority_source") or control_plane.get("authority_source") or authority_source),
            control_authority=authority,
            runtime_config_applied=runtime_config,
            desired_runtime_config=desired_runtime_config,
            session_freeze=data.get("session_freeze") or control_plane.get("session_freeze"),
            final_verdict=data.get("final_verdict") or control_plane.get("final_verdict") or data,
            plan_digest=data.get("plan_digest") or control_plane.get("plan_digest"),
            protocol_version=self._coerce_int(data.get("protocol_version") or control_plane.get("protocol_version"), self.DEFAULT_PROTOCOL_VERSION),
            detail=str(data.get("detail") or control_plane.get("detail") or ""),
            authoritative_runtime_envelope_present=False,
            envelope_origin=origin,
        )

    def normalize_control_authority(
        self,
        payload: Mapping[str, Any] | None,
        *,
        authority_source: str,
    ) -> dict[str, Any]:
        """Normalize control-authority shape while preserving compatibility."""
        data = self._as_dict(payload)
        owner = self._as_dict(data.get("owner")) or dict(self.FALLBACK_OWNER)
        owner.setdefault("actor_id", self.FALLBACK_OWNER["actor_id"])
        owner.setdefault("workspace", self.FALLBACK_OWNER["workspace"])
        owner.setdefault("role", self.FALLBACK_OWNER["role"])
        owner.setdefault("session_id", "")
        active_lease = self._as_dict(data.get("active_lease"))
        if not active_lease:
            active_lease = {
                "lease_id": "",
                "actor_id": owner.get("actor_id", ""),
                "workspace": owner.get("workspace", ""),
                "role": owner.get("role", ""),
                "session_id": owner.get("session_id", ""),
                "expires_in_s": 0,
                "source": authority_source,
            }
        owner_provenance = self._as_dict(data.get("owner_provenance"))
        owner_provenance.setdefault("source", authority_source)
        return {
            "summary_state": str(data.get("summary_state", "degraded" if not payload else "ready")),
            "summary_label": str(data.get("summary_label", "控制权快照")),
            "detail": str(data.get("detail", "")),
            "owner": owner,
            "active_lease": active_lease,
            "owner_provenance": owner_provenance,
            "workspace_binding": str(data.get("workspace_binding", owner.get("workspace", ""))),
            "session_binding": str(data.get("session_binding", owner.get("session_id", ""))),
            "conflict_reason": str(data.get("conflict_reason", "")),
            "authority_source": authority_source,
            "blockers": list(data.get("blockers", [])) if isinstance(data.get("blockers"), list) else [],
            "warnings": list(data.get("warnings", [])) if isinstance(data.get("warnings"), list) else [],
        }

    def normalize_final_verdict(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        """Normalize final-verdict payloads from replies or control-plane snapshots."""
        data = self._as_dict(payload)
        if isinstance(data.get("accepted"), bool):
            policy_state = str(data.get("policy_state", "ready" if data.get("accepted") else "idle"))
            return {
                "accepted": bool(data.get("accepted")),
                "reason": str(data.get("reason", "")),
                "policy_state": policy_state,
                "source": str(data.get("source", data.get("authority_source", ""))),
                "evidence_id": str(data.get("evidence_id", "")),
                "advisory_only": bool(data.get("advisory_only", False)),
                "summary_state": str(data.get("summary_state", policy_state)),
                "summary_label": str(data.get("summary_label", "运行时前检")),
                "detail": str(data.get("detail", data.get("reason", ""))),
                "blockers": list(data.get("blockers", [])) if isinstance(data.get("blockers"), list) else [],
                "warnings": list(data.get("warnings", [])) if isinstance(data.get("warnings"), list) else [],
                "plan_metrics": self._as_dict(data.get("plan_metrics")),
            }
        nested = self._as_dict(data.get("final_verdict"))
        if nested and isinstance(nested.get("accepted"), bool):
            return self.normalize_final_verdict({**data, **nested})
        control_plane = self._extract_control_plane(data)
        for candidate in (
            self._as_dict(control_plane.get("model_precheck")),
            self._as_dict(self._as_dict(data.get("unified_snapshot")).get("model_precheck")),
        ):
            nested_verdict = self._as_dict(candidate.get("final_verdict"))
            if nested_verdict and isinstance(nested_verdict.get("accepted"), bool):
                return self.normalize_final_verdict({**candidate, **nested_verdict})
        return {}

    def normalize_session_freeze(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        """Normalize session-freeze payload and derived digests."""
        data = self._as_dict(payload)
        if not data:
            return {}
        return {
            "session_locked": bool(data.get("session_locked", False)),
            "session_id": str(data.get("session_id", "")),
            "session_dir": str(data.get("session_dir", "")),
            "locked_at_ns": self._coerce_int(data.get("locked_at_ns"), 0),
            "plan_hash": str(data.get("plan_hash", "")),
            "active_segment": self._coerce_int(data.get("active_segment"), 0),
            "tool_name": str(data.get("tool_name", "")),
            "tcp_name": str(data.get("tcp_name", "")),
            "load_kg": data.get("load_kg"),
            "rt_mode": str(data.get("rt_mode", "")),
            "cartesian_impedance": list(data.get("cartesian_impedance", [])) if isinstance(data.get("cartesian_impedance"), list) else [],
            "desired_wrench_n": list(data.get("desired_wrench_n", [])) if isinstance(data.get("desired_wrench_n"), list) else [],
            "freeze_version": str(data.get("freeze_version", "")),
            "runtime_profile_hash": str(data.get("runtime_profile_hash", "")),
            "sdk_boundary_hash": str(data.get("sdk_boundary_hash", "")),
            "executor_profile_hash": str(data.get("executor_profile_hash", "")),
        }

    def normalize_plan_digest(
        self,
        payload: Mapping[str, Any] | None,
        *,
        session_freeze: Mapping[str, Any] | None = None,
        final_verdict: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Normalize plan identity facts.

        Args:
            payload: Plan digest payload.
            session_freeze: Optional normalized session freeze.
            final_verdict: Optional normalized final verdict.
        """
        data = self._as_dict(payload)
        freeze = self._as_dict(session_freeze)
        verdict = self._as_dict(final_verdict)
        plan_metrics = self._as_dict(verdict.get("plan_metrics"))
        return {
            "plan_id": str(data.get("plan_id") or plan_metrics.get("plan_id") or ""),
            "plan_hash": str(data.get("plan_hash") or plan_metrics.get("plan_hash") or freeze.get("plan_hash") or ""),
            "locked_scan_plan_hash": str(data.get("locked_scan_plan_hash") or freeze.get("plan_hash") or ""),
            "session_freeze_consistent": bool(data.get("session_freeze_consistent", True)),
        }

    def extract_final_verdict(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        """Compatibility wrapper used by existing backends."""
        return self.normalize_final_verdict(payload)

    @staticmethod
    def _normalize_runtime_config_payload(payload: Mapping[str, Any] | RuntimeConfig | None) -> dict[str, Any]:
        if isinstance(payload, RuntimeConfig):
            return payload.to_dict()
        data = dict(payload or {})
        runtime_config = data.get("runtime_config")
        if isinstance(runtime_config, Mapping):
            return dict(runtime_config)
        return data

    @staticmethod
    def _as_dict(payload: Mapping[str, Any] | None) -> dict[str, Any]:
        return dict(payload or {})

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        try:
            if value is None or value == "":
                return int(default)
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    def _extract_control_plane(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        data = dict(payload or {})
        return self._as_dict(data.get("control_plane_snapshot") or data.get("control_plane"))

    @staticmethod
    def _derive_summary_state(
        control_authority: Mapping[str, Any],
        final_verdict: Mapping[str, Any],
        session_freeze: Mapping[str, Any],
        *,
        authoritative_runtime_envelope_present: bool,
    ) -> str:
        authority_state = str(control_authority.get("summary_state", "degraded"))
        verdict_state = str(final_verdict.get("summary_state", final_verdict.get("policy_state", "ready" if final_verdict.get("accepted") else "idle")))
        if authority_state == "blocked" or verdict_state == "blocked":
            return "blocked"
        if session_freeze and not bool(session_freeze.get("session_locked", True)):
            return "degraded"
        if authority_state in {"degraded", "warning", "unknown"} or verdict_state in {"degraded", "warning", "idle", "unknown"}:
            return "degraded"
        if not authoritative_runtime_envelope_present:
            return "degraded"
        return "ready"

    @staticmethod
    def _default_detail(authority_source: str, control_authority: Mapping[str, Any], *, synthesized: bool, envelope_origin: str) -> str:
        owner = dict(control_authority.get("owner", {}))
        actor = owner.get("actor_id", "runtime-authority")
        workspace = owner.get("workspace", "runtime")
        if synthesized:
            return f"authority_source={authority_source} owner={actor}@{workspace} synthesized_from={envelope_origin}; authoritative_runtime_envelope missing"
        return f"authority_source={authority_source} owner={actor}@{workspace} envelope_origin={envelope_origin}"
