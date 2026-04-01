from __future__ import annotations

from typing import Any


class VerdictAuthorityResolver:
    @staticmethod
    def normalize(runtime_verdict: dict[str, Any], advisory: dict[str, Any]) -> dict[str, Any]:
        payload = dict(runtime_verdict)
        final_verdict = dict(payload.get("final_verdict", {}))
        blockers = list(payload.get("blockers", []))
        warnings = list(payload.get("warnings", []))
        summary_state = str(payload.get("summary_state") or ("blocked" if final_verdict.get("accepted") is False else "ready"))
        payload.setdefault("summary_state", summary_state)
        payload.setdefault("summary_label", str(advisory.get("summary_label") or {"ready": "模型前检通过", "warning": "模型前检告警", "blocked": "模型前检阻塞", "idle": "未生成路径", "unavailable": "运行时裁决不可用"}.get(summary_state, "模型前检")))
        payload.setdefault("detail", str(final_verdict.get("reason") or advisory.get("detail", "")))
        payload["warnings"] = warnings
        payload["blockers"] = blockers
        payload["final_verdict"] = {
            "accepted": bool(final_verdict.get("accepted", summary_state != "blocked")),
            "reason": str(final_verdict.get("reason") or payload.get("detail", "")),
            "evidence_id": str(final_verdict.get("evidence_id", "")),
            "expected_state_delta": final_verdict.get("expected_state_delta", {}),
            "policy_state": str(final_verdict.get("policy_state", summary_state)),
            "source": str(final_verdict.get("source") or payload.get("authority_source", "cpp_robot_core")),
            "advisory_only": False,
            "authoritative": True,
        }
        payload.setdefault("authority_source", str(payload["final_verdict"].get("source") or "cpp_robot_core"))
        payload.setdefault("verdict_kind", "final")
        payload.setdefault("approximate", False)
        payload.setdefault("advisory_python", advisory)
        payload.setdefault("model_contract", dict(advisory.get("model_contract", {})))
        payload.setdefault("envelope", dict(advisory.get("envelope", {})))
        payload.setdefault("dh_parameters", list(advisory.get("dh_parameters", [])))
        payload.setdefault("plan_metrics", dict(advisory.get("plan_metrics", {})))
        payload.setdefault("execution_selection", dict(advisory.get("execution_selection", {})))
        return payload
