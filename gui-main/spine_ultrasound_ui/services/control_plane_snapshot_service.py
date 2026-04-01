from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.services.backend_projection_cache import BackendProjectionCache


class ControlPlaneSnapshotService:
    def __init__(self) -> None:
        self._projection_cache = BackendProjectionCache()

    def _update_partition(self, name: str, payload: dict[str, Any]) -> None:
        self._projection_cache.update_partition(name, payload)

    def build(
        self,
        *,
        backend_link: dict[str, Any] | None = None,
        control_authority: dict[str, Any] | None = None,
        bridge_observability: dict[str, Any] | None = None,
        config_report: dict[str, Any] | None = None,
        sdk_alignment: dict[str, Any] | None = None,
        model_report: dict[str, Any] | None = None,
        deployment_profile: dict[str, Any] | None = None,
        session_governance: dict[str, Any] | None = None,
        evidence_seal: dict[str, Any] | None = None,
        release_mode: str | None = None,
        runtime_doctor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        backend_link = dict(backend_link or {})
        bridge_observability = dict(bridge_observability or {})
        config_report = dict(config_report or {})
        sdk_alignment = dict(sdk_alignment or {})
        model_report = dict(model_report or {})
        deployment_profile = dict(deployment_profile or {})
        session_governance = dict(session_governance or {})
        evidence_seal = dict(evidence_seal or {})
        runtime_doctor = dict(runtime_doctor or {})
        backend_control_plane = dict(backend_link.get("control_plane", {}))
        control_authority = dict(control_authority or backend_control_plane.get("control_authority", {}))

        blockers: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        operator_hints: list[dict[str, Any]] = []

        def _push(kind: str, section: str, summary: dict[str, Any]) -> None:
            target = blockers if kind == "blockers" else warnings
            for item in summary.get(kind, []) or []:
                payload = dict(item)
                payload.setdefault("section", section)
                target.append(payload)

        for name, summary in (
            ("backend_link", backend_link),
            ("control_authority", control_authority),
            ("bridge_observability", bridge_observability),
            ("config", config_report),
            ("sdk_alignment", sdk_alignment),
            ("model", model_report),
            ("session_governance", session_governance),
            ("evidence_seal", evidence_seal),
            ("runtime_doctor", runtime_doctor),
        ):
            _push("blockers", name, summary)
            _push("warnings", name, summary)

        protocol_state = dict(backend_control_plane.get("protocol_status", {}))
        config_consistency = dict(backend_control_plane.get("config_sync", {}))
        topic_coverage = dict(backend_control_plane.get("topic_coverage", {}))
        recent_command_health = dict(backend_control_plane.get("command_window", {}))

        latest_telemetry_age_ms = backend_link.get("latest_telemetry_age_ms")
        if latest_telemetry_age_ms is None:
            latest_telemetry_age_ms = bridge_observability.get("latest_telemetry_age_ms")
        telemetry_freshness = {
            "summary_state": "blocked" if bool(backend_link.get("telemetry_stale") or bridge_observability.get("summary_state") == "blocked") else ("degraded" if bool(backend_link.get("telemetry_stale")) else "ready"),
            "summary_label": "遥测新鲜度正常" if not bool(backend_link.get("telemetry_stale")) else "遥测新鲜度不足",
            "detail": backend_link.get("detail") or bridge_observability.get("detail") or "未提供遥测新鲜度摘要。",
            "latest_telemetry_age_ms": latest_telemetry_age_ms,
            "telemetry_stale": bool(backend_link.get("telemetry_stale", False)),
        }

        ownership_state = {
            "summary_state": str(control_authority.get("summary_state", "unknown")),
            "summary_label": str(control_authority.get("summary_label", "control authority")),
            "detail": str(control_authority.get("detail", "")),
            "owner": dict(control_authority.get("owner", {})),
            "active_lease": dict(control_authority.get("active_lease", {})),
            "owner_provenance": dict(control_authority.get("owner_provenance", {})),
            "workspace_binding": control_authority.get("workspace_binding", ""),
            "session_binding": control_authority.get("session_binding", ""),
            "conflict_reason": control_authority.get("conflict_reason", ""),
        }
        session_locked = bool(session_governance.get("session_locked", False)) or session_governance.get("summary_state") in {"ready", "warning", "blocked"}
        session_lock = {
            "summary_state": "ready" if session_locked else "degraded",
            "summary_label": "会话已锁定" if session_locked else "会话未锁定",
            "detail": session_governance.get("detail", "会话治理状态未提供。"),
            "session_locked": session_locked,
            "session_id": session_governance.get("session_id", ""),
        }
        evidence_seal_state = {
            "summary_state": str(evidence_seal.get("summary_state", "ready" if not session_locked else ("unknown" if evidence_seal else "degraded"))),
            "summary_label": str(evidence_seal.get("summary_label", "证据封存待会话冻结后生成" if not session_locked else ("证据封存未提供" if not evidence_seal else "证据封存状态"))),
            "detail": str(evidence_seal.get("detail", "session unlocked" if not session_locked else "")),
        }
        resolved_release_mode = str(release_mode or deployment_profile.get("name", "dev"))

        canonical_sections = {
            "protocol_version": protocol_state,
            "config_consistency": config_consistency,
            "topic_coverage": topic_coverage,
            "telemetry_freshness": telemetry_freshness,
            "recent_command_health": recent_command_health,
            "ownership_state": ownership_state,
            "session_lock": session_lock,
            "deployment_profile": deployment_profile,
            "bridge_observability_state": bridge_observability,
            "evidence_seal_state": evidence_seal_state,
            "release_mode": {"name": resolved_release_mode},
            "runtime_doctor": dict(runtime_doctor),
            "sdk_alignment": sdk_alignment,
            "model_precheck": model_report,
            "config_baseline": config_report,
        }

        for section_name, summary in canonical_sections.items():
            self._update_partition(section_name, dict(summary))
            state = str(dict(summary).get("summary_state", "unknown"))
            if state == "blocked":
                blockers.append({
                    "section": section_name,
                    "name": dict(summary).get("summary_label", section_name),
                    "detail": dict(summary).get("detail", "blocked"),
                })
            elif state in {"degraded", "warning"}:
                warnings.append({
                    "section": section_name,
                    "name": dict(summary).get("summary_label", section_name),
                    "detail": dict(summary).get("detail", "degraded"),
                })

        if deployment_profile.get("review_only"):
            warnings.append({"section": "deployment_profile", "name": "review_only", "detail": "当前为只读审阅模式。"})
            operator_hints.append({"level": "warning", "message": "当前 profile 为 review，只允许回放、审阅与导出。"})
        if deployment_profile.get("requires_strict_control_authority") and ownership_state.get("summary_state") in {"degraded", "blocked"}:
            blockers.append({"section": "deployment_profile", "name": "strict_control_authority_required", "detail": "当前部署剖面要求严格控制权租约。"})
            operator_hints.append({"level": "blocker", "message": "先获取有效 lease，再执行任何写命令。"})
        if ownership_state.get("summary_state") == "blocked":
            operator_hints.append({"level": "blocker", "message": ownership_state.get("detail") or "控制权冲突。"})
        if config_consistency.get("summary_state") == "blocked":
            operator_hints.append({"level": "blocker", "message": config_consistency.get("detail") or "前后端配置不一致。"})
        if protocol_state.get("summary_state") == "blocked":
            operator_hints.append({"level": "blocker", "message": protocol_state.get("detail") or "协议版本不一致。"})

        if blockers:
            summary_state = "blocked"
        elif warnings:
            summary_state = "degraded"
        else:
            summary_state = "ready"

        summary_label = {
            "ready": "控制面已收敛",
            "degraded": "控制面降级",
            "blocked": "控制面阻塞",
        }.get(summary_state, "控制面未知")

        governance_readiness = {
            "summary_state": summary_state,
            "summary_label": summary_label,
            "detail": "统一控制面投影：链路、配置、控制权、观测、会话与证据单次汇总。",
            "percent": 100 if summary_state == "ready" else (70 if summary_state == "degraded" else 0),
            "blockers": blockers,
            "warnings": warnings,
            "operator_hints": operator_hints,
        }

        self._update_partition("governance_readiness", governance_readiness)
        self._update_partition("operator_hints", {"items": operator_hints})
        self._update_partition("blockers", {"items": blockers})
        self._update_partition("warnings", {"items": warnings})

        projection_snapshot = self._projection_cache.snapshot()
        return {
            "summary_state": summary_state,
            "summary_label": summary_label,
            "detail": governance_readiness["detail"],
            "blockers": blockers,
            "warnings": warnings,
            "operator_hints": operator_hints,
            "governance_readiness": governance_readiness,
            "protocol_version": protocol_state,
            "config_consistency": config_consistency,
            "topic_coverage": topic_coverage,
            "telemetry_freshness": telemetry_freshness,
            "recent_command_health": recent_command_health,
            "ownership_state": ownership_state,
            "session_lock": session_lock,
            "deployment_profile": dict(deployment_profile),
            "bridge_observability_state": dict(bridge_observability),
            "evidence_seal_state": evidence_seal_state,
            "release_mode": {"name": resolved_release_mode},
            "runtime_doctor": dict(runtime_doctor),
            "projection_revision": projection_snapshot["revision"],
            "projection_partitions": projection_snapshot["partitions"],
            "sections": {
                "backend_link": {"summary_state": backend_link.get("summary_state", "unknown"), "summary_label": backend_link.get("summary_label", "backend link")},
                "control_authority": {"summary_state": control_authority.get("summary_state", "unknown"), "summary_label": control_authority.get("summary_label", "control authority")},
                "bridge_observability": {"summary_state": bridge_observability.get("summary_state", "unknown"), "summary_label": bridge_observability.get("summary_label", "bridge observability")},
                "config": {"summary_state": config_report.get("summary_state", "unknown"), "summary_label": config_report.get("summary_label", "config baseline")},
                "sdk_alignment": {"summary_state": sdk_alignment.get("summary_state", "unknown"), "summary_label": sdk_alignment.get("summary_label", "sdk alignment")},
                "model": {"summary_state": model_report.get("summary_state", "unknown"), "summary_label": model_report.get("summary_label", "model precheck")},
                "deployment_profile": dict(deployment_profile),
                "runtime_doctor": {"summary_state": runtime_doctor.get("summary_state", "unknown"), "summary_label": runtime_doctor.get("summary_label", "runtime doctor")},
            },
        }
