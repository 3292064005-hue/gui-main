from __future__ import annotations

from pathlib import Path
from typing import Any


class SessionIntelligenceInputLoader:
    """Load persisted session artifacts needed for intelligence products."""

    def load(self, service, session_dir: Path) -> dict[str, Any]:
        manifest = service._read_json(session_dir / "meta" / "manifest.json")
        return {
            "manifest": manifest,
            "scan_plan": service._read_json(session_dir / "meta" / "scan_plan.json"),
            "command_journal": service._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl"),
            "annotations": service._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl"),
            "alarms": service._read_json(session_dir / "derived" / "alarms" / "alarm_timeline.json"),
            "quality": service._read_json(session_dir / "derived" / "quality" / "quality_timeline.json"),
            "report": service._read_json(session_dir / "export" / "session_report.json"),
            "summary": service._read_json(session_dir / "export" / "summary.json"),
            "evidence_seal": service._read_json(session_dir / "meta" / "session_evidence_seal.json"),
            "integrity": service.integrity.build(session_dir),
            "session_id": str(manifest.get("session_id", session_dir.name)),
        }
