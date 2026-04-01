from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class ContactControlSnapshot:
    target_force_n: float
    measured_force_n: float
    quality_score: float
    contact_confidence: float
    scan_speed_mm_s: float


@dataclass
class ContactControlDecision:
    normal_adjust_mm: float
    recommended_speed_mm_s: float
    action: str
    rescan_hint: bool
    hold_required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProbeContactController:
    def __init__(self, *, max_normal_adjust_mm: float = 1.2, quality_floor: float = 0.68) -> None:
        self.max_normal_adjust_mm = float(max_normal_adjust_mm)
        self.quality_floor = float(quality_floor)

    def evaluate(self, snapshot: ContactControlSnapshot) -> ContactControlDecision:
        error_n = float(snapshot.target_force_n) - float(snapshot.measured_force_n)
        normal_adjust_mm = max(-self.max_normal_adjust_mm, min(self.max_normal_adjust_mm, error_n * 0.22))
        quality_score = float(snapshot.quality_score)
        contact_confidence = float(snapshot.contact_confidence)
        if contact_confidence < 0.3:
            return ContactControlDecision(
                normal_adjust_mm=max(0.4, normal_adjust_mm),
                recommended_speed_mm_s=max(1.5, snapshot.scan_speed_mm_s * 0.4),
                action="reacquire_contact",
                rescan_hint=True,
                hold_required=False,
            )
        if quality_score < self.quality_floor:
            return ContactControlDecision(
                normal_adjust_mm=normal_adjust_mm,
                recommended_speed_mm_s=max(2.0, snapshot.scan_speed_mm_s * 0.55),
                action="slow_down_for_quality",
                rescan_hint=True,
                hold_required=False,
            )
        if abs(error_n) > max(2.5, snapshot.target_force_n * 0.35):
            return ContactControlDecision(
                normal_adjust_mm=normal_adjust_mm,
                recommended_speed_mm_s=max(2.0, snapshot.scan_speed_mm_s * 0.6),
                action="trim_contact_force",
                rescan_hint=False,
                hold_required=False,
            )
        return ContactControlDecision(
            normal_adjust_mm=normal_adjust_mm,
            recommended_speed_mm_s=float(snapshot.scan_speed_mm_s),
            action="continue_scan",
            rescan_hint=False,
            hold_required=False,
        )
