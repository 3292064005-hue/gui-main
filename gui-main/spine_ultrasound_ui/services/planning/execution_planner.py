from __future__ import annotations

from spine_ultrasound_ui.models import ExecutionConstraints, RuntimeConfig, ScanPlan, ScanSegment
from spine_ultrasound_ui.services.planning.contact_model import ContactModel
from spine_ultrasound_ui.services.planning.plan_validator import PlanValidator
from spine_ultrasound_ui.utils import now_ns


class ExecutionPlanner:
    version = "execution_planner_v2"

    def __init__(self, validator: PlanValidator | None = None) -> None:
        self.validator = validator or PlanValidator()

    def build(self, preview_plan: ScanPlan, *, config: RuntimeConfig, contact_model: ContactModel, profile: str = "standard") -> ScanPlan:
        segments: list[ScanSegment] = []
        duration_factor = 1.0 if profile == "standard" else 1.15
        quality_floor = config.image_quality_threshold if profile == "standard" else max(config.image_quality_threshold, 0.86)
        for segment in preview_plan.segments:
            execution_segment = ScanSegment.from_dict(segment.to_dict())
            execution_segment.requires_contact_probe = True
            execution_segment.quality_target = max(segment.quality_target, quality_floor)
            execution_segment.contact_band = {
                "lower_n": contact_model.lower_band_n,
                "upper_n": contact_model.upper_band_n,
                "target_n": contact_model.target_force_n,
            }
            execution_segment.transition_policy = "conservative" if profile == "conservative" else "serpentine"
            execution_segment.estimated_duration_ms = max(1, int(round(execution_segment.estimated_duration_ms * duration_factor)))
            segments.append(execution_segment)
        plan = ScanPlan(
            session_id=preview_plan.session_id,
            plan_id=preview_plan.plan_id.replace("PREVIEW", f"EXECUTION_{profile.upper()}"),
            approach_pose=preview_plan.approach_pose,
            retreat_pose=preview_plan.retreat_pose,
            segments=segments,
            planner_version=self.version,
            registration_hash=preview_plan.registration_hash,
            plan_kind="execution",
            created_ts_ns=now_ns(),
            surface_model_hash=preview_plan.surface_model_hash,
            execution_constraints=ExecutionConstraints(
                max_segment_duration_ms=max((segment.estimated_duration_ms for segment in segments), default=0),
                allowed_contact_band={"lower_n": contact_model.lower_band_n, "upper_n": contact_model.upper_band_n},
                transition_smoothing="conservative" if profile == "conservative" else "standard",
                recovery_checkpoint_policy="segment_boundary" if profile == "standard" else "per_probe_window",
                probe_spacing_mm=contact_model.probe_spacing_mm,
                probe_depth_mm=contact_model.probe_depth_mm,
            ),
        )
        plan.validation_summary = self.validator.validate(plan)
        plan.validation_summary["execution_profile"] = profile
        return plan

    def build_candidates(self, preview_plan: ScanPlan, *, config: RuntimeConfig, contact_model: ContactModel) -> list[ScanPlan]:
        return [
            self.build(preview_plan, config=config, contact_model=contact_model, profile="standard"),
            self.build(preview_plan, config=config, contact_model=contact_model, profile="conservative"),
        ]
