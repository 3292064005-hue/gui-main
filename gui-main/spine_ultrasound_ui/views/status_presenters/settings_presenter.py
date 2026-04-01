from __future__ import annotations

from .common import StatusViewContext


class SettingsPresenter:
    def apply(self, ctx: StatusViewContext) -> None:
        window = ctx.window
        profile_state = "已持久化" if ctx.persistence.get("config_exists") else "未保存"
        if ctx.persistence.get("ui_exists"):
            profile_state += " / 布局已保存"
        module_lines = [f"- {item.get('module')}: {item.get('status')} / {item.get('purpose')}" for item in ctx.sdk_alignment.get('modules', [])]
        command_lines = [f"- {item.get('ui_action')} -> {item.get('sdk_binding')}" for item in ctx.sdk_alignment.get('command_bindings', [])]
        safety_contract = dict(ctx.sdk_alignment.get('safety_contract', {}))
        note_parts = [
            f"对齐状态：{ctx.sdk_alignment.get('summary_label', '-')}",
            f"覆盖率：{ctx.sdk_alignment.get('feature_coverage', {}).get('coverage_percent', 0)}%",
            f"配置基线：{ctx.config_report.get('summary_label', '-')}",
            f"模型前检：{ctx.model_report.get('summary_label', '-')}",
            f"会话治理：{ctx.session_governance.get('summary_label', '-')}",
            f"前后端链路：{ctx.backend_link.get('summary_label', '-')}",
            f"桥接观测：{ctx.bridge_observability.get('summary_label', '-')}",
            "",
            "主线顺序:",
            *[f"{idx + 1}. {item}" for idx, item in enumerate(ctx.sdk_alignment.get('mainline_sequence', []))],
            "",
            "模块矩阵:",
            *module_lines,
            "",
            "命令映射:",
            *command_lines,
            "",
            "安全合同:",
            f"- collision={safety_contract.get('collision_detection_enabled', '-')}, sensitivity={safety_contract.get('collision_sensitivity', '-')}, fallback={safety_contract.get('collision_fallback_mm', '-')} mm",
            f"- soft_limit={safety_contract.get('soft_limit_enabled', '-')}, margin={safety_contract.get('joint_soft_limit_margin_deg', '-')}°",
            f"- singularity={safety_contract.get('singularity_avoidance_enabled', '-')}",
        ]
        for title, items in [
            ("配置阻塞项", ctx.config_blockers),
            ("配置告警", ctx.config_warnings),
            ("SDK 阻塞项", ctx.sdk_blockers),
            ("SDK 告警", ctx.sdk_warnings),
            ("模型阻塞项", ctx.model_blockers),
            ("模型告警", ctx.model_warnings),
            ("会话治理阻塞项", ctx.session_blockers),
            ("会话治理告警", ctx.session_warnings),
            ("链路阻塞项", ctx.backend_blockers),
            ("链路告警", ctx.backend_warnings),
            ("控制面阻塞项", ctx.control_blockers),
            ("控制面告警", ctx.control_warnings),
            ("桥接阻塞项", ctx.bridge_blockers),
            ("桥接告警", ctx.bridge_warnings),
        ]:
            if items:
                note_parts.extend(["", f"{title}:"])
                note_parts.extend([f"- {item.get('name')}: {item.get('detail')}" for item in items])
        if ctx.control_plane:
            note_parts.extend(["", "控制面摘要:", f"- {ctx.control_plane.get('detail', '-')}", f"- 配置同步：{ctx.control_plane.get('config_sync', {}).get('detail', '-')}", f"- 协议状态：{ctx.control_plane.get('protocol_status', {}).get('detail', '-')}", f"- 主题覆盖：{ctx.control_plane.get('topic_coverage', {}).get('coverage_percent', 0)}%"])
        if ctx.bridge_observability:
            note_parts.extend(["", "桥接观测摘要:", f"- detail={ctx.bridge_observability.get('detail', '-')}", f"- fresh={ctx.bridge_observability.get('freshness', {}).get('summary_label', '-')}", f"- cmd={ctx.bridge_observability.get('command_observability', {}).get('summary_label', '-')}" ])
        if ctx.session_governance:
            note_parts.extend(["", "会话治理摘要:", f"- detail={ctx.session_governance.get('detail', '-')}", f"- release_allowed={ctx.session_governance.get('release_gate', {}).get('release_allowed', False)}", f"- artifact_ready={ctx.session_governance.get('artifact_counts', {}).get('ready', 0)} / {ctx.session_governance.get('artifact_counts', {}).get('registered', 0)}", f"- dominant_incidents={', '.join(ctx.session_governance.get('incidents', {}).get('dominant_types', [])) or '-'}", f"- selected_profile={ctx.session_governance.get('selected_execution', {}).get('selected_profile', '-')}"])
        if ctx.sdk_runtime.get('errors'):
            note_parts.extend(["", "SDK 资产错误:"])
            note_parts.extend([f"- {item}" for item in ctx.sdk_runtime.get('errors', [])])
        window.settings_page.set_runtime_info(
            workspace=ctx.persistence.get("workspace", "-"),
            backend=window.backend.__class__.__name__,
            config_path=ctx.persistence.get("config_path", "-"),
            ui_path=ctx.persistence.get("ui_path", "-"),
            last_saved=f"配置 {ctx.persistence.get('last_config_save', '未保存')} / 布局 {ctx.persistence.get('last_ui_save', '未保存')}",
            profile_state=profile_state,
            sdk_family=ctx.sdk_alignment.get("sdk_family", "-"),
            sdk_summary=ctx.sdk_alignment.get("summary_label", "-"),
            robot_profile=f"{ctx.sdk_alignment.get('robot_model', '-')} / {ctx.sdk_alignment.get('sdk_robot_class', '-')} / {ctx.sdk_alignment.get('scan_rt_mode', '-')}",
            ip_link=f"remote={ctx.sdk_alignment.get('remote_ip', '-')} / local={ctx.sdk_alignment.get('local_ip', '-')} / {ctx.sdk_alignment.get('preferred_link', '-')}",
            sdk_note="\n".join(note_parts),
            backend_link_state=f"{ctx.backend_link.get('summary_label', '-')} / {ctx.backend_link.get('detail', '-')}",
            backend_stream_state=f"telemetry={'ON' if ctx.backend_link.get('telemetry_connected') else 'OFF'} / camera={'ON' if ctx.backend_link.get('camera_connected') else 'OFF'} / ultrasound={'ON' if ctx.backend_link.get('ultrasound_connected') else 'OFF'} / cmd_ok={ctx.backend_link.get('command_success_rate', 100)}% / cfg={ctx.control_plane.get('config_sync', {}).get('summary_label', '-')} / bridge={ctx.bridge_observability.get('summary_label', '-')}",
        )
