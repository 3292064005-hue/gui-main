from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig


class ControlPlaneRawFactsService:
    REQUIRED_TOPICS = ["core_state", "robot_state", "safety_status", "scan_progress", "contact_state"]

    def build(self, *, local_config: RuntimeConfig, runtime_config: dict[str, Any] | None = None, schema: dict[str, Any] | None = None, status: dict[str, Any] | None = None, health: dict[str, Any] | None = None, topic_catalog: dict[str, Any] | None = None, recent_commands: list[dict[str, Any]] | None = None, control_authority: dict[str, Any] | None = None) -> dict[str, Any]:
        runtime_config = dict((runtime_config or {}).get("runtime_config", runtime_config or {}))
        schema = dict(schema or {})
        status = dict(status or {})
        health = dict(health or {})
        topic_catalog = dict(topic_catalog or {})
        recent_commands = [dict(item) for item in (recent_commands or [])]
        control_authority = dict(control_authority or {})
        blockers: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []
        protocol_versions = {"status": status.get("protocol_version"), "schema": schema.get("protocol_version"), "health": health.get("protocol_version")}
        declared_versions = {int(v) for v in protocol_versions.values() if isinstance(v, (int, float))}
        protocol_ok = len(declared_versions) <= 1 and (not declared_versions or 1 in declared_versions)
        protocol_detail = ", ".join(f"{k}={v}" for k, v in protocol_versions.items() if v is not None) or "未提供协议版本"
        protocol_status = {"summary_state": "ready" if protocol_ok else "blocked", "summary_label": "协议一致" if protocol_ok else "协议不一致", "detail": protocol_detail, "versions": protocol_versions}
        if not protocol_ok:
            blockers.append({"name": "控制面协议不一致", "detail": protocol_detail})
        local_payload = local_config.to_dict()
        drift_fields = []
        matching_fields = 0
        compared_fields = 0
        for key, local_value in local_payload.items():
            if key not in runtime_config:
                continue
            compared_fields += 1
            remote_value = runtime_config.get(key)
            if remote_value == local_value:
                matching_fields += 1
            else:
                drift_fields.append({"field": key, "local": local_value, "remote": remote_value})
        missing_remote_fields = [key for key in local_payload.keys() if key not in runtime_config]
        if missing_remote_fields:
            warnings.append({"name": "后端运行配置字段不完整", "detail": f"后端缺少 {len(missing_remote_fields)} 个字段，示例：{', '.join(missing_remote_fields[:5])}"})
        config_sync_detail = f"配置一致 {matching_fields}/{compared_fields}" if not drift_fields else f"发现 {len(drift_fields)} 个配置漂移字段：{', '.join(item['field'] for item in drift_fields[:6])}"
        config_sync = {"summary_state": "blocked" if drift_fields else "ready", "summary_label": "配置一致" if not drift_fields else "配置漂移", "detail": config_sync_detail, "matching_fields": matching_fields, "compared_fields": compared_fields, "missing_remote_fields": missing_remote_fields, "drift_fields": drift_fields[:12]}
        if drift_fields:
            blockers.append({"name": "前后端运行配置不一致", "detail": config_sync_detail})
        topic_names = set()
        for item in topic_catalog.get("topics", []):
            if isinstance(item, dict):
                topic_names.add(str(item.get("name", "")))
            elif isinstance(item, str):
                topic_names.add(item)
        missing_topics = [name for name in self.REQUIRED_TOPICS if name not in topic_names]
        topic_coverage = {"required": list(self.REQUIRED_TOPICS), "available": sorted(name for name in topic_names if name), "missing": missing_topics, "coverage_percent": int(round(((len(self.REQUIRED_TOPICS) - len(missing_topics)) / len(self.REQUIRED_TOPICS)) * 100)), "summary_state": "ready" if not missing_topics else "degraded", "summary_label": "主题覆盖完整" if not missing_topics else "主题覆盖不足", "detail": "全部必需 topic 已提供" if not missing_topics else f"缺少 topic: {', '.join(missing_topics)}"}
        if missing_topics:
            warnings.append({"name": "关键遥测主题缺失", "detail": topic_coverage["detail"]})
        failed_recent = [item for item in recent_commands if not bool(item.get("ok", False))]
        command_window = {"count": len(recent_commands), "failed": len(failed_recent), "latest": recent_commands[-1] if recent_commands else {}, "summary_state": "ready" if not failed_recent else "degraded", "summary_label": "命令窗口健康" if not failed_recent else "命令窗口存在失败", "detail": "最近命令全部成功" if not failed_recent else f"最近 {len(failed_recent)} 条命令失败"}
        if failed_recent:
            warnings.append({"name": "最近命令失败", "detail": command_window["detail"]})
        summary_state = "blocked" if blockers else ("degraded" if warnings else "ready")
        return {"summary_state": summary_state, "summary_label": {"ready": "控制面一致", "degraded": "控制面降级", "blocked": "控制面阻塞"}[summary_state], "detail": "后端原始控制面事实，尚未做最终操作员投影。", "blockers": blockers, "warnings": warnings, "protocol_status": protocol_status, "config_sync": config_sync, "topic_coverage": topic_coverage, "command_window": command_window, "control_authority": control_authority, "health": health, "status": status, "schema": schema, "runtime_config": runtime_config}
