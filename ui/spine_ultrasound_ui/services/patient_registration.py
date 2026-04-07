from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, radians, sin
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile
from spine_ultrasound_ui.utils import now_text


@dataclass
class PatientRegistrationResult:
    """Backward-compatible wrapper for patient registration payloads.

    The canonical registration contract is now the guidance-only V2 payload, but
    some existing callers still expect an object exposing ``to_dict``. This
    wrapper preserves that boundary without hiding the richer contract fields.
    """

    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


def _surface_axes(yaw_deg: float) -> dict[str, list[float]]:
    yaw = radians(yaw_deg)
    scan_axis = [round(cos(yaw), 6), round(sin(yaw), 6), 0.0]
    lr_axis = [round(-sin(yaw), 6), round(cos(yaw), 6), 0.0]
    return {
        "scan_longitudinal": scan_axis,
        "left_right": lr_axis,
        "surface_normal": [0.0, 0.0, -1.0],
    }


def _default_landmarks(origin_x_mm: float, corridor_length_mm: float, roi_center_y: float, surface_z_mm: float) -> list[dict[str, float]]:
    return [
        {"name": "c7_estimate", "x": origin_x_mm, "y": round(roi_center_y - 8.0, 2), "z": surface_z_mm},
        {"name": "thoracic_midline", "x": round(origin_x_mm + corridor_length_mm * 0.45, 2), "y": roi_center_y, "z": surface_z_mm},
        {"name": "thoracolumbar_junction", "x": round(origin_x_mm + corridor_length_mm * 0.7, 2), "y": round(roi_center_y + 2.0, 2), "z": surface_z_mm},
        {"name": "sacrum_estimate", "x": round(origin_x_mm + corridor_length_mm, 2), "y": round(roi_center_y + 8.0, 2), "z": surface_z_mm},
    ]


