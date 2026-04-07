from __future__ import annotations

import hashlib
import json
from typing import Any

from spine_ultrasound_ui.utils import now_text


class ManualAdjustmentService:
    """Normalize and hash optional operator guidance corrections.

    Manual adjustments are allowed only before session freeze. This service does
    not decide whether they are acceptable; it only produces a stable contract
    that can be audited and re-validated.
    """

    def normalize(self, adjustments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Return the normalized manual adjustment artifact.

        Args:
            adjustments: Optional list of operator-provided deltas.

        Returns:
            A JSON-serializable manual adjustment artifact with a stable hash.

        Raises:
            ValueError: Raised when any adjustment entry is not a mapping.
        """
        records: list[dict[str, Any]] = []
        for index, raw in enumerate(list(adjustments or []), start=1):
            if not isinstance(raw, dict):
                raise ValueError("manual adjustment entries must be mappings")
            records.append(
                {
                    "adjustment_id": str(raw.get("adjustment_id", f"adj-{index:03d}")),
                    "operator_id": str(raw.get("operator_id", "operator")),
                    "created_at": str(raw.get("created_at", now_text())),
                    "reason": str(raw.get("reason", "manual_guidance_review")),
                    "target": str(raw.get("target", "guidance_zone")),
                    "delta": dict(raw.get("delta", {})),
                    "pre_hash": str(raw.get("pre_hash", "")),
                    "post_hash": str(raw.get("post_hash", "")),
                }
            )
        payload = {
            "schema_version": "1.0",
            "generated_at": now_text(),
            "adjustments": records,
            "adjustment_count": len(records),
        }
        payload["hash"] = self._stable_hash(payload)
        return payload

    @staticmethod
    def _stable_hash(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
