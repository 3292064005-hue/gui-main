from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.probe_contact_controller import ContactControlSnapshot, ProbeContactController
from spine_ultrasound_ui.services.xmate_profile import XMateProfile
from spine_ultrasound_ui.utils import now_text


def build_scan_protocol(
    *,
    session_id: str,
    plan: ScanPlan,
    config: RuntimeConfig,
    robot_profile: XMateProfile,
    patient_registration: dict[str, Any] | None,
) -> dict[str, Any]:
    corridor = dict((patient_registration or {}).get("scan_corridor", {}))
    body_surface = dict((patient_registration or {}).get("body_surface", {}))
    controller = ProbeContactController()
    contact_decision = controller.evaluate(
        ContactControlSnapshot(
            target_force_n=float(config.pressure_target),
            measured_force_n=float(config.pressure_target),
            quality_score=float(config.image_quality_threshold),
            contact_confidence=0.8,
            scan_speed_mm_s=float(config.scan_speed_mm_s),
        )
    )
    segments = []
    for segment in plan.segments:
        waypoints = [point.to_dict() for point in segment.waypoints]
        segments.append(
            {
                "segment_id": segment.segment_id,
                "scan_direction": segment.scan_direction,
                "target_pressure_n": segment.target_pressure,
                "waypoint_count": len(waypoints),
                "start_pose": waypoints[0] if waypoints else {},
                "end_pose": waypoints[-1] if waypoints else {},
                "segment_length_mm": round(max(0.0, float(config.segment_length_mm)), 2),
                "estimated_duration_ms": int(segment.estimated_duration_ms),
                "requires_contact_probe": bool(segment.requires_contact_probe),
                "quality_target": float(segment.quality_target),
                "coverage_target": float(segment.coverage_target),
                "rescan_allowed": True,
            }
        )
    return {
        "generated_at": now_text(),
        "session_id": session_id,
        "robot_model": robot_profile.robot_model,
        "sdk_robot_class": robot_profile.sdk_robot_class,
        "axis_count": robot_profile.axis_count,
        "rt_loop_hz": robot_profile.rt_loop_hz,
        "preferred_link": robot_profile.preferred_link,
        "single_control_source_required": robot_profile.requires_single_control_source,
        "clinical_control_modes": {
            "approach": "MoveL",
            "seek_contact": "cartesianImpedance",
            "scan": config.rt_mode,
            "retreat": "MoveL",
        },
        "contact_control": {
            "target_force_n": float(config.pressure_target),
            "upper_force_n": float(config.pressure_upper),
            "lower_force_n": float(config.pressure_lower),
            "seek_speed_mm_s": float(config.contact_seek_speed_mm_s),
            "retreat_speed_mm_s": float(config.retreat_speed_mm_s),
            "controller_preview": contact_decision.to_dict(),
            "desired_wrench_n": list(robot_profile.desired_wrench_n),
        },
        "path_policy": {
            "plan_id": plan.plan_id,
            "plan_kind": plan.plan_kind,
            "planner_version": plan.planner_version,
            "registration_hash": plan.registration_hash,
            "validation_summary": dict(plan.validation_summary),
            "segment_count": len(plan.segments),
            "sample_step_mm": float(config.sample_step_mm),
            "segment_length_mm": float(config.segment_length_mm),
            "scan_speed_mm_s": float(config.scan_speed_mm_s),
            "strip_width_mm": float(robot_profile.strip_width_mm),
            "strip_overlap_mm": float(robot_profile.strip_overlap_mm),
            "corridor": corridor,
            "rescan_policy": {"enabled": True, "mode": "low_quality_patch", "quality_threshold": float(config.image_quality_threshold)},
        },
        "registration_contract": {
            "patient_frame": dict((patient_registration or {}).get("patient_frame", {})),
            "camera_source": str((patient_registration or {}).get("source", "")),
            "body_surface": body_surface,
        },
        "rt_parameters": {
            "rt_network_tolerance_percent": int(robot_profile.rt_network_tolerance_percent),
            "joint_filter_hz": float(robot_profile.joint_filter_hz),
            "cart_filter_hz": float(robot_profile.cart_filter_hz),
            "torque_filter_hz": float(robot_profile.torque_filter_hz),
            "cartesian_impedance": list(robot_profile.cartesian_impedance),
            "fc_frame_type": robot_profile.fc_frame_type,
        },
        "segments": segments,
        "patient_frame": dict((patient_registration or {}).get("patient_frame", {})),
        "safety_contract": {
            "hold_on_stale_telemetry": True,
            "controlled_retract_on_force_timeout": True,
            "estop_latch_on_persistent_timeout": True,
            "direct_torque_allowed_in_clinical_mainline": False,
            "surface_tilt_limits_deg": dict(robot_profile.surface_tilt_limits_deg),
        },
    }


def save_scan_protocol(target: Path, payload: dict[str, Any]) -> Path:
    target.write_text(__import__("json").dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target