def build_registration_facts(
    *,
    experiment_id: str,
    roi_center_y: float,
    segment_count: int,
    config: RuntimeConfig,
    source_label: str,
    source_type: str,
    confidence: float,
    observation: dict[str, Any] | None = None,
    camera_device_id: str = "rgbd_back_camera",
) -> dict[str, Any]:
    """Build normalized guidance facts prior to freeze gating.

    Args:
        experiment_id: Experiment identifier used for traceability.
        roi_center_y: Estimated corridor center in millimeters.
        segment_count: Estimated count of usable scan strips.
        config: Runtime configuration influencing corridor size and guidance
            limits.
        source_label: Backward-compatible source label retained for manifest and
            scan-protocol compatibility.
        source_type: Normalized guidance source mode.
        confidence: Seed confidence used to derive quality metrics.
        observation: Optional image-derived guidance observation.
        camera_device_id: Camera identifier bound to the guidance facts.

    Returns:
        A normalized facts dictionary consumed by the guidance runtime.

    Raises:
        ValueError: Raised when the derived segment count is invalid.
    """
    profile = load_xmate_profile()
    obs = dict(observation or {})
    raw_segments = int(obs.get("segment_count", segment_count))
    if raw_segments <= 0:
        raise ValueError("segment_count must be a positive integer")
    usable_segments = raw_segments
    corridor_length_mm = round(usable_segments * float(config.segment_length_mm), 2)
    default_width_mm = round(max(float(profile.strip_width_mm), usable_segments * max(4.0, profile.strip_overlap_mm + 2.0)), 2)
    back_roi = dict(obs.get("back_roi", {}))
    corridor_width_mm = round(float(back_roi.get("height_mm", default_width_mm) or default_width_mm), 2)
    roi_center_y = round(float(obs.get("roi_center_y_mm", roi_center_y)), 2)
    estimated_yaw = round(float(obs.get("surface_yaw_deg", min(10.0, usable_segments * 1.5))), 2)
    provider_mode = str(obs.get("provider_mode", "synthetic"))
    origin_x_mm = 110.0
    surface_z_mm = round(float(obs.get("surface_z_mm", 205.0) or 205.0), 2)
    patient_frame = {
        "name": "patient_spine",
        "origin_mm": {"x": origin_x_mm, "y": roi_center_y, "z": surface_z_mm},
        "axes": _surface_axes(estimated_yaw),
        "reference_camera": camera_device_id,
    }
    scan_corridor = {
        "start_mm": {"x": origin_x_mm, "y": round(roi_center_y - corridor_width_mm / 2.0, 2), "z": surface_z_mm},
        "end_mm": {"x": round(origin_x_mm + corridor_length_mm, 2), "y": round(roi_center_y + corridor_width_mm / 2.0, 2), "z": surface_z_mm},
        "centerline_mm": {"x": round(origin_x_mm + corridor_length_mm / 2.0, 2), "y": roi_center_y, "z": surface_z_mm},
        "length_mm": corridor_length_mm,
        "width_mm": corridor_width_mm,
        "segment_count": usable_segments,
        "strip_width_mm": float(profile.strip_width_mm),
        "strip_overlap_mm": float(profile.strip_overlap_mm),
        "scan_pattern": "serpentine_long_axis",
    }
    landmarks = [dict(item) for item in obs.get("landmarks", _default_landmarks(origin_x_mm, corridor_length_mm, roi_center_y, surface_z_mm))]
    body_surface = dict(obs.get("body_surface", {
        "model": "camera_back_surface_estimator",
        "normal": [0.0, 0.0, -1.0],
        "surface_pitch_deg": 0.0,
        "surface_yaw_deg": estimated_yaw,
        "probe_tilt_limits_deg": dict(profile.surface_tilt_limits_deg),
        "contact_guard_margin_mm": float(profile.contact_guard_margin_mm),
    }))
    midline_points = [
        {"x": landmark["x"], "y": landmark["y"], "z": landmark["z"]}
        for landmark in landmarks
    ]
    midline_polyline = dict(obs.get("midline_polyline", {
        "coordinate_frame": "patient_surface",
        "points_mm": midline_points,
        "confidence": round(max(0.75, min(0.97, confidence)), 3),
    }))
    if not back_roi:
        back_roi = {
            "center_y_mm": roi_center_y,
            "length_mm": corridor_length_mm + 20.0,
            "height_mm": corridor_width_mm + 30.0,
            "confidence": round(max(0.72, min(0.96, confidence)), 3),
        }
    quality_metrics = dict(obs.get("quality_metrics", {}))
    overall_confidence = round(float(obs.get("confidence", confidence) or confidence), 3)
    if not quality_metrics:
        quality_metrics = {
            "overall_confidence": overall_confidence,
            "roi_confidence": float(back_roi.get("confidence", overall_confidence)),
            "midline_confidence": float(midline_polyline.get("confidence", overall_confidence)),
            "surface_fit_rms_mm": 2.4 if source_type != "fallback_simulated" else 3.2,
            "corridor_margin_mm": 8.0 if source_type != "fallback_simulated" else 5.0,
            "landmark_count": len(landmarks),
            "provider_mode": provider_mode,
        }
    camera_observations = {
        "roi_mode": config.roi_mode,
        "roi_center_y_mm": roi_center_y,
        "back_roi_height_mm": float(back_roi.get("height_mm", corridor_width_mm + 30.0) or corridor_width_mm + 30.0),
        "back_roi_length_mm": float(back_roi.get("length_mm", corridor_length_mm + 20.0) or corridor_length_mm + 20.0),
        "midline_confidence": float(midline_polyline.get("confidence", quality_metrics.get("midline_confidence", overall_confidence))),
        "landmark_visibility": {
            "c7": round(max(0.72, min(0.95, overall_confidence - 0.05)), 3),
            "thoracic_midline": round(max(0.76, min(0.96, overall_confidence)), 3),
            "sacrum": round(max(0.7, min(0.94, overall_confidence - 0.07)), 3),
        },
        "camera_model": "rgbd_assisted_guidance",
        "provider_mode": provider_mode,
        "back_roi": back_roi,
        "midline_polyline": midline_polyline,
        "guidance_role": "pre_scan_guidance_only",
    }
    registration_quality = dict(obs.get("registration_quality", {}))
    if not registration_quality:
        registration_quality = {
            "overall_confidence": quality_metrics["overall_confidence"],
            "surface_fit_rms_mm": quality_metrics["surface_fit_rms_mm"],
            "corridor_margin_mm": quality_metrics["corridor_margin_mm"],
            "registration_ready": True,
            "confidence_breakdown": {
                "camera": quality_metrics["overall_confidence"] if source_type != "camera_ultrasound_fusion" else round(quality_metrics["overall_confidence"] * 0.6, 3),
                "ultrasound": round(quality_metrics["overall_confidence"] * 0.4, 3) if source_type == "camera_ultrasound_fusion" else 0.0,
                "hybrid": quality_metrics["overall_confidence"] if source_type == "camera_ultrasound_fusion" else 0.0,
                "fallback": quality_metrics["overall_confidence"] if source_type == "fallback_simulated" else 0.0,
            },
            "quality_metrics": quality_metrics,
            "registration_covariance": {
                "longitudinal_mm2": round(max(0.6, corridor_length_mm / 180.0), 3),
                "lateral_mm2": round(max(0.4, corridor_width_mm / 45.0), 3),
                "normal_mm2": 0.35,
            },
        }
    guidance_targets = dict(obs.get("guidance_targets", {
        "entry_point_mm": dict(scan_corridor["start_mm"]),
        "exit_point_mm": dict(scan_corridor["end_mm"]),
        "centerline_mm": dict(scan_corridor["centerline_mm"]),
        "approach_clearance_mm": float(profile.approach_clearance_mm),
    }))
    notes = list(obs.get("notes", [])) + [
        f"Experiment {experiment_id} uses {source_label} guidance for xMate ER3 spinal sweep.",
        "Camera guidance produces pre-scan patient_frame, body surface, and long-axis corridor before session freeze.",
        "Guidance remains advisory after session freeze and never becomes an RT execution authority.",
    ]
    return {
        "experiment_id": experiment_id,
        "source": source_label,
        "source_type": source_type,
        "generated_at": now_text(),
        "patient_frame": patient_frame,
        "scan_corridor": scan_corridor,
        "landmarks": landmarks,
        "body_surface": body_surface,
        "camera_observations": camera_observations,
        "registration_quality": registration_quality,
        "guidance_targets": guidance_targets,
        "usable_segments": list(obs.get("usable_segments", list(range(1, usable_segments + 1)))),
        "notes": notes,
    }


def build_patient_registration(
    *,
    experiment_id: str,
    roi_center_y: float,
    segment_count: int,
    config: RuntimeConfig,
    source_label: str = "camera_backed_registration",
    source_type: str = "camera_only",
    confidence: float = 0.84,
) -> PatientRegistrationResult:
    """Return a backward-compatible registration wrapper.

    New code should prefer ``GuidanceRuntimeService``. This function remains as
    a compatibility helper for callers that still expect ``to_dict``.
    """
    from spine_ultrasound_ui.services.perception.guidance_runtime_service import GuidanceRuntimeService

    runtime = GuidanceRuntimeService()
    result = runtime.build(
        experiment_id=experiment_id,
        config=config,
        device_roster={
            "robot": {"online": True, "fresh": True},
            "camera": {"online": True, "fresh": True},
            "ultrasound": {"online": True, "fresh": True},
            "pressure": {"online": True, "fresh": True},
        },
        source_type=source_type,
        source_label=source_label,
        roi_center_y=roi_center_y,
        segment_count=segment_count,
        confidence=confidence,
    )
    return PatientRegistrationResult(payload=result.patient_registration)
