from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.planning.types import LocalizationResult


@dataclass
class ScanPlanAdapterContext:
    """Immutable inputs plus mutable evidence for adapter execution.

    Attributes:
        stage: Planning stage identifier, e.g. ``preview`` or ``execution``.
        config: Runtime configuration used to derive timing and safety limits.
        localization: Optional localization result attached to the plan build.
        planner_context: Planner-side context such as surface/contact models.
        evidence: Adapter-produced evidence records appended in order.
    """

    stage: str
    config: RuntimeConfig
    localization: LocalizationResult | None = None
    planner_context: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


class ScanPlanRequestAdapter:
    """Base interface for deterministic scan-plan adapters."""

    name = "adapter"

    def apply(self, plan: ScanPlan, context: ScanPlanAdapterContext) -> ScanPlan:
        """Apply a deterministic mutation or enrichment to a scan plan.

        Args:
            plan: Candidate scan plan.
            context: Adapter execution context.

        Returns:
            Potentially updated scan plan.

        Raises:
            ValueError: When the adapter detects a non-recoverable plan defect.
        """
        raise NotImplementedError

    def _emit(self, context: ScanPlanAdapterContext, *, detail: str, metrics: dict[str, Any] | None = None) -> None:
        context.evidence.append({
            "name": self.name,
            "detail": str(detail),
            "metrics": dict(metrics or {}),
        })


class ResolveFrameAdapter(ScanPlanRequestAdapter):
    """Normalize pose frames and Euler ranges for runtime delivery."""

    name = "resolve_frames"

    def apply(self, plan: ScanPlan, context: ScanPlanAdapterContext) -> ScanPlan:
        normalized = 0

        def _normalize_angle(value: float) -> float:
            nonlocal normalized
            numeric = float(value)
            if not math.isfinite(numeric):
                normalized += 1
                return 0.0
            while numeric > 180.0:
                numeric -= 360.0
                normalized += 1
            while numeric < -180.0:
                numeric += 360.0
                normalized += 1
            return round(numeric, 3)

        for pose in [plan.approach_pose, plan.retreat_pose]:
            pose.rx = _normalize_angle(pose.rx)
            pose.ry = _normalize_angle(pose.ry)
            pose.rz = _normalize_angle(pose.rz)
        for segment in plan.segments:
            for waypoint in segment.waypoints:
                waypoint.rx = _normalize_angle(waypoint.rx)
                waypoint.ry = _normalize_angle(waypoint.ry)
                waypoint.rz = _normalize_angle(waypoint.rz)
        self._emit(context, detail="normalized waypoint frame/euler fields for runtime delivery", metrics={"normalized_angle_fields": normalized})
        return plan


class SurfaceConstraintAdapter(ScanPlanRequestAdapter):
    """Clamp scan-depth samples to the frozen surface corridor when required."""

    name = "surface_constraints"

    def apply(self, plan: ScanPlan, context: ScanPlanAdapterContext) -> ScanPlan:
        surface_model = dict(context.planner_context.get("surface_model", {}))
        if not surface_model:
            self._emit(context, detail="surface model unavailable; no corridor clamp applied", metrics={"adjusted_waypoints": 0})
            return plan
        surface_z = float(surface_model.get("surface_z_mm", 0.0) or 0.0)
        guard_mm = max(1.0, float(surface_model.get("clearance_mm", 4.0) or 4.0) * 0.25)
        adjusted = 0
        for segment in plan.segments:
            for waypoint in segment.waypoints:
                if context.stage in {"preview", "execution", "rescan"} and waypoint.z < surface_z - guard_mm:
                    waypoint.z = round(surface_z, 3)
                    adjusted += 1
        self._emit(
            context,
            detail="verified scan-waypoint depth against frozen surface corridor",
            metrics={"surface_z_mm": round(surface_z, 3), "guard_mm": round(guard_mm, 3), "adjusted_waypoints": adjusted},
        )
        return plan


class SafetyLimitAdapter(ScanPlanRequestAdapter):
    """Harden plan execution constraints and contact bands."""

    name = "safety_limits"

    def apply(self, plan: ScanPlan, context: ScanPlanAdapterContext) -> ScanPlan:
        max_duration = max((int(segment.estimated_duration_ms or 0) for segment in plan.segments), default=0)
        plan.execution_constraints.max_segment_duration_ms = max(plan.execution_constraints.max_segment_duration_ms, max_duration)
        contact_model = dict(context.planner_context.get("contact_model", {}))
        lower = float(contact_model.get("lower_band_n", plan.execution_constraints.allowed_contact_band.get("lower_n", 0.0)) or 0.0)
        upper = float(contact_model.get("upper_band_n", plan.execution_constraints.allowed_contact_band.get("upper_n", 0.0)) or 0.0)
        target = float(contact_model.get("target_force_n", 0.0) or 0.0)
        if plan.plan_kind == "execution":
            if upper <= lower:
                raise ValueError("execution plan safety envelope requires upper_n > lower_n")
            band = {"lower_n": lower, "upper_n": upper}
            plan.execution_constraints.allowed_contact_band = band
            for segment in plan.segments:
                if not segment.contact_band:
                    segment.contact_band = {**band, "target_n": target}
        self._emit(
            context,
            detail="hardened execution constraints and contact safety envelope",
            metrics={"max_segment_duration_ms": int(plan.execution_constraints.max_segment_duration_ms), "allowed_contact_band": dict(plan.execution_constraints.allowed_contact_band)},
        )
        return plan


