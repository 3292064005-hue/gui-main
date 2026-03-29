from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text


class FrameSyncIndexer:
    def build(self, session_dir: Path) -> dict[str, Any]:
        camera_entries = self._read_jsonl(session_dir / "raw" / "camera" / "index.jsonl")
        ultrasound_entries = self._read_jsonl(session_dir / "raw" / "ultrasound" / "index.jsonl")
        quality_entries = self._read_jsonl(session_dir / "raw" / "ui" / "quality_feedback.jsonl")
        contact_entries = self._read_jsonl(session_dir / "raw" / "core" / "contact_state.jsonl")
        progress_entries = self._read_jsonl(session_dir / "raw" / "core" / "scan_progress.jsonl")
        annotations = self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
        manifest = self._read_json(session_dir / "meta" / "manifest.json")
        rows: list[dict[str, Any]] = []
        for index, us_entry in enumerate(ultrasound_entries):
            us_ts = int(us_entry.get("source_ts_ns", 0) or us_entry.get("monotonic_ns", 0))
            quality = self._nearest(quality_entries, us_ts)
            camera = self._nearest(camera_entries, us_ts)
            contact = self._nearest(contact_entries, us_ts)
            progress = self._nearest(progress_entries, us_ts)
            matching_annotations = [
                dict(item.get("data", {}))
                for item in annotations
                if abs(int(item.get("source_ts_ns", 0) or item.get("monotonic_ns", 0)) - us_ts) <= 250_000_000
            ][:6]
            rows.append(
                {
                    "frame_id": index + 1,
                    "ts_ns": us_ts,
                    "ultrasound_frame_path": us_entry.get("data", {}).get("frame_path", ""),
                    "camera_frame_path": camera.get("data", {}).get("frame_path", "") if camera else "",
                    "quality_score": float(quality.get("data", {}).get("quality_score", 0.0)) if quality else 0.0,
                    "contact_confidence": float(contact.get("data", {}).get("confidence", 0.0)) if contact else 0.0,
                    "pressure_current": float(contact.get("data", {}).get("pressure_current", 0.0)) if contact else 0.0,
                    "recommended_action": str(contact.get("data", {}).get("recommended_action", "")) if contact else "",
                    "segment_id": int(progress.get("data", {}).get("active_segment", 0)) if progress else 0,
                    "progress_pct": float(progress.get("data", {}).get("overall_progress", 0.0)) if progress else 0.0,
                    "annotation_refs": matching_annotations,
                }
            )
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
            },
        }

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
