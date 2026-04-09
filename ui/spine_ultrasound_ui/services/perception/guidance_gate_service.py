from __future__ import annotations

import hashlib
import json
from typing import Any

from spine_ultrasound_ui.utils import now_text


class GuidanceGateService:
    """Evaluate whether the guidance contract may be frozen into a session.

    The gate keeps camera guidance strictly inside the pre-scan preparation
    boundary. Review-required bundles may only become freeze-ready after an
    explicit review approval is recorded.
    """

    def evaluate(
        self,
        *,
        device_roster: dict[str, Any],
        calibration_bundle: dict[str, Any],
        registration_candidate: dict[str, Any],
        source_frame_set: dict[str, Any],
        source_type: str,
        manual_adjustment: dict[str, Any],
        review_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the structured localization readiness verdict.

        Args:
            device_roster: Current device health facts.
            calibration_bundle: Frozen calibration bundle candidate.
            registration_candidate: Candidate patient guidance contract.
            source_frame_set: Camera evidence index used for guidance.
            source_type: Guidance source mode.
            manual_adjustment: Manual adjustment artifact.
            review_context: Optional review approval context.

        Returns:
            The readiness verdict used by session freeze.
        """

        def _item(name: str) -> dict[str, Any]:
            return dict(device_roster.get(name, {}))

        def _online(name: str) -> bool:
            item = _item(name)
            return bool(item.get("online", item.get("connected", False))) and bool(item.get("fresh", True))

        review_context = dict(review_context or {})
        review_approved = bool(review_context.get("approved", False))
        device_gate = {
            "camera_online": _online("camera"),
            "robot_online": _online("robot"),
            "ultrasound_online": _online("ultrasound"),
            "pressure_online": _online("pressure"),
            "camera_fact_source": str(_item("camera").get("fact_source", "runtime_snapshot")),
            "robot_fact_source": str(_item("robot").get("fact_source", "runtime_snapshot")),
            "ultrasound_fact_source": str(_item("ultrasound").get("fact_source", "runtime_snapshot")),
            "pressure_fact_source": str(_item("pressure").get("fact_source", "runtime_snapshot")),
            "frame_fresh": bool(source_frame_set.get("fresh", False)),
            "frame_count": int(source_frame_set.get("frame_count", 0) or 0),
        }
        calibration_gate = {
            "bundle_release_state": str(calibration_bundle.get("release_state", "draft")),
            "camera_intrinsics_valid": bool(calibration_bundle.get("camera_intrinsics_hash")),
            "camera_to_base_valid": bool(calibration_bundle.get("camera_to_base_hash")),
            "probe_tcp_valid": bool(calibration_bundle.get("probe_tcp_hash")),
            "temporal_sync_valid": bool(calibration_bundle.get("temporal_sync_hash")),
            "temporal_sync_jitter_ms": float(calibration_bundle.get("residual_metrics", {}).get("temporal_sync_jitter_ms", 0.0) or 0.0),
        }
        quality_metrics = dict(registration_candidate.get("quality_metrics", {}))
        perception_gate = {
            "roi_confidence": float(quality_metrics.get("roi_confidence", 0.0) or 0.0),
            "midline_confidence": float(quality_metrics.get("midline_confidence", 0.0) or 0.0),
            "surface_fit_rms_mm": float(quality_metrics.get("surface_fit_rms_mm", 0.0) or 0.0),
            "landmark_count": int(quality_metrics.get("landmark_count", 0) or 0),
            "corridor_margin_mm": float(quality_metrics.get("corridor_margin_mm", 0.0) or 0.0),
        }
        guidance_gate = {
            "guidance_mode": "guidance_only",
            "source_type": source_type,
            "registration_candidate_hash": str(registration_candidate.get("candidate_hash", "")),
            "manual_adjustment_count": int(manual_adjustment.get("adjustment_count", 0) or 0),
            "registration_covariance_ok": bool(registration_candidate.get("registration_covariance", {})),
            "review_approved": review_approved,
        }
        blocking_reasons: list[str] = []
        warnings: list[str] = []
        if not device_gate["camera_online"]:
            blocking_reasons.append("camera_offline")
        if not device_gate["robot_online"]:
            blocking_reasons.append("robot_offline")
        if not device_gate["frame_fresh"]:
            blocking_reasons.append("guidance_frames_stale")
        if device_gate["frame_count"] < 1:
            blocking_reasons.append("guidance_frames_missing")
        if calibration_gate["bundle_release_state"] != "approved":
            blocking_reasons.append("calibration_bundle_not_approved")
        if not calibration_gate["camera_intrinsics_valid"]:
            blocking_reasons.append("camera_intrinsics_missing")
        if not calibration_gate["camera_to_base_valid"]:
            blocking_reasons.append("camera_to_base_missing")
        if not calibration_gate["probe_tcp_valid"]:
            blocking_reasons.append("probe_tcp_missing")
        if not calibration_gate["temporal_sync_valid"]:
            blocking_reasons.append("temporal_sync_missing")
        if calibration_gate["temporal_sync_jitter_ms"] > 10.0:
            blocking_reasons.append("temporal_sync_jitter_exceeds_threshold")
        if perception_gate["roi_confidence"] < 0.7:
            blocking_reasons.append("roi_confidence_below_threshold")
        if perception_gate["midline_confidence"] < 0.75:
            blocking_reasons.append("midline_confidence_below_threshold")
        if perception_gate["surface_fit_rms_mm"] > 3.5:
            blocking_reasons.append("surface_fit_rms_exceeds_threshold")
        if perception_gate["landmark_count"] < 3:
            blocking_reasons.append("insufficient_landmarks")
        if perception_gate["corridor_margin_mm"] < 5.0:
            blocking_reasons.append("corridor_margin_below_threshold")
        if source_type == "fallback_simulated" and not review_approved:
            warnings.append("fallback_guidance_requires_review")
        if guidance_gate["manual_adjustment_count"] > 0 and not review_approved:
            warnings.append("manual_adjustment_present")
        review_required = bool(warnings)
        status = "BLOCKED" if blocking_reasons else ("READY_WITH_REVIEW" if review_required else "READY_FOR_FREEZE")
        freeze_gate = {
            "freeze_ready": status == "READY_FOR_FREEZE",
            "review_required": review_required,
            "review_approved": review_approved,
            "stale_artifacts": False,
            "source_frame_set_hash": str(source_frame_set.get("source_frame_set_hash", "")),
            "algorithm_bundle_hash": str(registration_candidate.get("algorithm_bundle_hash", "")),
        }
        payload = {
            "schema_version": "1.0",
            "generated_at": now_text(),
            "status": status,
            "device_gate": device_gate,
            "calibration_gate": calibration_gate,
            "perception_gate": perception_gate,
            "guidance_gate": guidance_gate,
            "freeze_gate": freeze_gate,
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
            "summary_metrics": {
                "overall_confidence": float(quality_metrics.get("overall_confidence", 0.0) or 0.0),
                "usable_segment_count": int(registration_candidate.get("usable_segment_count", 0) or 0),
                "frame_count": device_gate["frame_count"],
            },
            "review_required": review_required,
            "review_approval": {
                "approved": review_approved,
                "operator_id": str(review_context.get("operator_id", "")),
                "reason": str(review_context.get("reason", "")),
            },
        }
        payload["readiness_hash"] = self._stable_hash(payload)
        return payload

    @staticmethod
    def _stable_hash(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
