from __future__ import annotations

import hashlib
import json
from typing import Any

from spine_ultrasound_ui.utils import now_text


class GuidanceReplayService:
    """Build the replay index for frozen camera guidance evidence."""

    def build(
        self,
        *,
        session_or_experiment_id: str,
        source_frame_set: dict[str, Any],
        processing_step_refs: list[str],
        candidate_hash: str,
        registration_hash: str,
        readiness_hash: str,
        calibration_bundle_hash: str,
    ) -> dict[str, Any]:
        """Return the replay index for guidance-only localization.

        Args:
            session_or_experiment_id: Freeze owner identifier.
            source_frame_set: Frozen frame set metadata.
            processing_step_refs: Processing step identifiers.
            candidate_hash: Registration candidate hash.
            registration_hash: Frozen registration hash.
            readiness_hash: Readiness artifact hash.
            calibration_bundle_hash: Calibration bundle hash.

        Returns:
            Replay index payload.

        Raises:
            No exceptions are raised.
        """
        payload = {
            "schema_version": "1.0",
            "replay_id": f"guidance-replay::{session_or_experiment_id}",
            "generated_at": now_text(),
            "frame_refs": list(source_frame_set.get("frame_refs", [])),
            "processing_step_refs": list(processing_step_refs),
            "candidate_hash": candidate_hash,
            "registration_hash": registration_hash,
            "readiness_hash": readiness_hash,
            "calibration_bundle_hash": calibration_bundle_hash,
        }
        payload["replay_hash"] = self._stable_hash(payload)
        return payload

    @staticmethod
    def _stable_hash(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
