from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.contracts import schema_catalog


class QAPackService:
    def build(self, session_dir: Path) -> dict[str, Any]:
        return {
            "session_dir": str(session_dir),
            "manifest": self._read_json(session_dir / "meta" / "manifest.json"),
            "report": self._read_json(session_dir / "export" / "session_report.json"),
            "replay": self._read_json(session_dir / "replay" / "replay_index.json"),
            "quality": self._read_json(session_dir / "derived" / "quality" / "quality_timeline.json"),
            "alarms": self._read_json(session_dir / "derived" / "alarms" / "alarm_timeline.json"),
            "frame_sync": self._read_json(session_dir / "derived" / "sync" / "frame_sync_index.json"),
            "compare": self._read_json(session_dir / "export" / "session_compare.json"),
            "trends": self._read_json(session_dir / "export" / "session_trends.json"),
            "diagnostics": self._read_json(session_dir / "export" / "diagnostics_pack.json"),
            "annotations": self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl"),
            "robot_profile": self._read_json(session_dir / "meta" / "xmate_profile.json"),
            "patient_registration": self._read_json(session_dir / "meta" / "patient_registration.json"),
            "scan_protocol": self._read_json(session_dir / "derived" / "preview" / "scan_protocol.json"),
            "schemas": schema_catalog(),
        }

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
