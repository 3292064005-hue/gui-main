from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState
from spine_ultrasound_ui.utils import now_text


class PostprocessService:
    def __init__(self, exp_manager: ExperimentManager):
        self.exp_manager = exp_manager

    def preprocess(self, session_dir: Path | None) -> CapabilityStatus:
        if session_dir is None:
            return self._blocked("图像预处理")
        target = self._build_quality_timeline(session_dir)
        self.exp_manager.append_artifact(session_dir, "quality_timeline", target)
        return CapabilityStatus(
            ready=True,
            state="AVAILABLE",
            implementation=ImplementationState.IMPLEMENTED.value,
            detail=f"质量时间线已生成：{target.name}",
        )

    def reconstruct(self, session_dir: Path | None) -> CapabilityStatus:
        if session_dir is None:
            return self._blocked("局部重建")
        target = self._build_replay_index(session_dir)
        self.exp_manager.append_artifact(session_dir, "replay_index", target)
        return CapabilityStatus(
            ready=True,
            state="AVAILABLE",
            implementation=ImplementationState.IMPLEMENTED.value,
            detail=f"回放索引已生成：{target.name}",
        )

    def assess(self, session_dir: Path | None) -> CapabilityStatus:
        if session_dir is None:
            return self._blocked("Cobb 角评估")
        self._ensure_artifact(session_dir, "derived/quality/quality_timeline.json", self._build_quality_timeline)
        self._ensure_artifact(session_dir, "replay/replay_index.json", self._build_replay_index)
        target = self._build_session_report(session_dir)
        self.exp_manager.append_artifact(session_dir, "session_report", target)
        return CapabilityStatus(
            ready=True,
            state="AVAILABLE",
            implementation=ImplementationState.IMPLEMENTED.value,
            detail=f"会话报告已生成：{target.name}",
        )

    def refresh_all(self, session_dir: Path | None) -> dict[str, CapabilityStatus]:
        return {
            "preprocess": self.preprocess(session_dir),
            "reconstruction": self.reconstruct(session_dir),
            "assessment": self.assess(session_dir),
        }

    @staticmethod
    def _blocked(label: str) -> CapabilityStatus:
        return CapabilityStatus(
            ready=False,
            state="BLOCKED",
            implementation=ImplementationState.IMPLEMENTED.value,
            detail=f"{label}需要先完成一次有效会话。",
        )

    def _ensure_artifact(self, session_dir: Path, relative_path: str, builder) -> Path:
        target = session_dir / relative_path
        if target.exists():
            return target
        return builder(session_dir)

    def _build_quality_timeline(self, session_dir: Path) -> Path:
        quality_entries = self._read_jsonl(session_dir / "raw" / "ui" / "quality_feedback.jsonl")
        points = [
            {
                "seq": int(entry.get("seq", 0)),
                "ts_ns": int(entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0)),
                "image_quality": float(entry.get("data", {}).get("image_quality", 0.0)),
                "feature_confidence": float(entry.get("data", {}).get("feature_confidence", 0.0)),
                "quality_score": float(entry.get("data", {}).get("quality_score", 0.0)),
                "need_resample": bool(entry.get("data", {}).get("need_resample", False)),
            }
            for entry in quality_entries
        ]
        quality_scores = [point["quality_score"] for point in points]
        payload = {
            "generated_at": now_text(),
            "session_id": self.exp_manager.load_manifest(session_dir)["session_id"],
            "sample_count": len(points),
            "points": points,
            "summary": {
                "min_quality_score": min(quality_scores) if quality_scores else 0.0,
                "max_quality_score": max(quality_scores) if quality_scores else 0.0,
                "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 4) if quality_scores else 0.0,
                "resample_events": sum(1 for point in points if point["need_resample"]),
            },
        }
        return self.exp_manager.save_json_artifact(session_dir, "derived/quality/quality_timeline.json", payload)

    def _build_replay_index(self, session_dir: Path) -> Path:
        manifest = self.exp_manager.load_manifest(session_dir)
        camera_entries = self._read_jsonl(session_dir / "raw" / "camera" / "index.jsonl")
        ultrasound_entries = self._read_jsonl(session_dir / "raw" / "ultrasound" / "index.jsonl")
        payload = {
            "generated_at": now_text(),
            "session_id": manifest["session_id"],
            "streams": {
                "camera": {
                    "index_path": "raw/camera/index.jsonl",
                    "frame_count": len(camera_entries),
                    "latest_frame": camera_entries[-1]["data"]["frame_path"] if camera_entries else "",
                },
                "ultrasound": {
                    "index_path": "raw/ultrasound/index.jsonl",
                    "frame_count": len(ultrasound_entries),
                    "latest_frame": ultrasound_entries[-1]["data"]["frame_path"] if ultrasound_entries else "",
                },
                "core_topics": [
                    topic
                    for topic in ["robot_state", "contact_state", "scan_progress", "alarm_event"]
                    if (session_dir / "raw" / "core" / f"{topic}.jsonl").exists()
                ],
            },
            "artifacts": dict(manifest.get("artifacts", {})),
        }
        return self.exp_manager.save_json_artifact(session_dir, "replay/replay_index.json", payload)

    def _build_session_report(self, session_dir: Path) -> Path:
        manifest = self.exp_manager.load_manifest(session_dir)
        summary = self._read_json(session_dir / "export" / "summary.json")
        quality_timeline = self._read_json(session_dir / "derived" / "quality" / "quality_timeline.json")
        replay_index = self._read_json(session_dir / "replay" / "replay_index.json")
        payload = {
            "generated_at": now_text(),
            "experiment_id": manifest["experiment_id"],
            "session_id": manifest["session_id"],
            "core_state": summary.get("core_state", "UNKNOWN"),
            "workflow": summary.get("workflow", {}),
            "safety": summary.get("safety", {}),
            "recording": summary.get("recording", {}),
            "quality_summary": quality_timeline.get("summary", {}),
            "replay_summary": {
                "camera_frames": replay_index.get("streams", {}).get("camera", {}).get("frame_count", 0),
                "ultrasound_frames": replay_index.get("streams", {}).get("ultrasound", {}).get("frame_count", 0),
                "core_topics": replay_index.get("streams", {}).get("core_topics", []),
            },
            "artifacts": self.exp_manager.load_manifest(session_dir).get("artifacts", {}),
        }
        return self.exp_manager.save_json_artifact(session_dir, "export/session_report.json", payload)

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entries.append(json.loads(line))
        return entries

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
