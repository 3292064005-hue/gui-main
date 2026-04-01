from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReleaseGateInputLoader:
    """Load release-gate inputs from the canonical session layout."""

    def load(self, session_dir: Path) -> dict[str, Any]:
        """Load all inputs required by the release gate.

        Args:
            session_dir: Session directory containing derived/export/meta assets.

        Returns:
            Dictionary of named input payloads.

        Raises:
            No exceptions are raised. Missing files resolve to empty payloads.
        """
        return {
            "contract": self._read_json(session_dir / "derived" / "session" / "contract_consistency.json"),
            "release_evidence": self._read_json(session_dir / "export" / "release_evidence_pack.json"),
            "diagnostics": self._read_json(session_dir / "export" / "diagnostics_pack.json"),
            "integrity": self._read_json(session_dir / "export" / "session_integrity.json"),
            "event_delivery": self._read_json(session_dir / "derived" / "events" / "event_delivery_summary.json"),
            "resume_outcomes": self._read_json(session_dir / "derived" / "session" / "resume_attempt_outcomes.json"),
            "selected_execution": self._read_json(session_dir / "derived" / "planning" / "selected_execution_rationale.json"),
            "command_policy_snapshot": self._read_json(session_dir / "derived" / "session" / "command_policy_snapshot.json"),
            "contract_kernel_diff": self._read_json(session_dir / "derived" / "session" / "contract_kernel_diff.json"),
            "evidence_seal": self._read_json(session_dir / "meta" / "session_evidence_seal.json"),
            "control_plane_snapshot": self._read_json(session_dir / "derived" / "session" / "control_plane_snapshot.json"),
            "manifest": self._read_json(session_dir / "meta" / "manifest.json"),
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
