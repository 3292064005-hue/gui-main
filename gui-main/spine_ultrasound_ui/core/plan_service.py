from __future__ import annotations

from typing import Iterable

from spine_ultrasound_ui.models import CapabilityStatus, ExperimentRecord, ImplementationState, RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.localization_strategies import (
    CameraRegistrationStrategy,
    FallbackRegistrationStrategy,
    HybridRegistrationStrategy,
    UltrasoundRegistrationStrategy,
)
from spine_ultrasound_ui.services.planning import LocalizationResult, PlanValidator, PlanningGraph


class SimulatedLocalizationStrategy(HybridRegistrationStrategy):
    """Backward-compatible alias for the stronger hybrid pipeline."""


class LocalizationPipeline:
    def __init__(self, strategies: Iterable[object] | None = None) -> None:
        self.strategies = list(strategies or [HybridRegistrationStrategy(), CameraRegistrationStrategy(), UltrasoundRegistrationStrategy(), FallbackRegistrationStrategy()])

    def run(self, experiment: ExperimentRecord, config: RuntimeConfig) -> LocalizationResult:
        last_result: LocalizationResult | None = None
        for strategy in self.strategies:
            result = strategy.run(experiment, config)
            last_result = result
            if result.status.ready:
                return result
        if last_result is None:
            raise RuntimeError("no localization strategy configured")
        return last_result


class DeterministicPlanStrategy:
    version = PlanningGraph.version

    def __init__(self, validator: PlanValidator | None = None) -> None:
        self.graph = PlanningGraph(validator)

    def build_preview_plan(self, experiment: ExperimentRecord, localization: LocalizationResult, config: RuntimeConfig) -> ScanPlan:
        return self.graph.build_preview_plan(experiment, localization, config)

    def build_execution_plan(self, preview_plan: ScanPlan, *, config: RuntimeConfig, localization: LocalizationResult) -> ScanPlan:
        return self.graph.build_execution_plan(preview_plan, config=config, localization=localization)

    def build_rescan_patch_plan(
        self,
        base_plan: ScanPlan,
        low_quality_segments: list[int],
        *,
        quality_target: float,
        low_quality_windows: list[dict[str, int]] | None = None,
        hotspot_windows: list[dict[str, int]] | None = None,
    ) -> ScanPlan:
        return self.graph.build_rescan_patch_plan(
            base_plan,
            low_quality_segments,
            quality_target=quality_target,
            low_quality_windows=low_quality_windows,
            hotspot_windows=hotspot_windows,
        )

    def validate(self, plan: ScanPlan, **kwargs):
        return self.graph.validate(plan, **kwargs)


class PlanService:
    def __init__(
        self,
        localization_strategy: SimulatedLocalizationStrategy | None = None,
        plan_strategy: DeterministicPlanStrategy | None = None,
    ) -> None:
        self.localization_pipeline = LocalizationPipeline([localization_strategy] if localization_strategy is not None else None)
        self.plan_strategy = plan_strategy or DeterministicPlanStrategy()
        self._last_localization: LocalizationResult | None = None

    def run_localization(self, experiment: ExperimentRecord, config: RuntimeConfig) -> LocalizationResult:
        result = self.localization_pipeline.run(experiment, config)
        self._last_localization = result
        return result

    def build_preview_plan(
        self,
        experiment: ExperimentRecord,
        localization: LocalizationResult,
        config: RuntimeConfig,
    ) -> tuple[ScanPlan, CapabilityStatus]:
        self._last_localization = localization
        plan = self.plan_strategy.build_preview_plan(experiment, localization, config)
        return (
            plan,
            CapabilityStatus(
                ready=True,
                state="READY",
                implementation=ImplementationState.IMPLEMENTED.value,
                detail="当前扫查路径由患者配准、表面建模、接触预探、执行候选评估与长轴条带扫查策略联合生成。",
            ),
        )

    def build_execution_plan(self, preview_plan: ScanPlan, *, config: RuntimeConfig) -> ScanPlan:
        localization = self._last_localization or LocalizationResult(
            status=CapabilityStatus(ready=True, state="READY", implementation=ImplementationState.IMPLEMENTED.value, detail="execution fallback"),
            roi_center_y=0.0,
            segment_count=len(preview_plan.segments),
            patient_registration={"scan_corridor": {}},
            confidence=0.75,
        )
        return self.plan_strategy.build_execution_plan(preview_plan, config=config, localization=localization)

    def build_rescan_patch_plan(
        self,
        *,
        base_plan: ScanPlan,
        low_quality_segments: list[int],
        quality_target: float,
        low_quality_windows: list[dict[str, int]] | None = None,
        hotspot_windows: list[dict[str, int]] | None = None,
    ) -> ScanPlan:
        return self.plan_strategy.build_rescan_patch_plan(
            base_plan,
            low_quality_segments,
            quality_target=quality_target,
            low_quality_windows=low_quality_windows,
            hotspot_windows=hotspot_windows,
        )
