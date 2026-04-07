from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.backend_errors import normalize_backend_exception


class SessionGovernanceService:
    """Summarize session intelligence artifacts for the desktop.

    The desktop does not need the full raw contents of every generated artifact on each
    refresh. It needs an operator-facing governance digest: is the current session
    internally consistent, resumable, and eventually releasable.
    """

    def build(self, session_dir: Path | None) -> dict[str, Any]:
        if session_dir is None:
            return {
                "summary_state": "idle",
                "summary_label": "未锁定会话",
                "detail": "当前还没有锁定会话，因此不存在会话治理与发布门禁结果。",
                "blockers": [],
                "warnings": [],
                "artifact_counts": {"registered": 0, "ready": 0},
                "release_gate": {},
                "resume": {},
                "diagnostics": {},
                "integrity": {},
                "selected_execution": {},
                "incidents": {},
            }

        read_errors: list[dict[str, Any]] = []
        manifest = self._read_json(session_dir / "meta" / "manifest.json", read_errors)
        gate = self._read_json(session_dir / "export" / "release_gate_decision.json", read_errors)
        integrity = self._read_json(session_dir / "export" / "session_integrity.json", read_errors)
        diagnostics = self._read_json(session_dir / "export" / "diagnostics_pack.json", read_errors)
        resume = self._read_json(session_dir / "meta" / "resume_decision.json", read_errors)
        incidents = self._read_json(session_dir / "derived" / "incidents" / "session_incidents.json", read_errors)
        selected_execution = self._read_json(session_dir / "derived" / "planning" / "selected_execution_rationale.json", read_errors)
        contract = self._read_json(session_dir / "derived" / "session" / "contract_consistency.json", read_errors)
        control_plane_snapshot = self._read_json(session_dir / "derived" / "session" / "control_plane_snapshot.json", read_errors)
        evidence_seal = self._read_json(session_dir / "meta" / "session_evidence_seal.json", read_errors)
        event_delivery = self._read_json(session_dir / "derived" / "events" / "event_delivery_summary.json", read_errors)

        blockers: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        if gate:
            for reason in list(gate.get("blocking_reasons", [])):
                blockers.append({"name": "release_gate", "detail": str(reason)})
            for reason in list(gate.get("warning_reasons", [])):
                warnings.append({"name": "release_gate", "detail": str(reason)})
        if contract and not bool(contract.get("summary", {}).get("consistent", True)):
            blockers.append({"name": "contract_consistency", "detail": "contract_consistency 未通过。"})
        if integrity and not bool(integrity.get("summary", {}).get("integrity_ok", True)):
            blockers.append({"name": "artifact_integrity", "detail": "session_integrity 未通过。"})
        if resume and not bool(resume.get("resume_allowed", True)):
            warnings.append({"name": "resume", "detail": "当前 resume_decision 不允许恢复。"})
        if int(event_delivery.get("summary", {}).get("continuity_gap_count", 0) or 0) > 0:
            blockers.append({"name": "event_delivery", "detail": "事件连续性存在 gap。"})
        if not bool(evidence_seal.get("seal_digest", "")):
            warnings.append({"name": "session_evidence_seal", "detail": "会话证据封存尚未形成。"})
        for error in read_errors:
            warnings.append({"name": error["name"], "detail": error["detail"]})

        summary_state = "ready"
        if blockers:
            summary_state = "blocked"
        elif warnings:
            summary_state = "warning"
        artifact_registry = dict(manifest.get("artifact_registry", {}))
        dominant_incidents = [
            item.get("incident_type", "")
            for item in sorted(incidents.get("incidents", []), key=lambda row: int(row.get("count", 1) or 1), reverse=True)[:3]
            if item.get("incident_type")
        ]
        detail = self._detail(summary_state, gate, blockers, warnings)
        return {
            "summary_state": summary_state,
            "summary_label": {
                "ready": "会话治理通过",
                "warning": "会话治理告警",
                "blocked": "会话治理阻塞",
            }.get(summary_state, "会话治理未知"),
            "detail": detail,
            "session_id": str(manifest.get("session_id", session_dir.name)),
            "session_dir": str(session_dir),
            "blockers": blockers,
            "warnings": warnings,
            "artifact_counts": {
                "registered": len(artifact_registry),
                "ready": sum(1 for descriptor in artifact_registry.values() if bool(descriptor.get("ready", False))),
            },
            "release_gate": {
                "release_allowed": bool(gate.get("release_allowed", False)),
                "release_candidate": bool(gate.get("release_candidate", False)),
                "blocking_reasons": list(gate.get("blocking_reasons", [])),
                "warning_reasons": list(gate.get("warning_reasons", [])),
                "required_remediations": list(gate.get("required_remediations", [])),
            },
            "resume": {
                "resume_allowed": bool(resume.get("resume_allowed", False)),
                "resume_reasons": list(resume.get("blocking_reasons", [])),
            },
            "diagnostics": {
                "command_count": int(diagnostics.get("summary", {}).get("command_count", 0) or 0),
                "alarm_count": int(diagnostics.get("summary", {}).get("alarm_count", 0) or 0),
                "incident_count": int(diagnostics.get("summary", {}).get("incident_count", 0) or 0),
                "continuity_gap_count": int(event_delivery.get("summary", {}).get("continuity_gap_count", 0) or 0),
            },
            "integrity": dict(integrity.get("summary", {})),
            "contract": dict(contract.get("summary", {})),
            "control_plane": {"summary_state": control_plane_snapshot.get("summary_state", ""), "summary_label": control_plane_snapshot.get("summary_label", "")},
            "evidence_seal": {"seal_digest": evidence_seal.get("seal_digest", ""), "artifact_count": int(evidence_seal.get("artifact_count", 0) or 0)},
            "selected_execution": {
                "selected_candidate_id": selected_execution.get("selected_candidate_id", ""),
                "selected_profile": selected_execution.get("selected_profile", ""),
            },
            "incidents": {
                "count": int(incidents.get("summary", {}).get("count", 0) or 0),
                "dominant_types": dominant_incidents,
            },
            "artifact_errors": read_errors,
        }

    @staticmethod
    def _detail(summary_state: str, gate: dict[str, Any], blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> str:
        if summary_state == "blocked":
            return f"当前会话存在 {len(blockers)} 项治理阻塞，发布门禁未通过。"
        if summary_state == "warning":
            return f"当前会话没有硬阻塞，但仍有 {len(warnings)} 项治理告警。"
        if gate:
            return "当前会话的治理链条完整，发布门禁结果为可通过。"
        return "当前会话已锁定，但还没有形成完整的治理产物。"

    @staticmethod
    def _read_json(path: Path, errors: list[dict[str, Any]]) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            normalized = normalize_backend_exception(exc, command='read_session_artifact', context='session-governance')
            errors.append({
                'name': 'artifact_read_error',
                'path': str(path),
                'error_type': normalized.error_type,
                'detail': f'{path.name}: {normalized.message}',
                'retryable': normalized.retryable,
            })
            return {}
