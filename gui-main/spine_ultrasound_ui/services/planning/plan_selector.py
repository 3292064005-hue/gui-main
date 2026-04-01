from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.models import ScanPlan


@dataclass
class SelectionResult:
    selected: ScanPlan
    selected_score: dict[str, Any]
    candidates: list[dict[str, Any]]


class PlanSelector:
    def choose(self, candidates: list[tuple[ScanPlan, dict[str, Any]]]) -> SelectionResult:
        if not candidates:
            raise ValueError("at least one execution plan candidate is required")
        ranked: list[tuple[float, ScanPlan, dict[str, Any]]] = []
        candidate_payloads: list[dict[str, Any]] = []
        for plan, score in candidates:
            composite = float(score.get("composite_score", 0.0) or 0.0)
            contact_penalty = float(score.get("contact_risk", 0.0) or 0.0) * 0.2
            duration_penalty = max(0.0, (float(score.get("estimated_duration_ms", 0.0) or 0.0) - 160_000.0) / 400_000.0)
            selection_score = round(composite - contact_penalty - duration_penalty, 4)
            enriched = {
                **dict(score),
                "plan_id": plan.plan_id,
                "plan_kind": plan.plan_kind,
                "selection_score": selection_score,
            }
            candidate_payloads.append(enriched)
            ranked.append((selection_score, plan, enriched))
        ranked.sort(key=lambda item: item[0], reverse=True)
        _, selected_plan, selected_score = ranked[0]
        return SelectionResult(selected=selected_plan, selected_score=selected_score, candidates=candidate_payloads)
