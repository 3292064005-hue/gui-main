from __future__ import annotations

from .common import StatusViewContext, join_lines


class ReplayPresenter:
    def apply(self, ctx: StatusViewContext) -> None:
        window = ctx.window
        metrics = ctx.metrics
        window.replay_page.lbl_current.setText(f"当前实验：{ctx.exp_id} / 会话：{ctx.current_exp.get('session_id', '-') if ctx.current_exp else '-'}")
        replay_lines = [
            f"系统状态：{ctx.system_state}",
            f"扫描进度：{metrics['scan_progress']:.0f}%",
            f"当前段：{metrics['segment_id']} / 路径点：{metrics['path_index']}",
            f"记录状态：{'录制中' if ctx.recording.get('recording', False) else '未录制'}",
            f"最近建议：{ctx.recommended_label}",
            f"阻塞项：{'、'.join([item for item in (ctx.blockers + [b.get('name', '') for b in ctx.config_blockers] + [b.get('name', '') for b in ctx.session_blockers]) if item]) or '无'}",
            f"会话治理：{ctx.session_governance.get('summary_label', '-')}",
            f"控制权：{ctx.control_authority.get('summary_label', '-')}",
        ]
        window.replay_page.timeline.setPlainText("\n".join(replay_lines))

        plan_metrics = dict(ctx.model_report.get('plan_metrics', {}))
        selection = dict(ctx.model_report.get('execution_selection', {}))
        plan_lines = [
            f"路径状态：{ctx.workflow.get('scan_plan', {}).get('state', '-')}",
            f"路径实现：{ctx.workflow.get('scan_plan', {}).get('implementation', '-')}",
            f"预览 plan_id：{ctx.workflow.get('preview_plan_id', '-')}",
            f"预览 hash：{ctx.workflow.get('preview_plan_hash', '-')}",
            f"执行 profile：{selection.get('selected_profile', '-')}",
            f"候选数量：{selection.get('candidate_count', 0)}",
            f"segments：{plan_metrics.get('segment_count', 0)} / waypoints：{plan_metrics.get('total_waypoints', 0)}",
            f"估计时长：{plan_metrics.get('estimated_duration_ms', 0)} ms",
            f"扫描速度：{ctx.config.get('scan_speed_mm_s', '-')} mm/s / step={ctx.config.get('sample_step_mm', '-')} mm",
            f"strip={ctx.config.get('strip_width_mm', '-')} mm / overlap={ctx.config.get('strip_overlap_mm', '-')} mm",
        ]
        selected_score = selection.get('selected_score', {})
        if isinstance(selected_score, dict) and selected_score:
            plan_lines.append(f"选择评分：{selected_score}")
        window.vision_page.plan_view.setPlainText(join_lines(plan_lines, "暂无路径摘要。"))

        envelope = dict(ctx.model_report.get('envelope', {}))
        dh_params = list(ctx.model_report.get('dh_parameters', []))
        model_lines = [f"状态：{ctx.model_report.get('summary_label', '-')}", f"说明：{ctx.model_report.get('detail', '-')}", f"近似模型：{'YES' if ctx.model_report.get('approximate') else 'NO'}"]
        if envelope:
            model_lines.extend([f"包络 x=[{envelope.get('x_min', 0)}, {envelope.get('x_max', 0)}] mm", f"包络 y=[{envelope.get('y_min', 0)}, {envelope.get('y_max', 0)}] mm", f"包络 z=[{envelope.get('z_min', 0)}, {envelope.get('z_max', 0)}] mm", f"最大平移步进：{envelope.get('max_translation_step_mm', 0)} mm", f"最大姿态步进：{envelope.get('max_rotation_step_deg', 0)} °"])
        if ctx.model_report.get('checks'):
            model_lines.extend(["", "检查项:"])
            for item in ctx.model_report.get('checks', []):
                prefix = "OK" if item.get('ok') else ("BLOCK" if item.get('severity') == 'blocker' else "WARN")
                model_lines.append(f"[{prefix}] {item.get('name')}: {item.get('detail')}")
        if dh_params:
            model_lines.extend(["", "DH 参数(前 3 项):"])
            for item in dh_params[:3]:
                model_lines.append(f"J{item.get('joint')}: a={item.get('a_mm')} mm, alpha={item.get('alpha_rad')}, d={item.get('d_mm')} mm")
        window.vision_page.model_view.setPlainText(join_lines(model_lines, "暂无模型前检结果。"))
