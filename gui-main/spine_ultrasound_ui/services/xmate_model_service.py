from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan
from spine_ultrasound_ui.utils.sdk_unit_contract import build_sdk_boundary_contract
from spine_ultrasound_ui.services.xmate_profile import XMateProfile, load_xmate_profile
from spine_ultrasound_ui.utils.runtime_fingerprint import payload_hash


@dataclass
class PathEnvelope:
    x_min: float = 0.0
    x_max: float = 0.0
    y_min: float = 0.0
    y_max: float = 0.0
    z_min: float = 0.0
    z_max: float = 0.0
    max_translation_step_mm: float = 0.0
    max_rotation_step_deg: float = 0.0
    approach_jump_mm: float = 0.0
    retreat_jump_mm: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "x_min": round(self.x_min, 3),
            "x_max": round(self.x_max, 3),
            "y_min": round(self.y_min, 3),
            "y_max": round(self.y_max, 3),
            "z_min": round(self.z_min, 3),
            "z_max": round(self.z_max, 3),
            "max_translation_step_mm": round(self.max_translation_step_mm, 3),
            "max_rotation_step_deg": round(self.max_rotation_step_deg, 3),
            "approach_jump_mm": round(self.approach_jump_mm, 3),
            "retreat_jump_mm": round(self.retreat_jump_mm, 3),
        }


