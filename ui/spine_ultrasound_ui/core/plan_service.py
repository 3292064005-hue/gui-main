
from __future__ import annotations

from typing import Any, Iterable

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
    """Run localization strategies against a shared authoritative device snapshot."""

    def __init__(self, strategies: Iterable[object] | None = None) -> None:
        self.strategies = list(strategies or [
            HybridRegistrationStrategy(),
            CameraRegistrationStrategy(),
            UltrasoundRegistrationStrategy(),
            FallbackRegistrationStrategy(),
        ])

    def run(
        self,
        experiment: ExperimentRecord,
        config: RuntimeConfig,
        *,
        device_roster: dict[str, Any] | None = None,
    ) -> LocalizationResult:
        last_result: LocalizationResult | None = None
        failures: list[str] = []
        for strategy in self.strategies:
            try:
                result = strategy.run(experiment, config, device_roster=device_roster)
            except (RuntimeError, ValueError) as exc:
                failures.append(f"{type(strategy).__name__}: {exc}")
                continue
            last_result = result
            if result.status.ready:
                return result
        if last_result is not None:
            if failures:
                detail = f"{last_result.status.detail} 其余策略失败: {'; '.join(failures)}"
                last_result.status.detail = detail
            return last_result
        detail = '; '.join(failures) if failures else 'no localization strategy configured'
        return LocalizationResult(
            status=CapabilityStatus(
                ready=False,
                state='BLOCKED',
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=f'视觉定位失败：{detail}',
            ),
            patient_registration={},
            confidence=0.0,
        )


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

    def run_localization(
        self,
        experiment: ExperimentRecord,
        config: RuntimeConfig,
        *,
        device_roster: dict[str, Any] | None = None,
    ) -> LocalizationResult:
        result = self.localization_pipeline.run(experiment, config, device_roster=device_roster)
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
                state='READY',
                implementation=ImplementationState.IMPLEMENTED.value,
                detail='当前扫查路径由患者配准、表面建模、接触预探、执行候选评估与长轴条带扫查策略联合生成。',
            ),
        )

    def build_execution_plan(self, preview_plan: ScanPlan, *, config: RuntimeConfig) -> ScanPlan:
        """Build the execution plan from a preview plan and canonical localization.

        Args:
            preview_plan: Preview plan selected for execution.
            config: Active runtime configuration.

        Returns:
            Session-bound execution plan.

        Raises:
            RuntimeError: Raised when no canonical localization result has been
                captured for the preview plan.

        Boundary behavior:
            This method no longer synthesizes fallback localization facts.
            Callers must first run localization and preview generation using the
            same canonical localization bundle.
        """
        if self._last_localization is None:
            raise RuntimeError('execution plan requires canonical localization before binding preview plan')
        return self.plan_strategy.build_execution_plan(preview_plan, config=config, localization=self._last_localization)

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
