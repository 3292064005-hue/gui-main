from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import ScanPlan
from spine_ultrasound_ui.services.planning.types import LocalizationResult


class PlanValidator:
    def validate(
        self,
        plan: ScanPlan,
        *,
        expected_axis_count: int = 6,
        corridor_width_mm: float | None = None,
        strip_spacing_mm: float | None = None,
        localization: LocalizationResult | None = None,
    ) -> dict[str, Any]:
        if expected_axis_count != 6:
            raise ValueError(f"unsupported axis count: {expected_axis_count}")
        if not plan.segments:
            raise ValueError("scan plan must contain at least one segment")
        total_waypoints = 0
        estimated_duration_ms = 0
        previous_segment_id = 0
        y_values: list[float] = []
        segment_ids: list[int] = []
        patch_segments = 0
        seen_hashes: set[str] = set()
        for segment in plan.segments:
            if segment.segment_id <= 0:
                raise ValueError("segment_id must be positive")
            if previous_segment_id and segment.segment_id != previous_segment_id + 1:
                raise ValueError("segment ids must be contiguous")
            previous_segment_id = segment.segment_id
            segment_ids.append(segment.segment_id)
            if segment.segment_hash and segment.segment_hash in seen_hashes:
                raise ValueError("segment hashes must be unique")
            if segment.segment_hash:
                seen_hashes.add(segment.segment_hash)
            if not segment.waypoints:
                raise ValueError(f"segment {segment.segment_id} has no waypoints")
            if len(segment.waypoints) < 2 and plan.plan_kind in {"preview", "execution"}:
                raise ValueError(f"segment {segment.segment_id} must contain at least two waypoints")
            if segment.needs_resample:
                patch_segments += 1
            if plan.plan_kind == "execution" and segment.contact_band:
                lower = float(segment.contact_band.get("lower_n", 0.0) or 0.0)
                upper = float(segment.contact_band.get("upper_n", 0.0) or 0.0)
                if upper <= lower:
                    raise ValueError("execution segment contact band must have upper_n > lower_n")
            for point in segment.waypoints:
                for axis in (point.x, point.y, point.z, point.rx, point.ry, point.rz):
                    if not isinstance(axis, (float, int)):
                        raise ValueError("waypoint values must be numeric")
                y_values.append(float(point.y))
            total_waypoints += len(segment.waypoints)
            estimated_duration_ms += int(segment.estimated_duration_ms or 0)
        span_y_mm = round(max(y_values) - min(y_values), 3) if y_values else 0.0
        if corridor_width_mm is not None and span_y_mm > corridor_width_mm + 5.0:
            raise ValueError("plan lateral span exceeds localization corridor")
        max_segment_duration_ms = int(plan.execution_constraints.max_segment_duration_ms or 0)
        if max_segment_duration_ms and max((segment.estimated_duration_ms for segment in plan.segments), default=0) > max_segment_duration_ms:
            raise ValueError("plan exceeds execution constraint max_segment_duration_ms")
        return {
            "validated": True,
            "planner_version": plan.planner_version,
            "registration_hash": plan.registration_hash,
            "plan_kind": plan.plan_kind,
            "segment_count": len(plan.segments),
            "segment_ids": segment_ids,
            "total_waypoints": total_waypoints,
            "estimated_duration_ms": estimated_duration_ms,
            "corridor_width_mm": round(float(corridor_width_mm or 0.0), 3),
            "strip_spacing_mm": round(float(strip_spacing_mm or 0.0), 3),
            "lateral_span_mm": span_y_mm,
            "contact_probe_required": any(segment.requires_contact_probe for segment in plan.segments),
            "localization_confidence": float(localization.confidence) if localization is not None else 0.0,
            "rescan_patch_segment_count": patch_segments,
            "execution_constraints": plan.execution_constraints.to_dict(),
        }
