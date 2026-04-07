from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text


class FrameSyncIndexer:
    """Build a synchronized ultrasound/camera/contact/robot evidence index.

    The indexer aligns each recorded ultrasound frame against the nearest camera,
    quality, pressure, contact, progress, and robot-state samples. The previous
    implementation only surfaced scan progress and contact metrics. This version
    also freezes whether a frame has a measured robot pose, whether the pose is
    temporally aligned, and whether the calibration/patient-frame chain needed
    for reconstruction is present.
    """

    def __init__(self, *, default_alignment_threshold_ms: int = 250) -> None:
        self.default_alignment_threshold_ms = int(default_alignment_threshold_ms)

    def build(self, session_dir: Path) -> dict[str, Any]:
        """Build the authoritative frame-sync index for a locked session.

        Args:
            session_dir: Locked session directory containing raw evidence.

        Returns:
            JSON-serializable frame-sync payload containing per-frame aligned
            metadata and a summary section.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` does not exist.

        Boundary behaviour:
            Missing optional streams do not abort the build. The returned rows
            simply mark the corresponding data as unavailable and add explicit
            manual-review reasons for downstream reconstruction.
        """
        if not session_dir.exists():
            raise FileNotFoundError(session_dir)

        camera_entries = self._read_jsonl(session_dir / "raw" / "camera" / "index.jsonl")
        ultrasound_entries = self._read_jsonl(session_dir / "raw" / "ultrasound" / "index.jsonl")
        quality_entries = self._read_jsonl(session_dir / "raw" / "ui" / "quality_feedback.jsonl")
        pressure_entries = self._read_jsonl(session_dir / "raw" / "pressure" / "samples.jsonl")
        contact_entries = self._read_jsonl(session_dir / "raw" / "core" / "contact_state.jsonl")
        progress_entries = self._read_jsonl(session_dir / "raw" / "core" / "scan_progress.jsonl")
        robot_entries = self._read_jsonl(session_dir / "raw" / "core" / "robot_state.jsonl")
        annotations = self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
        manifest = self._read_json(session_dir / "meta" / "manifest.json")
        patient_registration = self._read_json(session_dir / "meta" / "patient_registration.json")
        calibration_bundle = self._read_json(session_dir / "meta" / "calibration_bundle.json")

        alignment_threshold_ms = int(
            manifest.get("safety_thresholds", {}).get("stale_telemetry_ms", self.default_alignment_threshold_ms)
            or self.default_alignment_threshold_ms
        )
        calibration_valid = bool(calibration_bundle.get("bundle_hash"))
        patient_frame_valid = bool(dict(patient_registration.get("patient_frame", {})).get("origin_mm"))

        rows: list[dict[str, Any]] = []
        pose_valid_count = 0
        sync_valid_count = 0
        reconstructable_count = 0

        for index, us_entry in enumerate(ultrasound_entries, start=1):
            us_ts = int(us_entry.get("source_ts_ns", 0) or us_entry.get("monotonic_ns", 0))
            quality = self._nearest(quality_entries, us_ts)
            camera = self._nearest(camera_entries, us_ts)
            pressure = self._nearest(pressure_entries, us_ts)
            contact = self._nearest(contact_entries, us_ts)
            progress = self._nearest(progress_entries, us_ts)
            robot = self._nearest(robot_entries, us_ts)
            matching_annotations = [
                dict(item.get("data", {}))
                for item in annotations
                if abs(int(item.get("source_ts_ns", 0) or item.get("monotonic_ns", 0)) - us_ts) <= 250_000_000
            ][:6]

            robot_pose = self._extract_robot_pose(robot)
            robot_state_ts_ns = int(robot.get("source_ts_ns", 0) or robot.get("monotonic_ns", 0)) if robot else 0
            temporal_alignment_ms = 0.0 if robot_state_ts_ns <= 0 else round(abs(us_ts - robot_state_ts_ns) / 1_000_000.0, 3)
            pose_valid = bool(robot_pose.get("valid", False))
            sync_valid = bool(pose_valid and temporal_alignment_ms <= alignment_threshold_ms)
            manual_review_reasons: list[str] = []
            if not pose_valid:
                manual_review_reasons.append("missing_robot_pose")
            if pose_valid and not sync_valid:
                manual_review_reasons.append("robot_pose_out_of_sync")
            if not calibration_valid:
                manual_review_reasons.append("missing_calibration_bundle")
            if not patient_frame_valid:
                manual_review_reasons.append("missing_patient_frame")

            data = dict(us_entry.get("data", {}))
            row = {
                "frame_id": str(data.get("frame_id") or f"frame_{index:06d}"),
                "frame_seq": int(us_entry.get("seq", index) or index),
                "ts_ns": us_ts,
                "ultrasound_frame_path": str(data.get("frame_path", "") or ""),
                "ultrasound_frame_meta": {
                    key: value for key, value in data.items() if key not in {"frame_path", "kind", "frame_id"}
                },
                "camera_frame_path": str((camera or {}).get("data", {}).get("frame_path", "") or ""),
                "quality_score": float((quality or {}).get("data", {}).get("quality_score", 0.0) or 0.0),
                "contact_confidence": float((contact or {}).get("data", {}).get("confidence", 0.0)) if contact else float((pressure or {}).get("data", {}).get("contact_confidence", 0.0) or 0.0),
                "pressure_current": float((pressure or {}).get("data", {}).get("pressure_current", 0.0)) if pressure else float((contact or {}).get("data", {}).get("pressure_current", 0.0) or 0.0),
                "recommended_action": str((contact or {}).get("data", {}).get("recommended_action", "")) if contact else str((pressure or {}).get("data", {}).get("recommended_action", "") or ""),
                "wrench_n": [float(value) for value in list((pressure or {}).get("data", {}).get("wrench_n", []))],
                "segment_id": int((progress or {}).get("data", {}).get("active_segment", 0) or 0),
                "progress_pct": float((progress or {}).get("data", {}).get("progress_pct", (progress or {}).get("data", {}).get("overall_progress", 0.0)) or 0.0),
                "annotation_refs": matching_annotations,
                "robot_state_ts_ns": robot_state_ts_ns,
                "robot_pose": dict(robot_pose.get("pose", {})),
                "robot_pose_matrix": [
                    [float(cell) for cell in row_values]
                    for row_values in list(robot_pose.get("matrix", []))
                ] if robot_pose.get("matrix") else [],
                "robot_pose_source": str(robot_pose.get("source", "missing")),
                "robot_joint_pos": [float(value) for value in list((robot or {}).get("data", {}).get("joint_pos", []))],
                "robot_joint_torque": [float(value) for value in list((robot or {}).get("data", {}).get("joint_torque", []))],
                "pose_valid": pose_valid,
                "sync_valid": sync_valid,
                "temporal_alignment_ms": temporal_alignment_ms,
                "calibration_valid": calibration_valid,
                "patient_frame_valid": patient_frame_valid,
                "reconstructable": bool(pose_valid and sync_valid and calibration_valid and patient_frame_valid and str(data.get("frame_path", ""))),
                "manual_review_reasons": manual_review_reasons,
            }
            if row["pose_valid"]:
                pose_valid_count += 1
            if row["sync_valid"]:
                sync_valid_count += 1
            if row["reconstructable"]:
                reconstructable_count += 1
            rows.append(row)

        usable_frames = sum(1 for row in rows if row["quality_score"] >= 0.7 and row["contact_confidence"] >= 0.5)
        return {
            "generated_at": now_text(),
            "session_id": manifest.get("session_id", session_dir.name),
            "rows": rows,
            "summary": {
                "frame_count": len(rows),
                "usable_frame_count": usable_frames,
                "usable_ratio": round(usable_frames / max(1, len(rows)), 4),
                "camera_alignment_available": bool(camera_entries),
                "annotation_links": sum(len(row["annotation_refs"]) for row in rows),
                "pressure_alignment_available": bool(pressure_entries),
                "robot_alignment_available": bool(robot_entries),
                "alignment_threshold_ms": alignment_threshold_ms,
                "pose_valid_count": pose_valid_count,
                "sync_valid_count": sync_valid_count,
                "reconstructable_count": reconstructable_count,
                "calibration_valid": calibration_valid,
                "patient_frame_valid": patient_frame_valid,
            },
        }

    @staticmethod
    def _extract_robot_pose(entry: dict[str, Any] | None) -> dict[str, Any]:
        if not entry:
            return {"valid": False, "source": "missing", "pose": {}}
        payload = dict(entry.get("data", {}))
        raw_pose = payload.get("tcp_pose", {})
        if isinstance(raw_pose, dict):
            pose = {key: float(raw_pose.get(key, 0.0) or 0.0) for key in ["x", "y", "z", "rx", "ry", "rz"]}
            return {"valid": True, "source": "tcp_pose_dict", "pose": pose}
        if isinstance(raw_pose, list):
            if len(raw_pose) == 16:
                matrix = [
                    [float(raw_pose[row * 4 + col] or 0.0) for col in range(4)]
                    for row in range(4)
                ]
                pose = {
                    "x": float(matrix[0][3]),
                    "y": float(matrix[1][3]),
                    "z": float(matrix[2][3]),
                    "rx": 0.0,
                    "ry": 0.0,
                    "rz": 0.0,
                }
                return {"valid": True, "source": "tcp_pose_matrix", "pose": pose, "matrix": matrix}
            if len(raw_pose) >= 6:
                pose = {key: float(raw_pose[index] or 0.0) for index, key in enumerate(["x", "y", "z", "rx", "ry", "rz"])}
                return {"valid": True, "source": "tcp_pose_list", "pose": pose}
        return {"valid": False, "source": "unsupported_robot_pose", "pose": {}}

    @staticmethod
    def _nearest(entries: list[dict[str, Any]], ts_ns: int) -> dict[str, Any] | None:
        if not entries:
            return None
        return min(entries, key=lambda item: abs(int(item.get("source_ts_ns", 0) or item.get("monotonic_ns", 0)) - ts_ns))

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
