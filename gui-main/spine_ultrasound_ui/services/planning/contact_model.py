from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.planning.surface_model import SurfaceModel
from spine_ultrasound_ui.services.planning.types import LocalizationResult


@dataclass
class ContactModel:
    target_force_n: float
    lower_band_n: float
    upper_band_n: float
    probe_depth_mm: float
    probe_spacing_mm: float
    risk_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_force_n": round(self.target_force_n, 4),
            "lower_band_n": round(self.lower_band_n, 4),
            "upper_band_n": round(self.upper_band_n, 4),
            "probe_depth_mm": round(self.probe_depth_mm, 4),
            "probe_spacing_mm": round(self.probe_spacing_mm, 4),
            "risk_score": round(self.risk_score, 4),
        }


class ContactModelBuilder:
    def build(self, localization: LocalizationResult, *, config: RuntimeConfig, surface_model: SurfaceModel) -> ContactModel:
        registration = dict(localization.patient_registration or {})
        stability = dict(registration.get("stability", {}))
        registration_confidence = float(localization.confidence or 0.0)
        tilt_factor = min(1.0, abs(surface_model.local_tilt_deg) / 18.0)
        curvature_factor = min(1.0, max(surface_model.curvature_estimate, 0.0) * 8.0)
        stability_factor = min(1.0, float(stability.get("surface_fit_rmse_mm", 0.8)) / 3.0)
        confidence_penalty = max(0.0, 0.15 - (registration_confidence * 0.1))
        risk_score = min(1.0, 0.12 + tilt_factor * 0.22 + curvature_factor * 0.22 + stability_factor * 0.18 + confidence_penalty)
        band_half_width = max(0.25, min(1.5, 0.45 + risk_score))
        probe_spacing_mm = max(config.sample_step_mm, min(config.sample_step_mm * 4.0, 4.0 + (risk_score * 8.0)))
        probe_depth_mm = max(0.5, min(6.0, 1.0 + surface_model.clearance_mm * 0.18 + risk_score * 1.8))
        return ContactModel(
            target_force_n=float(config.pressure_target),
            lower_band_n=max(0.0, float(config.pressure_target) - band_half_width),
            upper_band_n=float(config.pressure_target) + band_half_width,
            probe_depth_mm=probe_depth_mm,
            probe_spacing_mm=probe_spacing_mm,
            risk_score=risk_score,
        )
