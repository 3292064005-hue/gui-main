from __future__ import annotations

from .common import StatusViewContext


class ExecutionPresenter:
    def apply(self, ctx: StatusViewContext) -> None:
        window = ctx.window
        metrics = ctx.metrics
        pose = ctx.pose
        pose_text = f"x={pose['x']:.1f}, y={pose['y']:.1f}, z={pose['z']:.1f}, rx={pose['rx']:.1f}, ry={pose['ry']:.1f}, rz={pose['rz']:.1f}"
        window.scan_page.lbl_segment.setText(str(metrics["segment_id"]))
        window.scan_page.lbl_path_idx.setText(str(metrics["path_index"]))
        window.scan_page.lbl_frame_id.setText(str(metrics["frame_id"]))
        window.scan_page.progress.setValue(int(metrics["scan_progress"]))
        window.scan_page.lbl_pressure_current.setText(f"{metrics['pressure_current']:.2f} N")
        window.scan_page.lbl_pressure_target.setText(f"{metrics['pressure_target']:.2f} N")
        window.scan_page.lbl_contact_mode.setText(metrics["contact_mode"])
        window.scan_page.lbl_contact_conf.setText(f"{metrics['contact_confidence']:.2f}")
        window.scan_page.lbl_pose.setText(pose_text)

        assessment_text = (
            f"评估状态：{ctx.system_state}\n"
            f"Cobb 角：{metrics['cobb_angle']:.1f}°\n"
            f"特征置信度：{metrics['feature_confidence']:.2f}\n"
            f"综合质量：{metrics.get('quality_score', 0.0):.2f}\n"
            f"建议动作：{metrics.get('recommended_action', '-')}\n"
            f"导出条件：{'已满足' if ctx.payload.get('permissions', {}).get('export_summary') else '未满足'}"
        )
        window.assessment_page.lbl_cobb.setText(f"{metrics['cobb_angle']:.1f}°")
        window.assessment_page.lbl_feature_conf.setText(f"{metrics['feature_confidence']:.2f}")
        window.assessment_page.lbl_quality_score.setText(f"{metrics.get('quality_score', metrics['image_quality']):.2f}")
        window.assessment_page.lbl_assessment_state.setText(ctx.system_state)
        window.assessment_page.assessment_text.setPlainText(assessment_text)
