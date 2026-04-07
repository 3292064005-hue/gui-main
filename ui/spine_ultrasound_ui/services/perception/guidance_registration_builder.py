from __future__ import annotations

import hashlib
import json
from typing import Any

from spine_ultrasound_ui.utils import now_text


class GuidanceRegistrationBuilder:
    """Build the canonical guidance-only patient registration contract.

    The builder converts perception facts, calibration lineage, and readiness
    verdicts into the single patient-registration artifact frozen into a
    session. Legacy compatibility fields are preserved so existing planners and
    readers continue to operate without modification.
    """

    def build(
        self,
        *,
        experiment_id: str,
        source_type: str,
        source_label: str,
        patient_frame: dict[str, Any],
        scan_corridor: dict[str, Any],
        landmarks: list[dict[str, Any]],
        body_surface: dict[str, Any],
        camera_observations: dict[str, Any],
        registration_quality: dict[str, Any],
        guidance_targets: dict[str, Any],
        usable_segments: list[int],
        notes: list[str],
        calibration_bundle: dict[str, Any],
        localization_readiness: dict[str, Any],
        source_frame_set: dict[str, Any],
        algorithm_bundle_hash: str,
        manual_adjustment: dict[str, Any],
        processing_step_refs: list[str],
    ) -> dict[str, Any]:
        """Return the canonical patient registration payload.

        Args:
            experiment_id: Experiment identifier used for traceability.
            source_type: Normalized guidance source type.
            source_label: Backward-compatible registration source label.
            patient_frame: Frozen patient frame.
            scan_corridor: Frozen scan corridor.
            landmarks: Ordered guidance landmarks.
            body_surface: Surface model used by the planner.
            camera_observations: Camera-side observations used to produce the
                guidance facts.
            registration_quality: Summary quality metrics.
            guidance_targets: Guidance-only planner targets.
            usable_segments: Segment indexes considered usable.
            notes: Human-readable audit notes.
            calibration_bundle: Frozen calibration bundle.
            localization_readiness: Readiness verdict.
            source_frame_set: Frozen frame set index.
            algorithm_bundle_hash: Stable hash of guidance algorithms.
            manual_adjustment: Frozen manual adjustment artifact.
            processing_step_refs: Ordered guidance processing-step identifiers
                used to build the frozen contract.

        Returns:
            Canonical registration payload with compatibility fields.

        Raises:
            No exceptions are raised. Callers are expected to pass normalized
            data structures.
        """
        payload = {
            "schema_version": "2.0",
            "registration_id": f"reg::{experiment_id}",
            "generated_at": now_text(),
            "status": self._normalize_status(localization_readiness),
            "role": "guidance_only",
            "guidance_mode": "pre_scan_guidance",
            "execution_authority": "planner_after_freeze",
            "source_type": source_type,
            "source": source_label,
            "camera_device_id": str(source_frame_set.get("camera_device_id", "")),
            "camera_frame_refs": list(source_frame_set.get("frame_refs", [])),
            "camera_intrinsics_hash": str(calibration_bundle.get("camera_intrinsics_hash", "")),
            "camera_to_base_hash": str(calibration_bundle.get("camera_to_base_hash", "")),
            "probe_tcp_hash": str(calibration_bundle.get("probe_tcp_hash", "")),
            "temporal_sync_hash": str(calibration_bundle.get("temporal_sync_hash", "")),
            "algorithm_bundle_hash": algorithm_bundle_hash,
            "back_roi": dict(camera_observations.get("back_roi", {})),
            "midline_polyline": dict(camera_observations.get("midline_polyline", {})),
            "landmarks": [dict(item) for item in landmarks],
            "body_surface": dict(body_surface),
            "camera_observations": dict(camera_observations),
            "confidence_breakdown": dict(registration_quality.get("confidence_breakdown", {})),
            "quality_metrics": dict(registration_quality.get("quality_metrics", {})),
            "patient_frame": dict(patient_frame),
            "scan_corridor": dict(scan_corridor),
            "guidance_targets": dict(guidance_targets),
            "usable_segments": list(usable_segments),
            "registration_covariance": dict(registration_quality.get("registration_covariance", {})),
            "manual_adjustments": list(manual_adjustment.get("adjustments", [])),
            "freeze_ready": bool(localization_readiness.get("freeze_gate", {}).get("freeze_ready", False)),
            "blocking_reasons": list(localization_readiness.get("blocking_reasons", [])),
            "warnings": list(localization_readiness.get("warnings", [])),
            "review_approval": dict(localization_readiness.get("review_approval", {})),
            "recommended_action": self._recommended_action(localization_readiness),
            "artifact_refs": [
                "meta/patient_registration.json",
                "meta/localization_readiness.json",
                "meta/calibration_bundle.json",
                "meta/localization_freeze.json",
                "derived/sync/source_frame_set.json",
            ],
            "processing_step_refs": list(processing_step_refs),
            "notes": list(notes),
            "registration_quality": dict(registration_quality),
        }
        payload["registration_hash"] = self._stable_hash(payload)
        return payload

    @staticmethod
    def _normalize_status(localization_readiness: dict[str, Any]) -> str:
        verdict = str(localization_readiness.get("status", "BLOCKED"))
        if verdict == "READY_FOR_FREEZE":
            return "READY"
        if verdict == "READY_WITH_REVIEW":
            return "REVIEW_REQUIRED"
        return "BLOCKED"

    @staticmethod
    def _recommended_action(localization_readiness: dict[str, Any]) -> str:
        verdict = str(localization_readiness.get("status", "BLOCKED"))
        if verdict == "READY_FOR_FREEZE":
            approval = dict(localization_readiness.get("review_approval", {}))
            return "freeze" if not approval.get("approved", False) else "freeze_after_review"
        if verdict == "READY_WITH_REVIEW":
            return "review"
        return "retry_capture"

    @staticmethod
    def _stable_hash(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
