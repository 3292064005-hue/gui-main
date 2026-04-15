from __future__ import annotations

from ipaddress import ip_address
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.robot_identity_service import RobotIdentity, RobotIdentityService
from spine_ultrasound_ui.utils.sdk_unit_contract import build_sdk_boundary_contract, extract_frame_translation_mm
from spine_ultrasound_ui.services.xmate_profile import XMateProfile, load_xmate_profile


class ClinicalConfigService:
    """Validate and normalize the desktop runtime config against the xMate mainline."""

    def __init__(self, profile: XMateProfile | None = None, identity_service: RobotIdentityService | None = None) -> None:
        self.profile = profile or load_xmate_profile()
        self.identity_service = identity_service or RobotIdentityService(self.profile.robot_model)
        self.identity = self.identity_service.resolve(
            self.profile.robot_model,
            self.profile.sdk_robot_class,
            self.profile.axis_count,
        )

    def apply_mainline_defaults(self, config: RuntimeConfig) -> RuntimeConfig:
        payload = config.to_dict()
        pressure_policy = dict(self.profile.contact_force_policy)
        legal_impedance = self._clip_vector(self.profile.cartesian_impedance, self.identity.cartesian_impedance_limits)
        legal_wrench = self._clip_vector(self.profile.desired_wrench_n, self.identity.desired_wrench_limits)
        payload.update(
            robot_model=self.identity.robot_model,
            sdk_robot_class=self.identity.sdk_robot_class,
            axis_count=self.identity.axis_count,
            remote_ip=self.profile.remote_ip,
            local_ip=self.profile.local_ip,
            preferred_link=self.identity.preferred_link,
            requires_single_control_source=self.identity.requires_single_control_source,
            rt_mode=self.identity.rt_mode,
            tool_name=self.profile.tool_name,
            tcp_name=self.profile.tcp_name,
            load_kg=self.profile.load_mass_kg,
            load_com_mm=list(self.profile.load_com_mm),
            load_inertia=list(self.profile.load_inertia),
            rt_network_tolerance_percent=max(self.identity.rt_network_tolerance_range[0], min(self.profile.rt_network_tolerance_percent, self.identity.rt_network_tolerance_range[1])),
            joint_filter_hz=self._clip_scalar(self.profile.joint_filter_hz, *self.identity.joint_filter_range_hz),
            cart_filter_hz=self._clip_scalar(self.profile.cart_filter_hz, *self.identity.joint_filter_range_hz),
            torque_filter_hz=self._clip_scalar(self.profile.torque_filter_hz, *self.identity.joint_filter_range_hz),
            collision_detection_enabled=self.profile.collision_detection_enabled,
            collision_sensitivity=self.profile.collision_sensitivity,
            collision_behavior=self.profile.collision_behavior,
            collision_fallback_mm=self.profile.collision_fallback_mm,
            soft_limit_enabled=self.profile.soft_limit_enabled,
            joint_soft_limit_margin_deg=self.profile.joint_soft_limit_margin_deg,
            singularity_avoidance_enabled=self.profile.singularity_avoidance_enabled,
            cartesian_impedance=legal_impedance,
            desired_wrench_n=legal_wrench,
            fc_frame_type=self.profile.fc_frame_type,
            fc_frame_matrix=list(self.profile.fc_frame_matrix),
            tcp_frame_matrix=list(self.profile.tcp_frame_matrix),
            strip_width_mm=self.profile.strip_width_mm,
            strip_overlap_mm=self.profile.strip_overlap_mm,
            pressure_target=float(pressure_policy.get("target_n", config.pressure_target)),
            pressure_upper=float(pressure_policy.get("warning_n", config.pressure_upper)),
            pressure_lower=max(1.0, float(pressure_policy.get("target_n", config.pressure_target)) - float(pressure_policy.get("settle_band_n", 1.0))),
            scan_speed_mm_s=self._preserve_positive_scalar(config.scan_speed_mm_s, float(self.profile.sweep_policy.get("scan_speed_mm_s", config.scan_speed_mm_s))),
            contact_seek_speed_mm_s=self._preserve_positive_scalar(config.contact_seek_speed_mm_s, float(self.profile.sweep_policy.get("contact_seek_speed_mm_s", config.contact_seek_speed_mm_s))),
            retreat_speed_mm_s=self._preserve_positive_scalar(config.retreat_speed_mm_s, float(self.profile.sweep_policy.get("retreat_speed_mm_s", config.retreat_speed_mm_s))),
            image_quality_threshold=self._preserve_bounded_scalar(config.image_quality_threshold, float(self.profile.sweep_policy.get("rescan_quality_threshold", config.image_quality_threshold)), lower=0.0, upper=1.0),
            rt_stale_state_timeout_ms=self.profile.rt_stale_state_timeout_ms,
            rt_phase_transition_debounce_cycles=self.profile.rt_phase_transition_debounce_cycles,
            rt_max_cart_step_mm=self.profile.rt_max_cart_step_mm,
            rt_max_cart_vel_mm_s=self.profile.rt_max_cart_vel_mm_s,
            rt_max_cart_acc_mm_s2=self.profile.rt_max_cart_acc_mm_s2,
            rt_max_pose_trim_deg=self.profile.rt_max_pose_trim_deg,
            rt_max_force_error_n=self.profile.rt_max_force_error_n,
            rt_integrator_limit_n=self.profile.rt_integrator_limit_n,
            contact_force_target_n=self.profile.contact_force_target_n,
            contact_force_tolerance_n=self.profile.contact_force_tolerance_n,
            contact_establish_cycles=self.profile.contact_establish_cycles,
            normal_admittance_gain=self.profile.normal_admittance_gain,
            normal_damping_gain=self.profile.normal_damping_gain,
            seek_contact_max_step_mm=self.profile.seek_contact_max_step_mm,
            normal_velocity_quiet_threshold_mm_s=self.profile.normal_velocity_quiet_threshold_mm_s,
            scan_force_target_n=self.profile.scan_force_target_n,
            scan_force_tolerance_n=self.profile.scan_force_tolerance_n,
            scan_normal_pi_kp=self.profile.scan_normal_pi_kp,
            scan_normal_pi_ki=self.profile.scan_normal_pi_ki,
            scan_tangent_speed_min_mm_s=self.profile.scan_tangent_speed_min_mm_s,
            scan_tangent_speed_max_mm_s=self.profile.scan_tangent_speed_max_mm_s,
            scan_pose_trim_gain=self.profile.scan_pose_trim_gain,
            scan_follow_enable_lateral_modulation=self.profile.scan_follow_enable_lateral_modulation,
            pause_hold_position_guard_mm=self.profile.pause_hold_position_guard_mm,
            pause_hold_force_guard_n=self.profile.pause_hold_force_guard_n,
            pause_hold_drift_kp=self.profile.pause_hold_drift_kp,
            pause_hold_drift_ki=self.profile.pause_hold_drift_ki,
            pause_hold_integrator_leak=self.profile.pause_hold_integrator_leak,
            retract_release_force_n=self.profile.retract_release_force_n,
            retract_release_cycles=self.profile.retract_release_cycles,
            retract_safe_gap_mm=self.profile.retract_safe_gap_mm,
            retract_max_travel_mm=self.profile.retract_max_travel_mm,
            retract_jerk_limit_mm_s3=self.profile.retract_jerk_limit_mm_s3,
            retract_timeout_ms=self.profile.retract_timeout_ms,
        )
        return RuntimeConfig.from_dict(payload)

    def build_report(self, config: RuntimeConfig) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        checks.append(self._check(
            "机器人身份",
            config.robot_model == self.identity.robot_model and config.sdk_robot_class == self.identity.sdk_robot_class and int(config.axis_count) == int(self.identity.axis_count),
            "blocker",
            f"当前身份 {config.robot_model}/{config.sdk_robot_class}/{config.axis_count} 轴 与官方主线一致。",
            f"当前身份 {config.robot_model}/{config.sdk_robot_class}/{config.axis_count} 轴，不符合官方主线 {self.identity.robot_model}/{self.identity.sdk_robot_class}/{self.identity.axis_count} 轴。",
        ))
        checks.append(self._check(
            "压力工作带",
            config.pressure_lower < config.pressure_target < config.pressure_upper,
            "blocker",
            f"pressure_lower={config.pressure_lower:.2f} < target={config.pressure_target:.2f} < upper={config.pressure_upper:.2f}",
            "压力上下限与目标压力顺序错误，正式流程会导致接触控制策略失真。",
        ))
        checks.append(self._check(
            "条带宽度/重叠",
            config.strip_width_mm > 0 and 0 <= config.strip_overlap_mm < config.strip_width_mm,
            "blocker",
            f"strip_width={config.strip_width_mm:.1f} mm, overlap={config.strip_overlap_mm:.1f} mm",
            "strip_overlap 必须非负且小于 strip_width，否则路径密度与覆盖率计算会失真。",
        ))
        checks.append(self._check(
            "速度关系",
            config.contact_seek_speed_mm_s > 0 and config.scan_speed_mm_s > 0 and config.retreat_speed_mm_s > 0 and config.contact_seek_speed_mm_s <= config.scan_speed_mm_s <= config.retreat_speed_mm_s,
            "warning",
            f"seek={config.contact_seek_speed_mm_s:.1f}, scan={config.scan_speed_mm_s:.1f}, retreat={config.retreat_speed_mm_s:.1f} mm/s",
            "推荐满足 seek <= scan <= retreat，避免接触搜索过快或退让过慢。",
        ))
        checks.append(self._check(
            "遥测与超时",
            config.telemetry_rate_hz > 0 and config.network_stale_ms > 0 and config.pressure_stale_ms > 0,
            "blocker",
            f"telemetry_rate_hz={config.telemetry_rate_hz}, network_stale_ms={config.network_stale_ms}, pressure_stale_ms={config.pressure_stale_ms}",
            "telemetry_rate_hz / network_stale_ms / pressure_stale_ms 必须为正值。",
        ))
        checks.append(self._check(
            "IP 格式",
            self._valid_ip(config.remote_ip) and self._valid_ip(config.local_ip),
            "blocker",
            f"remote={config.remote_ip}, local={config.local_ip}",
            "remote_ip 或 local_ip 不是合法 IPv4 地址。",
        ))
        checks.append(self._check(
            "阻抗/期望力维度",
            len(config.cartesian_impedance) == 6 and len(config.desired_wrench_n) == 6,
            "blocker",
            "cartesian_impedance / desired_wrench_n 均为 6 维。",
            "cartesian_impedance 和 desired_wrench_n 都必须是 6 维向量。",
        ))
        checks.append(self._vector_limit_check(
            "笛卡尔阻抗官方上限",
            config.cartesian_impedance,
            self.identity.cartesian_impedance_limits,
            severity="blocker",
            unit="N/m,Nm/rad",
        ))
        checks.append(self._vector_limit_check(
            "末端期望力官方上限",
            config.desired_wrench_n,
            self.identity.desired_wrench_limits,
            severity="blocker",
            unit="N,Nm",
        ))
        checks.append(self._check(
            "坐标矩阵维度",
            len(config.fc_frame_matrix) == 16 and len(config.tcp_frame_matrix) == 16,
            "blocker",
            "fc_frame_matrix / tcp_frame_matrix 均为 4x4 展平矩阵。",
            "fc_frame_matrix 或 tcp_frame_matrix 不是 16 维齐次矩阵。",
        ))
        unit_contract = build_sdk_boundary_contract(
            fc_frame_matrix=config.fc_frame_matrix,
            tcp_frame_matrix=config.tcp_frame_matrix,
            load_com_mm=config.load_com_mm,
        )
        tcp_translation_mm = extract_frame_translation_mm(config.tcp_frame_matrix)
        checks.append(self._check(
            "SDK 边界单位契约",
            unit_contract["sdk_length_unit"] == "m" and unit_contract["ui_length_unit"] == "mm",
            "blocker",
            "桌面规划保持 mm，SDK 边界统一换算到 m。",
            "单位契约异常：桌面/UI 与 SDK 边界单位未固定为 mm→m。",
        ))
        checks.append(self._check(
            "TCP 平移量",
            len(tcp_translation_mm) == 3 and max(abs(value) for value in tcp_translation_mm) <= 250.0,
            "warning",
            f"tcp translation={tcp_translation_mm} mm，仍在探头/TCP 常见量级内。",
            f"tcp translation={tcp_translation_mm} mm，疑似配置错误或量纲混淆。",
        ))
        checks.append(self._check(
            "负载参数维度",
            len(config.load_com_mm) == 3 and len(config.load_inertia) == 6 and config.load_kg > 0,
            "blocker",
            f"load={config.load_kg:.2f} kg, com={config.load_com_mm}, inertia={config.load_inertia}",
            "负载质量必须大于 0，load_com_mm 必须 3 维，load_inertia 必须 6 维。",
        ))
        checks.append(self._check(
            "滤波截止频率官方范围",
            self._in_range(config.joint_filter_hz, *self.identity.joint_filter_range_hz)
            and self._in_range(config.cart_filter_hz, *self.identity.joint_filter_range_hz)
            and self._in_range(config.torque_filter_hz, *self.identity.joint_filter_range_hz),
            "blocker",
            f"filters=({config.joint_filter_hz}, {config.cart_filter_hz}, {config.torque_filter_hz}) Hz",
            f"滤波截止频率必须落在 {self.identity.joint_filter_range_hz[0]}~{self.identity.joint_filter_range_hz[1]} Hz。",
        ))
        checks.append(self._check(
            "RT 网络阈值官方范围",
            self._in_range(int(config.rt_network_tolerance_percent), *self.identity.rt_network_tolerance_range),
            "blocker",
            f"rt_network_tolerance_percent={config.rt_network_tolerance_percent}",
            f"RT 网络阈值必须落在 {self.identity.rt_network_tolerance_range[0]}~{self.identity.rt_network_tolerance_range[1]}。",
        ))
        checks.append(self._check(
            "RT 网络阈值建议区间",
            self._in_range(int(config.rt_network_tolerance_percent), *self.identity.rt_network_tolerance_recommended),
            "warning",
            f"rt_network_tolerance_percent={config.rt_network_tolerance_percent}，落在建议 {self.identity.rt_network_tolerance_recommended[0]}~{self.identity.rt_network_tolerance_recommended[1]}。",
            f"rt_network_tolerance_percent={config.rt_network_tolerance_percent}，建议调整到 {self.identity.rt_network_tolerance_recommended[0]}~{self.identity.rt_network_tolerance_recommended[1]}。",
        ))
        checks.append(self._check(
            "主线配置贴合度",
            config.rt_mode == self.identity.rt_mode and config.preferred_link == self.identity.preferred_link and bool(config.requires_single_control_source),
            "blocker",
            f"rt_mode={config.rt_mode}, link={config.preferred_link}, single_source={config.requires_single_control_source}",
            "当前配置与 xMate 主线基线存在偏差，必须应用主线基线后才能继续。",
        ))
        checks.append(self._check(
            "工具/TCP 命名",
            bool(config.tool_name.strip()) and bool(config.tcp_name.strip()),
            "blocker",
            f"tool={config.tool_name}, tcp={config.tcp_name}",
            "tool_name / tcp_name 不能为空。",
        ))
        blockers = [item for item in checks if item["severity"] == "blocker" and not item["ok"]]
        warnings = [item for item in checks if item["severity"] == "warning" and not item["ok"]]
        summary_state = "aligned"
        if blockers:
            summary_state = "blocked"
        elif warnings:
            summary_state = "warning"
        return {
            "summary_state": summary_state,
            "summary_label": {
                "aligned": "配置基线通过",
                "warning": "配置基线告警",
                "blocked": "配置基线阻塞",
            }.get(summary_state, "配置状态未知"),
            "checks": checks,
            "blockers": blockers,
            "warnings": warnings,
            "profile_robot_model": self.profile.robot_model,
            "profile_sdk_robot_class": self.profile.sdk_robot_class,
            "resolved_identity": self.identity.to_dict(),
            "recommended_patch": self._recommended_patch(config),
            "baseline_summary": {
                "rt_mode": self.identity.rt_mode,
                "preferred_link": self.identity.preferred_link,
                "tool_name": self.profile.tool_name,
                "tcp_name": self.profile.tcp_name,
                "target_force_n": self.profile.contact_force_policy.get("target_n", 0.0),
                "warning_force_n": self.profile.contact_force_policy.get("warning_n", 0.0),
                "cartesian_impedance_limits": list(self.identity.cartesian_impedance_limits),
                "desired_wrench_limits": list(self.identity.desired_wrench_limits),
                "sdk_boundary_units": build_sdk_boundary_contract(
                    fc_frame_matrix=config.fc_frame_matrix,
                    tcp_frame_matrix=config.tcp_frame_matrix,
                    load_com_mm=config.load_com_mm,
                ),
            },
        }

    def _recommended_patch(self, config: RuntimeConfig) -> list[dict[str, Any]]:
        patch: list[dict[str, Any]] = []
        expected = {
            "robot_model": self.identity.robot_model,
            "sdk_robot_class": self.identity.sdk_robot_class,
            "axis_count": self.identity.axis_count,
            "remote_ip": self.profile.remote_ip,
            "preferred_link": self.identity.preferred_link,
            "rt_mode": self.identity.rt_mode,
            "requires_single_control_source": self.identity.requires_single_control_source,
            "tool_name": self.profile.tool_name,
            "tcp_name": self.profile.tcp_name,
            "rt_network_tolerance_percent": self.profile.rt_network_tolerance_percent,
            "cartesian_impedance": self._clip_vector(config.cartesian_impedance, self.identity.cartesian_impedance_limits),
            "desired_wrench_n": self._clip_vector(config.desired_wrench_n, self.identity.desired_wrench_limits),
        }
        current = config.to_dict()
        for key, value in expected.items():
            if current.get(key) != value:
                patch.append({"field": key, "current": current.get(key), "expected": value})
        return patch

    @staticmethod
    def _check(name: str, ok: bool, severity: str, detail_ok: str, detail_bad: str) -> dict[str, Any]:
        return {"name": name, "ok": bool(ok), "severity": severity, "detail": detail_ok if ok else detail_bad}


    @staticmethod
    def _preserve_positive_scalar(value: float, fallback: float) -> float:
        candidate = float(value)
        if candidate > 0:
            return candidate
        return float(fallback)

    @staticmethod
    def _preserve_bounded_scalar(value: float, fallback: float, *, lower: float, upper: float) -> float:
        candidate = float(value)
        if lower <= candidate <= upper:
            return candidate
        return max(lower, min(float(fallback), upper))

    @staticmethod
    def _valid_ip(value: str) -> bool:
        try:
            ip_address(str(value))
        except ValueError:
            return False
        return True

    @staticmethod
    def _clip_scalar(value: float, lower: float, upper: float) -> float:
        return max(lower, min(float(value), upper))

    @staticmethod
    def _clip_vector(values: list[float], limits: tuple[float, ...]) -> list[float]:
        payload = [float(values[idx]) if idx < len(values) else 0.0 for idx in range(len(limits))]
        return [max(-limit, min(payload[idx], limit)) for idx, limit in enumerate(limits)]

    @staticmethod
    def _in_range(value: float | int, lower: float | int, upper: float | int) -> bool:
        return float(lower) <= float(value) <= float(upper)

    @staticmethod
    def _vector_limit_check(name: str, values: list[float], limits: tuple[float, ...], *, severity: str, unit: str) -> dict[str, Any]:
        ok = len(values) == len(limits) and all(abs(float(value)) <= float(limits[idx]) for idx, value in enumerate(values[: len(limits)]))
        return {
            "name": name,
            "ok": ok,
            "severity": severity,
            "detail": (
                f"当前值 {list(values)} 在官方上限 {list(limits)} ({unit}) 内。"
                if ok
                else f"当前值 {list(values)} 超出官方上限 {list(limits)} ({unit})。"
            ),
        }
