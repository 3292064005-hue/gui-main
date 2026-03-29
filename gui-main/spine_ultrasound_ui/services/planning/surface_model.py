from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.services.planning.types import LocalizationResult


@dataclass
class SurfaceModel:
    surface_z_mm: float
    local_tilt_deg: float
    curvature_estimate: float
    clearance_mm: float
    corridor_width_mm: float
    corridor_length_mm: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_z_mm": round(self.surface_z_mm, 3),
            "local_tilt_deg": round(self.local_tilt_deg, 3),
            "curvature_estimate": round(self.curvature_estimate, 4),
            "clearance_mm": round(self.clearance_mm, 3),
            "corridor_width_mm": round(self.corridor_width_mm, 3),
            "corridor_length_mm": round(self.corridor_length_mm, 3),
        }


class SurfaceModelBuilder:
    def build(self, localization: LocalizationResult, *, default_length_mm: float, default_width_mm: float, clearance_mm: float) -> SurfaceModel:
        corridor = dict(localization.patient_registration.get("scan_corridor", {}))
        start_mm = dict(corridor.get("start_mm", {}))
        stability = dict(localization.patient_registration.get("stability", {}))
        return SurfaceModel(
            surface_z_mm=float(start_mm.get("z", 205.0)),
            local_tilt_deg=float(stability.get("surface_tilt_deg", 4.0)),
            curvature_estimate=float(stability.get("surface_fit_rmse_mm", 0.8)) / 100.0,
            clearance_mm=float(clearance_mm),
            corridor_width_mm=float(corridor.get("width_mm", default_width_mm)),
            corridor_length_mm=float(corridor.get("length_mm", default_length_mm)),
        )