class TimeParameterizationAdapter(ScanPlanRequestAdapter):
    """Reconcile per-segment durations with deterministic motion timing."""

    name = "time_parameterization"

    def apply(self, plan: ScanPlan, context: ScanPlanAdapterContext) -> ScanPlan:
        speed = max(float(context.config.scan_speed_mm_s or 0.0), 0.1)
        step = max(float(context.config.sample_step_mm or 0.0), 0.1)
        updated = 0
        for segment in plan.segments:
            nominal_duration = max(1, int(round((max(len(segment.waypoints) - 1, 1) * step / speed) * 1000.0)))
            if int(segment.estimated_duration_ms or 0) <= 0 or abs(int(segment.estimated_duration_ms or 0) - nominal_duration) > max(1000, nominal_duration):
                segment.estimated_duration_ms = nominal_duration
                updated += 1
        if plan.segments:
            plan.execution_constraints.max_segment_duration_ms = max(plan.execution_constraints.max_segment_duration_ms, max(int(segment.estimated_duration_ms or 0) for segment in plan.segments))
        self._emit(context, detail="reconciled estimated segment durations with deterministic scan timing", metrics={"updated_segments": updated, "sample_step_mm": step, "scan_speed_mm_s": speed})
        return plan


def _stable_segment_payload(segment) -> dict[str, Any]:
    payload = segment.to_dict()
    payload["segment_hash"] = ""
    return payload


def _stable_segment_hash(segment) -> str:
    return hashlib.sha256(json.dumps(_stable_segment_payload(segment), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _adapter_pipeline_payload(evidence: list[dict[str, Any]], stage: str, segment_hashes: list[str], plan_hash: str, template_hash: str) -> dict[str, Any]:
    return {
        "stage": stage,
        "applied_adapters": [entry.get("name", "") for entry in evidence],
        "adapter_evidence": list(evidence),
        "adapter_digest": hashlib.sha256(json.dumps(list(evidence), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest() if evidence else "",
        "plan_hash": plan_hash,
        "template_hash": template_hash,
        "canonical_plan_hash": plan_hash,
        "canonical_template_hash": template_hash,
        "segment_hashes": list(segment_hashes),
    }


def _stable_plan_hash(plan: ScanPlan, *, include_session_binding: bool) -> str:
    """Compute a deterministic hash from structural plan content only.

    The canonical digest intentionally excludes validation/score sidebands so
    replay, freeze and audit seals remain stable when the same geometric plan is
    re-materialized with refreshed diagnostics.
    """
    payload = plan.to_dict()
    payload["segments"] = [_stable_segment_payload(segment) for segment in plan.segments]
    payload["validation_summary"] = {}
    payload["score_summary"] = {}
    if not include_session_binding:
        payload["session_id"] = ""
        payload["plan_id"] = ""
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


class PlanDigestAdapter(ScanPlanRequestAdapter):
    """Recompute deterministic segment digests and attach pipeline metadata."""

    name = "plan_digest"

    def apply(self, plan: ScanPlan, context: ScanPlanAdapterContext) -> ScanPlan:
        segment_hashes: list[str] = []
        for segment in plan.segments:
            segment.segment_hash = _stable_segment_hash(segment)
            segment_hashes.append(segment.segment_hash)
        canonical_plan_hash = _stable_plan_hash(plan, include_session_binding=True)
        canonical_template_hash = _stable_plan_hash(plan, include_session_binding=False)
        self._emit(context, detail="recomputed plan/segment digests after adapter pipeline", metrics={"segment_count": len(segment_hashes)})
        plan.validation_summary = {
            **dict(plan.validation_summary),
            "adapter_pipeline": _adapter_pipeline_payload(
                context.evidence,
                context.stage,
                segment_hashes,
                canonical_plan_hash,
                canonical_template_hash,
            ),
        }
        return plan


class ScanPlanAdapterPipeline:
    """Execute a deterministic adapter chain for preview/execution plans."""

    def __init__(self, adapters: list[ScanPlanRequestAdapter]) -> None:
        self.adapters = list(adapters)

    def apply(self, plan: ScanPlan, context: ScanPlanAdapterContext) -> ScanPlan:
        """Apply adapters in-order and return the fully materialized plan.

        Args:
            plan: Candidate plan.
            context: Mutable adapter context.

        Returns:
            Final adapted plan.

        Raises:
            ValueError: Propagated from any adapter that rejects the plan.
        """
        current = plan
        for adapter in self.adapters:
            current = adapter.apply(current, context)
        return current
