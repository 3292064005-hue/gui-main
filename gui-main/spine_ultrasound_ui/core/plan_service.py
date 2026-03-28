from __future__ import annotations

from dataclasses import dataclass

from spine_ultrasound_ui.models import (
    CapabilityStatus,
    ExperimentRecord,
    ImplementationState,
    RuntimeConfig,
    ScanPlan,
    ScanSegment,
    ScanWaypoint,
)


@dataclass
class LocalizationResult:
    status: CapabilityStatus
    roi_center_y: float = 0.0
    segment_count: int = 0


class SimulatedLocalizationStrategy:
    def run(self, experiment: ExperimentRecord, config: RuntimeConfig) -> LocalizationResult:
        del config
        return LocalizationResult(
            status=CapabilityStatus(
                ready=True,
                state="READY",
                implementation=ImplementationState.SIMULATED.value,
                detail=f"实验 {experiment.exp_id} 使用模拟视觉定位结果。",
            ),
            roi_center_y=18.0,
            segment_count=4,
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
        plan_id = f"PREVIEW_{experiment.exp_id}"
        approach = ScanWaypoint(x=118.0, y=12.0, z=224.0, rx=180.0, ry=0.0, rz=90.0)
        retreat = ScanWaypoint(x=118.0, y=12.0, z=238.0, rx=180.0, ry=0.0, rz=90.0)
        segments: list[ScanSegment] = []
        for seg_id in range(1, localization.segment_count + 1):
            waypoints: list[ScanWaypoint] = []
            y_base = localization.roi_center_y + seg_id * 4.0
            point_count = max(2, int(config.segment_length_mm / max(config.sample_step_mm, 0.1)))
            for idx in range(point_count):
                waypoints.append(
                    ScanWaypoint(
                        x=110.0 + idx * config.sample_step_mm,
                        y=y_base,
                        z=205.0,
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
                    scan_direction="caudal_to_cranial" if seg_id % 2 else "cranial_to_caudal",
                )
            )
        plan = ScanPlan(
            session_id="",
            plan_id=plan_id,
            approach_pose=approach,
            retreat_pose=retreat,
            segments=segments,
        )
        self.validate(plan)
        return plan

    def validate(self, plan: ScanPlan) -> None:
        if not plan.segments:
            raise ValueError("scan plan must contain at least one segment")
        for segment in plan.segments:
            if segment.segment_id <= 0:
                raise ValueError("segment_id must be positive")
            if not segment.waypoints:
                raise ValueError(f"segment {segment.segment_id} has no waypoints")


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
                implementation=ImplementationState.SIMULATED.value,
                detail="当前扫查路径由确定性预览策略生成。",
            ),
        )
