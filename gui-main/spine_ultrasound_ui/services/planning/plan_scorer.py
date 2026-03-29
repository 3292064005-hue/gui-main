from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.planning.surface_model import SurfaceModel
from spine_ultrasound_ui.services.planning.types import LocalizationResult


class PlanScorer:
    def score(
        self,
        plan: ScanPlan,
        *,
        config: RuntimeConfig,
        localization: LocalizationResult | None = None,
        surface_model: SurfaceModel | None = None,
    ) -> dict[str, Any]:
        segment_count = max(1, len(plan.segments))
        estimated_duration_ms = sum(int(segment.estimated_duration_ms or 0) for segment in plan.segments)
        quality = min(1.0, max(config.image_quality_threshold, 0.75) + (0.08 if localization and localization.confidence > 0.85 else 0.0))
        coverage = min(1.0, 0.88 + (0.03 * min(segment_count, 4)))
        contact_risk = min(1.0, max(0.05, 0.18 + (0.02 * max(segment_count - 4, 0))))
        if surface_model is not None:
            contact_risk = min(1.0, contact_risk + abs(surface_model.local_tilt_deg) / 180.0 + surface_model.curvature_estimate)
        if plan.execution_constraints.allowed_contact_band:
            band = plan.execution_constraints.allowed_contact_band
            contact_risk = min(1.0, contact_risk + max(0.0, 0.3 - (float(band.get('upper_n', 0.0)) - float(band.get('lower_n', 0.0)))) * 0.4)
        smoothness = max(0.0, 1.0 - (0.05 * max(segment_count - 1, 0)))
        duration_score = max(0.0, 1.0 - min(1.0, estimated_duration_ms / 180_000.0))
        composite = round((quality * 0.30) + (coverage * 0.23) + (smoothness * 0.17) + (duration_score * 0.12) + ((1.0 - contact_risk) * 0.18), 4)
        return {
            "planner_version": plan.planner_version,
            "plan_kind": plan.plan_kind,
            "composite_score": composite,
            "quality_score": round(quality, 4),
            "coverage_score": round(coverage, 4),
            "contact_risk": round(contact_risk, 4),
            "smoothness_score": round(smoothness, 4),
            "duration_score": round(duration_score, 4),
            "estimated_duration_ms": estimated_duration_ms,
            "segment_count": segment_count,
            "execution_constraints": plan.execution_constraints.to_dict(),
        }
