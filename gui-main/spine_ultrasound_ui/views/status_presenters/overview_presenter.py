from __future__ import annotations

from .common import StatusViewContext, html_summary, set_text_edit_html_preserve_scroll


class OverviewPresenter:
    def apply(self, ctx: StatusViewContext) -> None:
        window = ctx.window
        metrics = ctx.metrics
        pose = ctx.pose
        state_kind = window._system_state_kind(ctx.system_state)
        total_blockers = (
            len(ctx.blockers)
            + len(ctx.config_blockers)
            + len(ctx.session_blockers)
            + len(ctx.backend_blockers)
            + len(ctx.bridge_blockers)
        )

        window._set_badge_state(window.system_state_label, f"状态 · {ctx.system_state}", state_kind)
        window._set_badge_state(window.exp_id_label, f"实验 · {ctx.exp_id}", "ok")
        window._set_badge_state(window.readiness_label, f"就绪 · {ctx.readiness_percent}%", ctx.readiness_state)
        window._set_badge_state(window.header_state_pill, f"系统 · {ctx.system_state}", state_kind)
        window._set_badge_state(window.header_mode_pill, f"模式 · {ctx.operate_mode}", "ok" if ctx.operate_mode not in {"-", "manual"} else "warn")
        window._set_badge_state(window.header_exp_pill, f"实验 · {ctx.exp_id}", "ok" if ctx.current_exp else "warn")
        window._set_badge_state(window.header_step_pill, f"下一步 · {ctx.recommended_label}", ctx.readiness_state)

        extra_blockers = ctx.blockers + [item.get("name", "") for item in ctx.config_blockers] + [item.get("name", "") for item in ctx.session_blockers] + [item.get("name", "") for item in ctx.backend_blockers] + [item.get("name", "") for item in ctx.bridge_blockers]
        self._set_optional_text(window, "lbl_next_action", f"下一步：{ctx.recommended_label}")
        self._set_optional_text(window, "lbl_next_reason", ctx.recommended_reason)
        self._set_optional_text(window, "lbl_next_tab", f"建议页面：{ctx.recommended_tab}")
        self._set_optional_text(window, "lbl_readiness_percent", f"{ctx.readiness_percent}%")
        self._set_optional_text(window, "lbl_readiness_detail", f"{ctx.readiness.get('passed', 0)} / {ctx.readiness.get('total', 0)} 检查通过")
        self._set_optional_text(
            window,
            "lbl_readiness_blockers",
            "阻塞项：" + ("、".join([item for item in extra_blockers if item]) if extra_blockers else "无"),
        )

        window.card_state.update_text(ctx.system_state, f"Operate mode: {ctx.operate_mode}")
        window.card_state.set_tone("danger" if state_kind == "danger" else "accent")
        window.card_exp.update_text(ctx.exp_id, ctx.current_exp.get("session_id", "-") if ctx.current_exp else "尚未创建实验")
        window.card_readiness.update_text(f"{ctx.readiness_percent}%", f"推荐：{ctx.recommended_label} / 阻塞：{len(ctx.blockers)} 项")
        window.card_readiness.set_tone("success" if ctx.readiness_percent >= 100 else "warning")
        window.card_pressure.update_text(f"{metrics['pressure_current']:.2f} / {metrics['pressure_target']:.2f} N", f"{metrics['contact_mode']} / {metrics.get('recommended_action', '-')}")
        window.card_pressure.set_tone("success" if metrics["contact_mode"] in {"CONTACT_STABLE", "STABLE_CONTACT"} else "warning")
        window.card_pose.update_text(f"x={pose['x']:.1f}, y={pose['y']:.1f}, z={pose['z']:.1f}", f"rx={pose['rx']:.1f}, ry={pose['ry']:.1f}, rz={pose['rz']:.1f}")
        window.card_quality.update_text(f"图像 {metrics['image_quality']:.2f}", f"质量分 {metrics.get('quality_score', 0.0):.2f}")
        window.card_quality.set_tone("warning" if metrics.get('quality_score', 0.0) < 0.75 else "success")
        window.card_result.update_text(f"扫描进度 {metrics['scan_progress']:.0f}%", f"段 {metrics['segment_id']} / RL {'RUN' if ctx.rl_status.get('running') else 'IDLE'} / 录制 {'ON' if ctx.recording.get('recording', False) else 'OFF'}")

        summary_lines = [
            ("当前系统状态", ctx.system_state),
            ("当前实验", ctx.exp_id),
            ("当前会话", ctx.current_exp.get("session_id", "-") if ctx.current_exp else "-"),
            ("流程就绪度", f"{ctx.readiness_percent}% / 建议 {ctx.recommended_label}"),
            ("SDK 主线", f"{ctx.sdk_alignment.get('summary_label', '-')} / 覆盖 {ctx.sdk_alignment.get('feature_coverage', {}).get('coverage_percent', 0)}%"),
            ("配置基线", f"{ctx.config_report.get('summary_label', '-')} / 阻塞 {len(ctx.config_blockers)} / 告警 {len(ctx.config_warnings)}"),
            ("模型前检", f"{ctx.model_report.get('summary_label', '-')} / 阻塞 {len(ctx.model_blockers)} / 告警 {len(ctx.model_warnings)}"),
            ("会话治理", f"{ctx.session_governance.get('summary_label', '-')} / 阻塞 {len(ctx.session_blockers)} / 告警 {len(ctx.session_warnings)}"),
            ("前后端链路", f"{ctx.backend_link.get('summary_label', '-')} / 命令成功率 {ctx.backend_link.get('command_success_rate', 100)}% / telemetry {'ON' if ctx.backend_link.get('telemetry_connected') else 'OFF'}"),
            ("控制面", f"{ctx.control_plane.get('summary_label', '-')} / {ctx.control_plane.get('config_sync', {}).get('summary_label', '-')} / {ctx.control_plane.get('protocol_status', {}).get('summary_label', '-')}"),
            ("控制权", f"{ctx.control_authority.get('summary_label', '-')} / {ctx.control_authority.get('detail', '-')}"),
            ("桥接观测", f"{ctx.bridge_observability.get('summary_label', '-')} / {ctx.bridge_observability.get('freshness', {}).get('summary_label', '-')} / {ctx.bridge_observability.get('command_observability', {}).get('summary_label', '-')}"),
            ("当前压力", f"{metrics['pressure_current']:.2f} N / 目标 {metrics['pressure_target']:.2f} N"),
            ("接触状态", f"{metrics['contact_mode']} / 动作建议 {metrics.get('recommended_action', '-')}"),
            ("图像质量", f"{metrics['image_quality']:.2f} / 综合 {metrics.get('quality_score', 0.0):.2f}"),
            ("当前 Cobb角", f"{metrics['cobb_angle']:.1f}°"),
            ("定位策略", f"{ctx.workflow.get('localization', {}).get('implementation', '-')} / {ctx.workflow.get('localization', {}).get('state', '-')}"),
            ("路径策略", f"{ctx.workflow.get('scan_plan', {}).get('implementation', '-')} / {ctx.workflow.get('scan_plan', {}).get('state', '-')}"),
            ("安全判定", f"{'YES' if ctx.safety.get('safe_to_scan', False) else 'NO'} / 联锁 {', '.join(ctx.safety.get('active_interlocks', [])) or '-'}"),
        ]
        window.overview_page.recommended_label.setText(f"建议下一步：{ctx.recommended_label}")
        window.overview_page.readiness_label.setText(f"流程就绪度：{ctx.readiness.get('passed', 0)} / {ctx.readiness.get('total', 0)}，阻塞项 {total_blockers}")
        set_text_edit_html_preserve_scroll(window.overview_page.overview_text, html_summary(summary_lines))

    @staticmethod
    def _set_optional_text(window, attr_name: str, text: str) -> None:
        widget = getattr(window, attr_name, None)
        if widget is not None:
            widget.setText(text)