class XMateModelService:
    """Deterministic preflight model report for scan plans.

    This is intentionally conservative and approximate. It does not claim to
    replace `robot.model()` from the real xCore SDK C++ runtime. It provides a
    stable application-side contract so the desktop can surface FK/IK/Jacobian
    governance before real hardware integration is available.
    """

    def __init__(self, profile: XMateProfile | None = None) -> None:
        self.profile = profile or load_xmate_profile()
        self._report_cache: dict[str, dict[str, Any]] = {}

    def build_report(self, plan: ScanPlan | None, config: RuntimeConfig) -> dict[str, Any]:
        if plan is None or not plan.segments:
            return {
                "summary_state": "idle",
                "summary_label": "未生成路径",
                "detail": "当前还没有可供验证的预览或执行路径。",
                "warnings": [],
                "blockers": [],
                "approximate": True,
                "authority": "advisory_python",
                "sdk_boundary_units": build_sdk_boundary_contract(fc_frame_matrix=config.fc_frame_matrix, tcp_frame_matrix=config.tcp_frame_matrix, load_com_mm=config.load_com_mm),
                "envelope": {},
                "dh_parameters": [item.to_dict() for item in self.profile.dh_parameters],
            }
        cache_key = payload_hash({
            "plan_hash": plan.plan_hash(),
            "segments": len(plan.segments),
            "waypoints": sum(len(segment.waypoints) for segment in plan.segments),
            "rt_mode": config.rt_mode,
            "axis_count": config.axis_count,
            "sdk_robot_class": config.sdk_robot_class,
            "tcp_frame_matrix": list(config.tcp_frame_matrix),
            "load_com_mm": list(config.load_com_mm),
        })
        cached = self._report_cache.get(cache_key)
        if cached is not None:
            return dict(cached)
        envelope = self._compute_envelope(plan)
        checks = self._checks(plan, envelope, config)
        blockers = [item for item in checks if item["severity"] == "blocker" and not item["ok"]]
        warnings = [item for item in checks if item["severity"] == "warning" and not item["ok"]]
        state = "ready"
        if blockers:
            state = "blocked"
        elif warnings:
            state = "warning"
        validation_summary = dict(plan.validation_summary)
        planner_context = dict(validation_summary.get("planner_context", {}))
        execution_candidates = list(planner_context.get("execution_candidates", []))
        selection = dict(planner_context.get("selection_rationale", {}))
        report = {
            "summary_state": state,
            "summary_label": {
                "ready": "模型前检通过",
                "warning": "模型前检告警",
                "blocked": "模型前检阻塞",
            }.get(state, "模型状态未知"),
            "detail": self._detail(plan, envelope, blockers, warnings),
            "warnings": warnings,
            "blockers": blockers,
            "checks": checks,
            "approximate": True,
            "authority": "advisory_python",
            "sdk_boundary_units": build_sdk_boundary_contract(fc_frame_matrix=config.fc_frame_matrix, tcp_frame_matrix=config.tcp_frame_matrix, load_com_mm=config.load_com_mm),
            "model_contract": {
                "robot_model": self.profile.robot_model,
                "sdk_robot_class": self.profile.sdk_robot_class,
                "axis_count": self.profile.axis_count,
                "profile_rt_mode": self.profile.rt_mode,
                "supported_rt_modes": list(self.profile.supported_rt_modes),
                "planner_enabled": True,
                "xmate_model_enabled": True,
                "duplication_policy": "desktop_advisory_only__official_fk_ik_jacobian_torque_stay_in_sdk_runtime",
            },
            "envelope": envelope.to_dict(),
            "dh_parameters": [item.to_dict() for item in self.profile.dh_parameters],
            "plan_metrics": {
                "plan_id": plan.plan_id,
                "plan_kind": plan.plan_kind,
                "segment_count": len(plan.segments),
                "total_waypoints": sum(len(segment.waypoints) for segment in plan.segments),
                "estimated_duration_ms": int(validation_summary.get("estimated_duration_ms", 0) or 0),
                "surface_model_hash": plan.surface_model_hash,
                "registration_hash": plan.registration_hash,
            },
            "execution_selection": {
                "candidate_count": len(execution_candidates),
                "selected_profile": selection.get("selected_profile", validation_summary.get("execution_profile", "-")),
                "selected_candidate_id": selection.get("selected_candidate_id", plan.plan_id),
                "selected_score": selection.get("selected_score", dict(plan.score_summary)),
            },
        }
        self._report_cache[cache_key] = dict(report)
        if len(self._report_cache) > 16:
            self._report_cache.pop(next(iter(self._report_cache)))
        return report

    def _compute_envelope(self, plan: ScanPlan) -> PathEnvelope:
        points = [plan.approach_pose]
        scan_points = []
        for segment in plan.segments:
            points.extend(segment.waypoints)
            scan_points.extend(segment.waypoints)
        points.append(plan.retreat_pose)
        xs = [float(point.x) for point in points]
        ys = [float(point.y) for point in points]
        zs = [float(point.z) for point in points]
        max_translation = 0.0
        max_rotation = 0.0
        previous = None
        for point in scan_points:
            if previous is not None:
                max_translation = max(max_translation, math.dist((previous.x, previous.y, previous.z), (point.x, point.y, point.z)))
                rot_delta = math.sqrt((previous.rx - point.rx) ** 2 + (previous.ry - point.ry) ** 2 + (previous.rz - point.rz) ** 2)
                max_rotation = max(max_rotation, rot_delta)
            previous = point
        approach_jump = 0.0
        retreat_jump = 0.0
        if scan_points:
            first = scan_points[0]
            last = scan_points[-1]
            approach_jump = math.dist((plan.approach_pose.x, plan.approach_pose.y, plan.approach_pose.z), (first.x, first.y, first.z))
            retreat_jump = math.dist((last.x, last.y, last.z), (plan.retreat_pose.x, plan.retreat_pose.y, plan.retreat_pose.z))
        return PathEnvelope(
            x_min=min(xs),
            x_max=max(xs),
            y_min=min(ys),
            y_max=max(ys),
            z_min=min(zs),
            z_max=max(zs),
            max_translation_step_mm=max_translation,
            max_rotation_step_deg=max_rotation,
            approach_jump_mm=approach_jump,
            retreat_jump_mm=retreat_jump,
        )

    def _checks(self, plan: ScanPlan, envelope: PathEnvelope, config: RuntimeConfig) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        checks.append(self._check(
            "机器人类/轴数",
            config.sdk_robot_class == self.profile.sdk_robot_class and int(config.axis_count) == int(self.profile.axis_count),
            "blocker",
            f"{config.sdk_robot_class}/{config.axis_count} 轴与模型配置一致。",
            f"当前为 {config.sdk_robot_class}/{config.axis_count} 轴，模型配置期望 {self.profile.sdk_robot_class}/{self.profile.axis_count} 轴。",
        ))
        checks.append(self._check(
            "Z 清距",
            envelope.z_min >= max(150.0, self.profile.contact_guard_margin_mm),
            "blocker",
            f"最小 z={envelope.z_min:.1f} mm，仍在保守临床工作区内。",
            f"最小 z={envelope.z_min:.1f} mm，低于保守工作区阈值，需复查 approach/retreat 与贴合深度。",
        ))
        checks.append(self._check(
            "横向走廊宽度",
            (envelope.y_max - envelope.y_min) <= max(config.strip_width_mm * max(1, len(plan.segments)) + 20.0, 90.0),
            "warning",
            f"横向跨度 {(envelope.y_max - envelope.y_min):.1f} mm 在规划走廊预算内。",
            f"横向跨度 {(envelope.y_max - envelope.y_min):.1f} mm 偏大，建议复查 strip_width/overlap 与定位走廊。",
        ))
        checks.append(self._check(
            "步进连续性",
            envelope.max_translation_step_mm <= max(config.sample_step_mm * 30.0, 15.0),
            "warning",
            f"扫描段内最大平移步进 {envelope.max_translation_step_mm:.2f} mm，连续性正常。",
            f"扫描段内最大平移步进 {envelope.max_translation_step_mm:.2f} mm 偏大，建议重新做 S 曲线或 waypoint 稠密化。",
        ))
        checks.append(self._check(
            "进退场跳变",
            envelope.approach_jump_mm <= max(config.approach_clearance_mm if hasattr(config, "approach_clearance_mm") else 30.0, 60.0),
            "warning",
            f"approach={envelope.approach_jump_mm:.2f} mm，接近位到首个扫查点跨度可接受。",
            f"approach={envelope.approach_jump_mm:.2f} mm，建议复查接近位是否离首个扫查点过远。",
        ))
        checks.append(self._check(
            "姿态连续性",
            envelope.max_rotation_step_deg <= 8.0,
            "warning",
            f"最大姿态步进 {envelope.max_rotation_step_deg:.2f}°，未见明显突变。",
            f"最大姿态步进 {envelope.max_rotation_step_deg:.2f}° 偏大，建议复查姿态跟随与末端法向约束。",
        ))
        checks.append(self._check(
            "单位边界契约",
            build_sdk_boundary_contract(fc_frame_matrix=config.fc_frame_matrix, tcp_frame_matrix=config.tcp_frame_matrix, load_com_mm=config.load_com_mm)["sdk_length_unit"] == "m",
            "blocker",
            "模型前检遵守 UI(mm) → SDK(m) 边界换算。",
            "模型前检检测到单位边界合同丢失。",
        ))
        checks.append(self._check(
            "临床 RT 模式",
            config.rt_mode == self.profile.rt_mode,
            "blocker",
            f"当前 RT 模式为 {config.rt_mode}，符合主线。",
            f"当前 RT 模式为 {config.rt_mode}，模型主线要求 {self.profile.rt_mode}。",
        ))
        return checks

    @staticmethod
    def _check(name: str, ok: bool, severity: str, detail_ok: str, detail_bad: str) -> dict[str, Any]:
        return {
            "name": name,
            "ok": bool(ok),
            "severity": severity,
            "detail": detail_ok if ok else detail_bad,
        }

    @staticmethod
    def _detail(plan: ScanPlan, envelope: PathEnvelope, blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> str:
        if blockers:
            return f"路径 {plan.plan_id} 存在 {len(blockers)} 项阻塞，禁止进入正式执行。"
        if warnings:
            return f"路径 {plan.plan_id} 无硬阻塞，但有 {len(warnings)} 项模型告警。"
        return (
            f"路径 {plan.plan_id} 前检通过，x=[{envelope.x_min:.1f}, {envelope.x_max:.1f}] mm, "
            f"y=[{envelope.y_min:.1f}, {envelope.y_max:.1f}] mm, z=[{envelope.z_min:.1f}, {envelope.z_max:.1f}] mm。"
        )
