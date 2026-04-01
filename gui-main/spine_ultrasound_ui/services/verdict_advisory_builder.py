from __future__ import annotations

from typing import Any


class VerdictAdvisoryBuilder:
    @staticmethod
    def build_unavailable(advisory: dict[str, Any]) -> dict[str, Any]:
        payload = dict(advisory)
        payload.setdefault("summary_state", "unavailable")
        payload.setdefault("summary_label", "运行时裁决不可用")
        payload.setdefault("detail", "authoritative runtime verdict unavailable")
        payload["authority_source"] = "verdict_unavailable"
        payload["verdict_kind"] = "unavailable"
        payload["approximate"] = True
        payload["advisory_python"] = dict(advisory)
        payload["final_verdict"] = {
            "accepted": False,
            "reason": str(payload.get("detail", "authoritative runtime verdict unavailable")),
            "evidence_id": "",
            "expected_state_delta": {"next_state": "await_authoritative_runtime"},
            "policy_state": str(payload.get("summary_state", "unavailable")),
            "source": "verdict_unavailable",
            "advisory_only": True,
            "authoritative": False,
        }
        return payload
