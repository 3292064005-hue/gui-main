from __future__ import annotations

from ipaddress import IPv4Address
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.robot_identity_service import RobotIdentityService
from spine_ultrasound_ui.services.xmate_profile import XMateProfile, load_xmate_profile


class SdkCapabilityService:
    """Build an SDK-aligned capability and preflight view for the desktop."""

    def __init__(self, profile: XMateProfile | None = None, identity_service: RobotIdentityService | None = None) -> None:
        self.profile = profile or load_xmate_profile()
        self.identity_service = identity_service or RobotIdentityService(self.profile.robot_model)
        self.identity = self.identity_service.resolve(self.profile.robot_model, self.profile.sdk_robot_class, self.profile.axis_count)

    def build(self, config: RuntimeConfig, robot_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        robot = dict(robot_snapshot or {})
        identity = self.identity_service.resolve(config.robot_model, config.sdk_robot_class, config.axis_count)
        modules = self._module_matrix(config, identity)
        live_binding = bool(robot.get("live_binding_established", False))
        for item in modules:
            item.setdefault("supported_by_vendor_sdk", True)
            item.setdefault("implemented_in_runtime", item.get("status") != "unsupported")
            item.setdefault("live_binding_established", live_binding and item.get("module") in {"rokae::Robot", "rokae::RtMotionControl", "rokae::xMateModel", "通信 I/O", "RL 工程", "协作功能"})
        checks = self._preflight_checks(config, robot, identity)
        blockers = [item for item in checks if item["severity"] == "blocker" and not item["ok"]]
        warnings = [item for item in checks if item["severity"] == "warning" and not item["ok"]]
        enabled_modules = sum(1 for item in modules if item["enabled"])
        summary_state = "aligned"
        if blockers:
            summary_state = "blocked"
        elif warnings:
            summary_state = "warning"
        return {
            "summary_state": summary_state,
            "summary_label": self._summary_label(summary_state),
            "sdk_family": "ROKAE xCore SDK (C++)",
            "controller_version": identity.controller_version,
            "robot_model": identity.robot_model,
            "sdk_robot_class": identity.sdk_robot_class,
            "remote_ip": config.remote_ip,
            "local_ip": config.local_ip,
            "preferred_link": config.preferred_link,
            "rt_loop_hz": self.profile.rt_loop_hz,
            "scan_rt_mode": config.rt_mode,
            "live_binding_established": live_binding,
            "feature_coverage": {
                "enabled_modules": enabled_modules,
                "total_modules": len(modules),
                "coverage_percent": int(round((enabled_modules / len(modules)) * 100)) if modules else 0,
            },
            "checks": checks,
            "blockers": blockers,
            "warnings": warnings,
            "modules": modules,
            "command_bindings": self._command_bindings(config, identity),
            "resolved_identity": identity.to_dict(),
            "mainline_sequence": [
                "connectToRobot(remoteIP, localIP)",
                "setPowerState(on)",
                "setOperateMode(auto)",
                "setMotionControlMode(NRT)",
                "moveReset()",
                "MoveAbsJ / MoveJ / MoveL 接近",
                "setMotionControlMode(RT)",
                "startReceiveRobotState(1ms, fields)",
                "setCartesianImpedance / setLoad / setEndEffectorFrame",
                "startMove(cartesianImpedance)",
                "setControlLoop() + startLoop()",
            ],
            "realtime_notes": [
                "实时主线由 C++ 以 1 kHz 执行，UI 不进入 RT 回调。",
                "在回调中读状态时，应将状态发送周期与控制周期都保持在 1 ms。",
                "进入 RT 前必须先完成网络阈值、滤波、TCP、负载与阻抗参数设置。",
            ],
            "clinical_policy": {
                "mainline_scan_mode": identity.rt_mode,
                "direct_torque_allowed": False,
                "single_control_source_required": identity.requires_single_control_source,
                "collision_detection_required": True,
                "soft_limit_required": True,
                "singularity_avoidance_recommended": True,
            },
            "safety_contract": {
                "collision_detection_enabled": config.collision_detection_enabled,
                "collision_sensitivity": config.collision_sensitivity,
                "collision_behavior": config.collision_behavior,
                "collision_fallback_mm": config.collision_fallback_mm,
                "soft_limit_enabled": config.soft_limit_enabled,
                "joint_soft_limit_margin_deg": config.joint_soft_limit_margin_deg,
                "singularity_avoidance_enabled": config.singularity_avoidance_enabled,
            },
        }

    def _module_matrix(self, config: RuntimeConfig, identity) -> list[dict[str, Any]]:
        scan_mode_ok = config.rt_mode == identity.rt_mode
        direct_torque_selected = config.rt_mode == "directTorque"
        return [
            {
                "module": "rokae::Robot",
                "enabled": True,
                "status": "ready",
                "purpose": "连接、上电、模式切换、姿态/关节/日志/工具工件查询",
                "core_methods": [
                    "connectToRobot",
                    "setPowerState",
                    "setOperateMode",
                    "robotInfo",
                    "jointPos",
                    "posture",
                    "queryControllerLog",
                    "setToolset",
                ],
            },
            {
                "module": "rokae::RtMotionControl",
                "enabled": scan_mode_ok and not direct_torque_selected,
                "status": "ready" if scan_mode_ok and not direct_torque_selected else "policy_blocked",
                "purpose": "1 kHz 实时阻抗/位置控制主线",
                "core_methods": [
                    "startReceiveRobotState",
                    "setControlLoop",
                    "startLoop",
                    "startMove",
                    "setCartesianImpedance",
                    "setRtNetworkTolerance",
                ],
            },
            {
                "module": "rokae::Planner",
                "enabled": identity.supports_planner,
                "status": "ready" if identity.supports_planner else "unsupported",
                "purpose": "S 曲线/点位跟随的上位机路径规划",
                "core_methods": ["JointMotionGenerator", "CartMotionGenerator", "FollowPosition"],
            },
            {
                "module": "rokae::xMateModel",
                "enabled": identity.supports_xmate_model,
                "status": "ready" if identity.supports_xmate_model else "unsupported",
                "purpose": "正逆解、雅可比、动力学前向计算",
                "core_methods": ["robot.model()", "getCartPose", "getJointPos", "jacobian", "getTorque"],
            },
            {
                "module": "通信 I/O",
                "enabled": True,
                "status": "ready",
                "purpose": "DI/DO/AI/AO、寄存器、xPanel 供电配置",
                "core_methods": ["getDI", "setDO", "getAI", "setAO", "readRegister", "writeRegister"],
            },
            {
                "module": "RL 工程",
                "enabled": True,
                "status": "ready",
                "purpose": "projectsInfo / loadProject / runProject / pauseProject",
                "core_methods": ["projectsInfo", "loadProject", "runProject", "pauseProject"],
            },
            {
                "module": "协作功能",
                "enabled": identity.supports_drag or identity.supports_path_replay,
                "status": "ready" if identity.supports_drag or identity.supports_path_replay else "unsupported",
                "purpose": "拖动示教、路径录制/回放、奇异规避",
                "core_methods": ["enableDrag", "startRecordPath", "replayPath", "queryPathLists", "setAvoidSingularity"],
            },
        ]

    def _preflight_checks(self, config: RuntimeConfig, robot_snapshot: dict[str, Any], identity) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        checks.append(self._check(
            name="机器人类匹配",
            ok=config.sdk_robot_class == identity.sdk_robot_class and int(config.axis_count) == int(identity.axis_count),
            severity="blocker",
            detail_ok=f"当前为 {config.sdk_robot_class}/{config.axis_count} 轴，符合 {identity.robot_model} 主线。",
            detail_bad=f"当前配置为 {config.sdk_robot_class}/{config.axis_count} 轴，主线期望 {identity.sdk_robot_class}/{identity.axis_count} 轴。",
        ))
        checks.append(self._check(
            name="实时扫描模式",
            ok=config.rt_mode == identity.rt_mode,
            severity="blocker",
            detail_ok=f"临床主线扫描模式为 {config.rt_mode}。",
            detail_bad=f"当前 rt_mode={config.rt_mode}，主线要求 {identity.rt_mode}。",
        ))
        checks.append(self._check(
            name="RT 模式受支持",
            ok=config.rt_mode in set(identity.supported_rt_modes),
            severity="blocker",
            detail_ok=f"{config.rt_mode} 在 {identity.label} RT 能力矩阵中。",
            detail_bad=f"{config.rt_mode} 不在 {identity.label} 官方 RT 能力矩阵中。",
        ))
        checks.append(self._check(
            name="直接力矩控制",
            ok=config.rt_mode != "directTorque",
            severity="blocker",
            detail_ok="临床主线未启用 directTorque。",
            detail_bad="临床主线禁止 directTorque，应保留给研究模式。",
        ))
        checks.append(self._check(
            name="远端/本机 IP",
            ok=bool(config.remote_ip and config.local_ip),
            severity="blocker",
            detail_ok=f"remote={config.remote_ip}, local={config.local_ip}",
            detail_bad="connectToRobot(remoteIP, localIP) 所需 IP 未配置完整。",
        ))
        checks.append(self._check(
            name="直连网段一致性",
            ok=self._same_subnet(config.remote_ip, config.local_ip),
            severity="warning",
            detail_ok="远端/本机 IP 位于同一 /24 网段。",
            detail_bad=f"remote={config.remote_ip}, local={config.local_ip} 看起来不在同一 /24 网段。",
        ))
        checks.append(self._check(
            name="连接方式",
            ok=config.preferred_link == identity.preferred_link,
            severity="blocker",
            detail_ok=f"当前使用 {config.preferred_link}，符合实时控制推荐链路。",
            detail_bad=f"当前 preferred_link={config.preferred_link}，实时主线推荐 {identity.preferred_link}。",
        ))
        checks.append(self._check(
            name="单控制源",
            ok=bool(config.requires_single_control_source),
            severity="blocker",
            detail_ok="当前配置要求单控制源。",
            detail_bad="当前未锁定单控制源，容易与 RobotAssist/其他客户端发生控制冲突。",
        ))
        checks.append(self._check(
            name="工具/TCP/载荷",
            ok=bool(config.tool_name and config.tcp_name and float(config.load_kg) > 0.0),
            severity="blocker",
            detail_ok=f"tool={config.tool_name}, tcp={config.tcp_name}, load={config.load_kg:.2f}kg",
            detail_bad="工具名、TCP 名或载荷质量未配置完整。",
        ))
        checks.append(self._check(
            name="网络容忍阈值",
            ok=identity.rt_network_tolerance_recommended[0] <= int(config.rt_network_tolerance_percent) <= identity.rt_network_tolerance_recommended[1],
            severity="warning",
            detail_ok=f"rt_network_tolerance_percent={config.rt_network_tolerance_percent}，落在手册建议 {identity.rt_network_tolerance_recommended[0]}~{identity.rt_network_tolerance_recommended[1]} 范围。",
            detail_bad=f"rt_network_tolerance_percent={config.rt_network_tolerance_percent}，手册对不稳定排查建议 {identity.rt_network_tolerance_recommended[0]}~{identity.rt_network_tolerance_recommended[1]}。",
        ))
        checks.append(self._check(
            name="笛卡尔阻抗官方上限",
            ok=len(config.cartesian_impedance) == len(identity.cartesian_impedance_limits) and all(abs(float(value)) <= identity.cartesian_impedance_limits[idx] for idx, value in enumerate(config.cartesian_impedance[: len(identity.cartesian_impedance_limits)])),
            severity="blocker",
            detail_ok=f"cartesian_impedance={config.cartesian_impedance} 在官方上限内。",
            detail_bad=f"cartesian_impedance={config.cartesian_impedance} 超出官方上限 {list(identity.cartesian_impedance_limits)}。",
        ))
        checks.append(self._check(
            name="末端期望力官方上限",
            ok=len(config.desired_wrench_n) == len(identity.desired_wrench_limits) and all(abs(float(value)) <= identity.desired_wrench_limits[idx] for idx, value in enumerate(config.desired_wrench_n[: len(identity.desired_wrench_limits)])),
            severity="blocker",
            detail_ok=f"desired_wrench_n={config.desired_wrench_n} 在官方上限内。",
            detail_bad=f"desired_wrench_n={config.desired_wrench_n} 超出官方上限 {list(identity.desired_wrench_limits)}。",
        ))
        checks.append(self._check(
            name="碰撞检测",
            ok=bool(config.collision_detection_enabled),
            severity="blocker",
            detail_ok=f"碰撞检测已开启，灵敏度={config.collision_sensitivity}，回退={config.collision_fallback_mm:.1f} mm。",
            detail_bad="当前未开启碰撞检测，正式主线不应继续。",
        ))
        checks.append(self._check(
            name="软限位",
            ok=bool(config.soft_limit_enabled),
            severity="blocker",
            detail_ok=f"软限位已开启，裕量={config.joint_soft_limit_margin_deg:.1f}°。",
            detail_bad="当前未开启软限位，正式主线不应继续。",
        ))
        checks.append(self._check(
            name="奇异规避",
            ok=bool(config.singularity_avoidance_enabled),
            severity="warning",
            detail_ok="奇异规避已开启。",
            detail_bad="当前未开启奇异规避，笛卡尔扫描主线存在姿态奇异风险。",
        ))
        checks.append(self._check(
            name="RL 主工程命名",
            ok=bool(config.rl_project_name and config.rl_task_name),
            severity="warning",
            detail_ok=f"RL project={config.rl_project_name}, task={config.rl_task_name}",
            detail_bad="未填写 RL 工程/任务名，RL 面板只能做只读展示。",
        ))
        checks.append(self._check(
            name="机器人已进入自动模式",
            ok=str(robot_snapshot.get("operate_mode", "")).lower() in {"automatic", "auto"} or not robot_snapshot,
            severity="warning",
            detail_ok="当前 operate_mode 已是自动。",
            detail_bad=f"当前 operate_mode={robot_snapshot.get('operate_mode', '-') }，正式主线应在自动模式下运行。",
        ))
        return checks

    def _command_bindings(self, config: RuntimeConfig, identity) -> list[dict[str, Any]]:
        return [
            {"ui_action": "连接机器人", "sdk_binding": f"{identity.sdk_robot_class}.connectToRobot({config.remote_ip}, {config.local_ip})", "plane": "base", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "系统上电", "sdk_binding": "setPowerState(on)", "plane": "base", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "自动模式", "sdk_binding": "setOperateMode(auto)", "plane": "base", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "预接近", "sdk_binding": "setMotionControlMode(NRT) + moveReset + MoveAbsJ/MoveL", "plane": "nrt", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "实时接触", "sdk_binding": "setMotionControlMode(RT) + getRtMotionController + startMove(cartesianImpedance)", "plane": "rt", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "实时扫查", "sdk_binding": "startReceiveRobotState + setCartesianImpedance + setControlLoop + startLoop", "plane": "rt", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "安全退让", "sdk_binding": "stopMove / MoveL retract / emergency_stop", "plane": "safety", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "控制器日志", "sdk_binding": "queryControllerLog(count, level)", "plane": "observability", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "RL 工程", "sdk_binding": "projectsInfo / loadProject / runProject / pauseProject", "plane": "rl", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "路径回放 / 拖动", "sdk_binding": "queryPathLists / replayPath / enableDrag", "plane": "collaboration", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "通信 I/O", "sdk_binding": "getDI/DO/AI/AO + readRegister/writeRegister", "plane": "io", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "路径规划", "sdk_binding": "rokae::Planner (JointMotionGenerator / CartMotionGenerator)", "plane": "planning", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
            {"ui_action": "运动学动力学", "sdk_binding": "robot.model() + xMateModel", "plane": "model", "supported_by_vendor_sdk": True, "implemented_in_runtime": True},
        ]

    @staticmethod
    def _same_subnet(remote_ip: str, local_ip: str) -> bool:
        try:
            remote = int(IPv4Address(remote_ip))
            local = int(IPv4Address(local_ip))
        except Exception:
            return False
        mask = 0xFFFFFF00
        return (remote & mask) == (local & mask)

    @staticmethod
    def _check(*, name: str, ok: bool, severity: str, detail_ok: str, detail_bad: str) -> dict[str, Any]:
        return {
            "name": name,
            "ok": bool(ok),
            "severity": severity,
            "detail": detail_ok if ok else detail_bad,
        }

    @staticmethod
    def _summary_label(state: str) -> str:
        mapping = {
            "aligned": "SDK 主线对齐",
            "warning": "SDK 主线可运行但有风险",
            "blocked": "SDK 主线未对齐",
        }
        return mapping.get(state, "SDK 状态未知")
