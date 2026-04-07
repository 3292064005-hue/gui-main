from __future__ import annotations

from dataclasses import dataclass

from spine_ultrasound_ui.models import CapabilityStatus, ExperimentRecord, ImplementationState, RuntimeConfig, ScanPlan
from .contact_model import ContactModelBuilder
from .execution_planner import ExecutionPlanner
from .plan_scorer import PlanScorer
from .plan_selector import PlanSelector
from .plan_validator import PlanValidator
from .preview_planner import PreviewPlanner
from .rescan_patch_planner import RescanPatchPlanner
from .surface_model import SurfaceModelBuilder
from .types import LocalizationResult, hash_payload


@dataclass
class PlanningContext:
    localization: LocalizationResult
    surface_model: dict
    contact_model: dict


@dataclass
class ExecutionSelectionBundle:
    selected: ScanPlan
    candidates: list[dict]
    selected_score: dict
    planner_context: dict


class PlanningGraph:
    version = "deterministic_preview_planner_v5"

    def __init__(self, validator: PlanValidator | None = None) -> None:
        self.validator = validator or PlanValidator()
        self.preview_planner = PreviewPlanner(self.validator)
        self.execution_planner = ExecutionPlanner(self.validator)
        self.rescan_patch_planner = RescanPatchPlanner(self.validator)
        self.scorer = PlanScorer()
        self.selector = PlanSelector()
        self.surface_builder = SurfaceModelBuilder()
        self.contact_builder = ContactModelBuilder()

    def context_for(self, *, localization: LocalizationResult, config: RuntimeConfig) -> PlanningContext:
        surface_model = self.surface_builder.build(
            localization,
            default_length_mm=config.segment_length_mm * max(1, localization.segment_count),
            default_width_mm=max(config.strip_width_mm, localization.segment_count * 4.0),
            clearance_mm=max(4.0, config.sample_step_mm * 3.0),
        )
        contact_model = self.contact_builder.build(localization, config=config, surface_model=surface_model)
        return PlanningContext(
            localization=localization,
            surface_model=surface_model.to_dict(),
            contact_model=contact_model.to_dict(),
        )

    def build_preview_plan(self, experiment: ExperimentRecord, localization: LocalizationResult, config: RuntimeConfig) -> ScanPlan:
        context = self.context_for(localization=localization, config=config)
        plan, planner_context = self.preview_planner.build(experiment_id=experiment.exp_id, localization=localization, config=config)
        plan.surface_model_hash = hash_payload(context.surface_model)
        score = self.scorer.score(plan, config=config, localization=localization)
        plan.score_summary = score
        plan.validation_summary = {
            **dict(plan.validation_summary),
            "planner_context": planner_context,
            "surface_model": context.surface_model,
            "contact_model": context.contact_model,
            "score": score,
        }
        return plan

    def select_execution_plan(
        self,
        preview_plan: ScanPlan,
        *,
        config: RuntimeConfig,
        localization: LocalizationResult,
    ) -> ExecutionSelectionBundle:
        context = self.context_for(localization=localization, config=config)
        contact_model = self.contact_builder.build(
            localization,
            config=config,
            surface_model=self.surface_builder.build(
                localization,
                default_length_mm=config.segment_length_mm * max(1, localization.segment_count),
                default_width_mm=max(config.strip_width_mm, localization.segment_count * 4.0),
                clearance_mm=max(4.0, config.sample_step_mm * 3.0),
            ),
        )
        candidates: list[tuple[ScanPlan, dict]] = []
        for candidate in self.execution_planner.build_candidates(preview_plan, config=config, contact_model=contact_model):
            score = self.scorer.score(candidate, config=config, localization=localization)
            candidate.score_summary = score
            candidates.append((candidate, score))
        selection = self.selector.choose(candidates)
        selected = selection.selected
        selected.score_summary = dict(selection.selected_score)
        ranked_candidates = list(selection.candidates)
        planner_context = {
            "surface_model": context.surface_model,
            "contact_model": context.contact_model,
            "execution_candidates": ranked_candidates,
            "selection_rationale": {
                "selected_candidate_id": str(selected.plan_id),
                "selected_plan_id": selected.plan_id,
                "selected_profile": selected.validation_summary.get("execution_profile", "standard"),
                "selected_score": dict(selection.selected_score),
                "ranking_snapshot": ranked_candidates,
                "selection_basis": {
                    "best_rank": 1,
                    "candidate_count": len(ranked_candidates),
                    "surface_model_hash": hash_payload(context.surface_model),
                    "contact_model_hash": hash_payload(context.contact_model),
                },
                "tradeoff_summary": {
                    "preferred_for": "lowest_execution_risk", 
                    "rejected_candidate_reasons": [
                        "higher_contact_risk" if idx else "selected" for idx, _ in enumerate(ranked_candidates)
                    ],
                },
                "rejected_candidate_reasons": [
                    "higher_contact_risk" for _ in ranked_candidates[1:]
                ],
            },
        }
        selected.validation_summary = {
            **dict(selected.validation_summary),
            "score": dict(selection.selected_score),
            **planner_context,
        }
        return ExecutionSelectionBundle(
            selected=selected,
            candidates=list(selection.candidates),
            selected_score=dict(selection.selected_score),
            planner_context=planner_context,
        )

    def build_execution_plan(
        self,
        preview_plan: ScanPlan,
        *,
        config: RuntimeConfig,
        localization: LocalizationResult,
    ) -> ScanPlan:
        return self.select_execution_plan(preview_plan, config=config, localization=localization).selected

    def build_rescan_patch_plan(
        self,
        base_plan: ScanPlan,
        low_quality_segments: list[int],
        *,
        quality_target: float,
        low_quality_windows: list[dict[str, int]] | None = None,
        hotspot_windows: list[dict[str, int]] | None = None,
    ) -> ScanPlan:
        patch = self.rescan_patch_planner.build(
            base_plan,
            low_quality_segments,
            quality_target=quality_target,
            low_quality_windows=low_quality_windows,
            hotspot_windows=hotspot_windows,
        )
        score = self.scorer.score(patch, config=RuntimeConfig(image_quality_threshold=quality_target))
        patch.score_summary = score
        patch.validation_summary = {
            **dict(patch.validation_summary),
            "score": score,
        }
        return patch

    def validate(self, plan: ScanPlan, **kwargs):
        return self.validator.validate(plan, **kwargs)
