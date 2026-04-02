from __future__ import annotations

from .common import StatusViewContext, join_lines, set_text_edit_plain_preserve_scroll


class PreparePresenter:
    def apply(self, ctx: StatusViewContext) -> None:
        window = ctx.window
        window.prepare_page.lbl_toolset.setText(str(ctx.config.get("tool_name", "-")))
        window.prepare_page.lbl_load.setText(f"{ctx.config.get('load_kg', '-')} kg")
        window.prepare_page.lbl_sdk.setText("ROKAE xCore SDK (C++ mainline)")
        window.prepare_page.lbl_robot_class.setText(f"{ctx.sdk_alignment.get('sdk_robot_class', ctx.config.get('sdk_robot_class', '-'))} / {ctx.config.get('axis_count', '-')} 轴")
        window.prepare_page.lbl_power.setText("ON" if ctx.robot.get("powered", False) else "OFF")
        window.prepare_page.lbl_mode.setText(ctx.operate_mode)
        window.prepare_page.lbl_rt_mode.setText(ctx.config.get("rt_mode", "-"))
        window.prepare_page.lbl_preferred_link.setText(ctx.config.get("preferred_link", "-"))
        window.prepare_page.lbl_camera.setText(f"{ctx.devices['camera']['health']} / fresh={ctx.devices['camera'].get('fresh', False)}")
        window.prepare_page.lbl_ultrasound.setText(f"{ctx.devices['ultrasound']['health']} / fresh={ctx.devices['ultrasound'].get('fresh', False)}")
        window.prepare_page.lbl_pressure.setText(f"{ctx.devices['pressure']['health']} / fresh={ctx.devices['pressure'].get('fresh', False)}")
        window.prepare_page.lbl_ip_pair.setText(f"remote={ctx.config.get('remote_ip', '-')} / local={ctx.config.get('local_ip', '-')}")
        window.prepare_page.lbl_readiness.setText(f"就绪度：{ctx.readiness_percent}%")
        readiness_lines = [f"[{'OK' if item.get('ready') else 'BLOCK'}] {item.get('name')}: {item.get('detail')}" for item in ctx.readiness.get('checks', [])]
        if ctx.config_report:
            readiness_lines.extend(["", f"配置基线：{ctx.config_report.get('summary_label', '-')}" ])
            readiness_lines.extend([f"[{'OK' if item.get('ok') else ('BLOCK' if item.get('severity') == 'blocker' else 'WARN')}] {item.get('name')}: {item.get('detail')}" for item in ctx.config_report.get('checks', [])])
        if ctx.model_report:
            readiness_lines.extend(["", f"模型前检：{ctx.model_report.get('summary_label', '-')}", str(ctx.model_report.get('detail', '-'))])
        if ctx.session_governance and ctx.session_governance.get('summary_state') != 'idle':
            readiness_lines.extend(["", f"会话治理：{ctx.session_governance.get('summary_label', '-')}", str(ctx.session_governance.get('detail', '-'))])
        if ctx.backend_link:
            readiness_lines.extend(["", f"前后端链路：{ctx.backend_link.get('summary_label', '-')}", str(ctx.backend_link.get('detail', '-'))])
        if ctx.control_authority:
            readiness_lines.extend(["", f"控制权：{ctx.control_authority.get('summary_label', '-')}", str(ctx.control_authority.get('detail', '-'))])
        if ctx.bridge_observability:
            readiness_lines.extend(["", f"桥接观测：{ctx.bridge_observability.get('summary_label', '-')}", str(ctx.bridge_observability.get('detail', '-'))])
        set_text_edit_plain_preserve_scroll(window.prepare_page.txt_blockers, join_lines(readiness_lines, "暂无启动前检查结果。"))
        window.prepare_page.lbl_sdk_state.setText(f"SDK 状态：{ctx.sdk_alignment.get('summary_label', '-')}")
        sdk_check_lines = []
        for item in ctx.sdk_alignment.get('checks', []):
            prefix = "OK" if item.get('ok') else ("BLOCK" if item.get('severity') == 'blocker' else "WARN")
            sdk_check_lines.append(f"[{prefix}] {item.get('name')}: {item.get('detail')}")
        if ctx.sdk_alignment.get('mainline_sequence'):
            sdk_check_lines.extend(["", "主线顺序:"])
            sdk_check_lines.extend([f"{idx + 1}. {step}" for idx, step in enumerate(ctx.sdk_alignment.get('mainline_sequence', []))])
        set_text_edit_plain_preserve_scroll(window.prepare_page.txt_sdk, join_lines(sdk_check_lines, "暂无 SDK 检查结果。"))
