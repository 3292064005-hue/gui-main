from __future__ import annotations

import hashlib
import json

from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan, ScanSegment, ScanWaypoint
from spine_ultrasound_ui.services.planning.plan_validator import PlanValidator
from spine_ultrasound_ui.services.planning.surface_model import SurfaceModelBuilder
from spine_ultrasound_ui.services.planning.types import LocalizationResult
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile
from spine_ultrasound_ui.utils import now_ns


class PreviewPlanner:
    version = "deterministic_preview_planner_v3"

    def __init__(self, validator: PlanValidator | None = None, surface_builder: SurfaceModelBuilder | None = None) -> None:
        self.validator = validator or PlanValidator()
        self.surface_builder = surface_builder or SurfaceModelBuilder()

    @staticmethod
    def _adaptive_segment_count(*, corridor_width_mm: float, config: RuntimeConfig, strip_width_mm: float) -> int:
        effective_spacing = max(1.0, min(config.strip_width_mm, strip_width_mm) - max(config.strip_overlap_mm, 0.0))
        requested = max(1, int(round(corridor_width_mm / effective_spacing)))
        return max(1, requested)

    def build(self, *, experiment_id: str, localization: LocalizationResult, config: RuntimeConfig) -> tuple[ScanPlan, dict[str, float]]:
        if not localization.status.ready:
            raise ValueError("localization result is not ready")
        profile = load_xmate_profile()
        corridor = dict(localization.patient_registration.get("scan_corridor", {}))
        center_y = float(corridor.get("centerline_mm", {}).get("y", localization.roi_center_y))
        surface_model = self.surface_builder.build(
            localization,
            default_length_mm=config.segment_length_mm * max(1, localization.segment_count),
            default_width_mm=max(profile.strip_width_mm, localization.segment_count * 4.0),
            clearance_mm=profile.approach_clearance_mm,
        )
        corridor_start = dict(corridor.get("start_mm", {}))
        corridor_width = float(surface_model.corridor_width_mm)
        corridor_length = float(surface_model.corridor_length_mm)
        segment_count = self._adaptive_segment_count(corridor_width_mm=corridor_width, config=config, strip_width_mm=profile.strip_width_mm)
        x_origin = float(corridor_start.get("x", 110.0))
        surface_z = float(surface_model.surface_z_mm)
        clearance = float(surface_model.clearance_mm)
        approach = ScanWaypoint(x=x_origin, y=center_y, z=surface_z + clearance, rx=180.0, ry=0.0, rz=90.0)
        retreat = ScanWaypoint(
            x=x_origin + min(20.0, corridor_length * 0.1),
            y=center_y,
            z=surface_z + clearance + profile.contact_guard_margin_mm,
            rx=180.0,
            ry=0.0,
            rz=90.0,
        )
        point_count = max(2, int(round(corridor_length / max(config.sample_step_mm, 0.1))) + 1)
        strip_spacing_mm = max(1.0, min(config.strip_width_mm, profile.strip_width_mm) - max(config.strip_overlap_mm, profile.strip_overlap_mm))
        offset_origin = center_y - ((segment_count - 1) * strip_spacing_mm / 2.0)
        per_point_duration_ms = max(5, int(round((max(config.sample_step_mm, 0.1) / max(config.scan_speed_mm_s, 0.1)) * 1000)))
        segments: list[ScanSegment] = []
        for seg_id in range(1, segment_count + 1):
            y_base = offset_origin + (seg_id - 1) * strip_spacing_mm
            reverse = seg_id % 2 == 0
            x_values = [x_origin + idx * config.sample_step_mm for idx in range(point_count)]
            if reverse:
                x_values = list(reversed(x_values))
            waypoints = [
                ScanWaypoint(x=round(x, 3), y=round(y_base, 3), z=surface_z, rx=180.0, ry=0.0, rz=90.0)
                for x in x_values
            ]
            segment = ScanSegment(
                segment_id=seg_id,
                waypoints=waypoints,
                target_pressure=config.pressure_target,
                scan_direction="cranial_to_caudal" if reverse else "caudal_to_cranial",
                estimated_duration_ms=point_count * per_point_duration_ms,
                requires_contact_probe=True,
                segment_priority=seg_id,
                quality_target=max(config.image_quality_threshold, 0.75),
                coverage_target=0.95,
            )
            segment.segment_hash = hashlib.sha256(json.dumps(segment.to_dict(), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            segments.append(segment)
        plan = ScanPlan(
            session_id="",
            plan_id=f"PREVIEW_{experiment_id}",
            approach_pose=approach,
            retreat_pose=retreat,
            segments=segments,
            planner_version=self.version,
            registration_hash=localization.registration_hash(),
            plan_kind="preview",
            created_ts_ns=now_ns(),
        )
        plan.validation_summary = self.validator.validate(
            plan,
            expected_axis_count=profile.axis_count,
            corridor_width_mm=corridor_width,
            strip_spacing_mm=strip_spacing_mm,
            localization=localization,
        )
        return plan, {
            "corridor_width_mm": corridor_width,
            "strip_spacing_mm": strip_spacing_mm,
            "corridor_length_mm": corridor_length,
            "surface_tilt_deg": surface_model.local_tilt_deg,
        }
