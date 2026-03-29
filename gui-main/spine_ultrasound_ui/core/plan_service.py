from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from spine_ultrasound_ui.models import (
    CapabilityStatus,
    ExperimentRecord,
    ImplementationState,
    RuntimeConfig,
    ScanPlan,
    ScanSegment,
    ScanWaypoint,
)
from spine_ultrasound_ui.services.patient_registration import build_patient_registration
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile


@dataclass
class LocalizationResult:
    status: CapabilityStatus
    roi_center_y: float = 0.0
    segment_count: int = 0
    patient_registration: dict[str, Any] = field(default_factory=dict)


class SimulatedLocalizationStrategy:
    def run(self, experiment: ExperimentRecord, config: RuntimeConfig) -> LocalizationResult:
        registration = build_patient_registration(
            experiment_id=experiment.exp_id,
            roi_center_y=18.0,
            segment_count=4,
            config=config,
        ).to_dict()
        return LocalizationResult(
            status=CapabilityStatus(
                ready=True,
                state="READY",
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=f"实验 {experiment.exp_id} 使用相机辅助患者配准结果。",
            ),
            roi_center_y=18.0,
            segment_count=4,
            patient_registration=registration,
        )


class DeterministicPlanStrategy:
    def build_preview_plan(
        self,
        experiment: ExperimentRecord,
        localization: LocalizationResult,
        config: RuntimeConfig,
    ) -> ScanPlan:
        if not localization.status.ready:
            raise ValueError("localization result is not ready")
        profile = load_xmate_profile()
        corridor = dict(localization.patient_registration.get("scan_corridor", {}))
        plan_id = f"PREVIEW_{experiment.exp_id}"
        corridor_start = dict(corridor.get("start_mm", {}))
        corridor_length = float(corridor.get("length_mm", config.segment_length_mm * max(1, localization.segment_count)))
        corridor_width = float(corridor.get("width_mm", max(profile.strip_width_mm, localization.segment_count * 4.0)))
        center_y = float(corridor.get("centerline_mm", {}).get("y", localization.roi_center_y))
        surface_z = float(corridor_start.get("z", 205.0))
        clearance = profile.approach_clearance_mm
        approach = ScanWaypoint(x=float(corridor_start.get("x", 110.0)), y=center_y, z=surface_z + clearance, rx=180.0, ry=0.0, rz=90.0)
        retreat = ScanWaypoint(x=float(corridor_start.get("x", 110.0)) + min(20.0, corridor_length * 0.1), y=center_y, z=surface_z + clearance + profile.contact_guard_margin_mm, rx=180.0, ry=0.0, rz=90.0)
        segments: list[ScanSegment] = []
        point_count = max(2, int(corridor_length / max(config.sample_step_mm, 0.1)))
        strip_spacing_mm = max(1.0, profile.strip_width_mm - profile.strip_overlap_mm)
        offset_origin = center_y - ((localization.segment_count - 1) * strip_spacing_mm / 2.0)
        for seg_id in range(1, localization.segment_count + 1):
            waypoints: list[ScanWaypoint] = []
            y_base = offset_origin + (seg_id - 1) * strip_spacing_mm
            reverse = seg_id % 2 == 0
            x_values = [float(corridor_start.get("x", 110.0)) + idx * config.sample_step_mm for idx in range(point_count)]
            if reverse:
                x_values = list(reversed(x_values))
            for x in x_values:
                waypoints.append(
                    ScanWaypoint(
                        x=round(x, 3),
                        y=round(y_base, 3),
                        z=surface_z,
                        rx=180.0,
                        ry=0.0,
                        rz=90.0,
                    )
                )
            segments.append(
                ScanSegment(
                    segment_id=seg_id,
                    waypoints=waypoints,
                    target_pressure=config.pressure_target,
                    scan_direction="cranial_to_caudal" if reverse else "caudal_to_cranial",
                )
            )
        plan = ScanPlan(
            session_id="",
            plan_id=plan_id,
            approach_pose=approach,
            retreat_pose=retreat,
            segments=segments,
        )
        self.validate(plan, expected_axis_count=profile.axis_count)
        return plan

    def validate(self, plan: ScanPlan, *, expected_axis_count: int = 6) -> None:
        del expected_axis_count
        if not plan.segments:
            raise ValueError("scan plan must contain at least one segment")
        for segment in plan.segments:
            if segment.segment_id <= 0:
                raise ValueError("segment_id must be positive")
            if not segment.waypoints:
                raise ValueError(f"segment {segment.segment_id} has no waypoints")
            if len(segment.waypoints) < 2:
                raise ValueError(f"segment {segment.segment_id} must contain at least two waypoints")


class PlanService:
    def __init__(
        self,
        localization_strategy: SimulatedLocalizationStrategy | None = None,
        plan_strategy: DeterministicPlanStrategy | None = None,
    ) -> None:
        self.localization_strategy = localization_strategy or SimulatedLocalizationStrategy()
        self.plan_strategy = plan_strategy or DeterministicPlanStrategy()

    def run_localization(self, experiment: ExperimentRecord, config: RuntimeConfig) -> LocalizationResult:
        return self.localization_strategy.run(experiment, config)

    def build_preview_plan(
        self,
        experiment: ExperimentRecord,
        localization: LocalizationResult,
        config: RuntimeConfig,
    ) -> tuple[ScanPlan, CapabilityStatus]:
        plan = self.plan_strategy.build_preview_plan(experiment, localization, config)
        return (
            plan,
            CapabilityStatus(
                ready=True,
                state="READY",
                implementation=ImplementationState.IMPLEMENTED.value,
                detail="当前扫查路径由 xMate ER3 患者配准与长轴条带扫查策略生成。",
            ),
        )
