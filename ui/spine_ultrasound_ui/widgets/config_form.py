from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLineEdit, QPushButton

from spine_ultrasound_ui.models import RuntimeConfig


class ConfigForm(QGroupBox):
    config_applied = Signal(RuntimeConfig)

    def __init__(self, config: RuntimeConfig):
        super().__init__("参数配置")
        self._base_config = config
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 18, 14, 14)

        self.pressure_target = QLineEdit()
        self.pressure_upper = QLineEdit()
        self.pressure_lower = QLineEdit()
        self.scan_speed = QLineEdit()
        self.sample_step = QLineEdit()
        self.segment_length = QLineEdit()
        self.contact_seek_speed = QLineEdit()
        self.retreat_speed = QLineEdit()
        self.quality_threshold = QLineEdit()
        self.smoothing_factor = QLineEdit()
        self.feature_threshold = QLineEdit()
        self.network_stale_ms = QLineEdit()
        self.pressure_stale_ms = QLineEdit()
        self.telemetry_rate_hz = QLineEdit()
        self.tool_name = QLineEdit()
        self.tcp_name = QLineEdit()
        self.load_kg = QLineEdit()
        self.remote_ip = QLineEdit()
        self.local_ip = QLineEdit()
        self.rt_network_tolerance_percent = QLineEdit()
        self.joint_filter_hz = QLineEdit()
        self.cart_filter_hz = QLineEdit()
        self.torque_filter_hz = QLineEdit()
        self.collision_sensitivity = QLineEdit()
        self.collision_fallback_mm = QLineEdit()
        self.soft_limit_margin_deg = QLineEdit()
        self.rl_project_name = QLineEdit()
        self.rl_task_name = QLineEdit()

        self.roi_mode = QComboBox()
        self.roi_mode.addItems(["auto", "manual"])
        self.rt_mode = QComboBox()
        self.rt_mode.addItems(["cartesianImpedance", "jointImpedance", "cartesianPosition", "jointPosition", "directTorque"])
        self.preferred_link = QComboBox()
        self.preferred_link.addItems(["wired_direct"])
        self.robot_model = QComboBox()
        self.robot_model.addItems(["xmate3"])
        self.sdk_robot_class = QComboBox()
        self.sdk_robot_class.addItems(["xMateRobot"])
        self.axis_count = QComboBox()
        self.axis_count.addItems(["6"])
        self.requires_single_control_source = QComboBox()
        self.requires_single_control_source.addItems(["true", "false"])
        self.collision_enabled = QComboBox()
        self.collision_enabled.addItems(["true", "false"])
        self.collision_behavior = QComboBox()
        self.collision_behavior.addItems(["pause_hold", "safe_retreat", "estop"])
        self.soft_limit_enabled = QComboBox()
        self.soft_limit_enabled.addItems(["true", "false"])
        self.singularity_avoidance_enabled = QComboBox()
        self.singularity_avoidance_enabled.addItems(["true", "false"])
        self.xpanel_vout_mode = QComboBox()
        self.xpanel_vout_mode.addItems(["off", "tool_12v", "tool_24v"])

        layout.addRow("目标压力 (N)", self.pressure_target)
        layout.addRow("压力上限 (N)", self.pressure_upper)
        layout.addRow("压力下限 (N)", self.pressure_lower)
        layout.addRow("扫查速度 (mm/s)", self.scan_speed)
        layout.addRow("采样步长 (mm)", self.sample_step)
        layout.addRow("分段长度 (mm)", self.segment_length)
        layout.addRow("接触搜索速度 (mm/s)", self.contact_seek_speed)
        layout.addRow("退让速度 (mm/s)", self.retreat_speed)
        layout.addRow("图像质量阈值", self.quality_threshold)
        layout.addRow("平滑系数", self.smoothing_factor)
        layout.addRow("特征阈值", self.feature_threshold)
        layout.addRow("RT 扫描模式", self.rt_mode)
        layout.addRow("网络超时 (ms)", self.network_stale_ms)
        layout.addRow("压力超时 (ms)", self.pressure_stale_ms)
        layout.addRow("遥测频率 (Hz)", self.telemetry_rate_hz)
        layout.addRow("ROI 模式", self.roi_mode)
        layout.addRow("工具名", self.tool_name)
        layout.addRow("TCP 名", self.tcp_name)
        layout.addRow("载荷 (kg)", self.load_kg)
        layout.addRow("机器人 IP", self.remote_ip)
        layout.addRow("本机 IP", self.local_ip)
        layout.addRow("链路偏好", self.preferred_link)
        layout.addRow("机器人型号", self.robot_model)
        layout.addRow("SDK Robot 类", self.sdk_robot_class)
        layout.addRow("轴数", self.axis_count)
        layout.addRow("单控制源", self.requires_single_control_source)
        layout.addRow("RT 容忍阈值 (%)", self.rt_network_tolerance_percent)
        layout.addRow("Joint filter (Hz)", self.joint_filter_hz)
        layout.addRow("Cartesian filter (Hz)", self.cart_filter_hz)
        layout.addRow("Torque filter (Hz)", self.torque_filter_hz)
        layout.addRow("碰撞检测", self.collision_enabled)
        layout.addRow("碰撞灵敏度", self.collision_sensitivity)
        layout.addRow("碰撞后动作", self.collision_behavior)
        layout.addRow("碰撞回退 (mm)", self.collision_fallback_mm)
        layout.addRow("软限位", self.soft_limit_enabled)
        layout.addRow("软限位裕量 (°)", self.soft_limit_margin_deg)
        layout.addRow("奇异规避", self.singularity_avoidance_enabled)
        layout.addRow("RL 工程", self.rl_project_name)
        layout.addRow("RL 任务", self.rl_task_name)
        layout.addRow("xPanel 供电", self.xpanel_vout_mode)

        self.apply_btn = QPushButton("应用参数")
        self.apply_btn.setProperty("kind", "primary")
        self.apply_btn.clicked.connect(self._emit_config)
        layout.addRow(self.apply_btn)
        self.populate_from_config(config)

    def populate_from_config(self, config: RuntimeConfig) -> None:
        self._base_config = config
        self.pressure_target.setText(str(config.pressure_target))
        self.pressure_upper.setText(str(config.pressure_upper))
        self.pressure_lower.setText(str(config.pressure_lower))
        self.scan_speed.setText(str(config.scan_speed_mm_s))
        self.sample_step.setText(str(config.sample_step_mm))
        self.segment_length.setText(str(config.segment_length_mm))
        self.contact_seek_speed.setText(str(config.contact_seek_speed_mm_s))
        self.retreat_speed.setText(str(config.retreat_speed_mm_s))
        self.quality_threshold.setText(str(config.image_quality_threshold))
        self.smoothing_factor.setText(str(config.smoothing_factor))
        self.feature_threshold.setText(str(config.feature_threshold))
        self.network_stale_ms.setText(str(config.network_stale_ms))
        self.pressure_stale_ms.setText(str(config.pressure_stale_ms))
        self.telemetry_rate_hz.setText(str(config.telemetry_rate_hz))
        self.roi_mode.setCurrentText(config.roi_mode)
        self.rt_mode.setCurrentText(config.rt_mode)
        self.tool_name.setText(config.tool_name)
        self.tcp_name.setText(config.tcp_name)
        self.load_kg.setText(str(config.load_kg))
        self.remote_ip.setText(config.remote_ip)
        self.local_ip.setText(config.local_ip)
        self.preferred_link.setCurrentText(config.preferred_link)
        self.robot_model.setCurrentText(config.robot_model)
        self.sdk_robot_class.setCurrentText(config.sdk_robot_class)
        self.axis_count.setCurrentText(str(config.axis_count))
        self.requires_single_control_source.setCurrentText("true" if config.requires_single_control_source else "false")
        self.rt_network_tolerance_percent.setText(str(config.rt_network_tolerance_percent))
        self.joint_filter_hz.setText(str(config.joint_filter_hz))
        self.cart_filter_hz.setText(str(config.cart_filter_hz))
        self.torque_filter_hz.setText(str(config.torque_filter_hz))
        self.collision_enabled.setCurrentText("true" if config.collision_detection_enabled else "false")
        self.collision_sensitivity.setText(str(config.collision_sensitivity))
        self.collision_behavior.setCurrentText(config.collision_behavior)
        self.collision_fallback_mm.setText(str(config.collision_fallback_mm))
        self.soft_limit_enabled.setCurrentText("true" if config.soft_limit_enabled else "false")
        self.soft_limit_margin_deg.setText(str(config.joint_soft_limit_margin_deg))
        self.singularity_avoidance_enabled.setCurrentText("true" if config.singularity_avoidance_enabled else "false")
        self.rl_project_name.setText(config.rl_project_name)
        self.rl_task_name.setText(config.rl_task_name)
        self.xpanel_vout_mode.setCurrentText(config.xpanel_vout_mode)

    def read_config(self) -> RuntimeConfig:
        payload = self._base_config.to_dict()
        payload.update(
            pressure_target=float(self.pressure_target.text()),
            pressure_upper=float(self.pressure_upper.text()),
            pressure_lower=float(self.pressure_lower.text()),
            scan_speed_mm_s=float(self.scan_speed.text()),
            sample_step_mm=float(self.sample_step.text()),
            segment_length_mm=float(self.segment_length.text()),
            contact_seek_speed_mm_s=float(self.contact_seek_speed.text()),
            retreat_speed_mm_s=float(self.retreat_speed.text()),
            image_quality_threshold=float(self.quality_threshold.text()),
            roi_mode=self.roi_mode.currentText(),
            smoothing_factor=float(self.smoothing_factor.text()),
            feature_threshold=float(self.feature_threshold.text()),
            rt_mode=self.rt_mode.currentText(),
            network_stale_ms=int(self.network_stale_ms.text()),
            pressure_stale_ms=int(self.pressure_stale_ms.text()),
            telemetry_rate_hz=int(self.telemetry_rate_hz.text()),
            tool_name=self.tool_name.text().strip(),
            tcp_name=self.tcp_name.text().strip(),
            load_kg=float(self.load_kg.text()),
            remote_ip=self.remote_ip.text().strip(),
            local_ip=self.local_ip.text().strip(),
            preferred_link=self.preferred_link.currentText(),
            robot_model=self.robot_model.currentText(),
            sdk_robot_class=self.sdk_robot_class.currentText(),
            axis_count=int(self.axis_count.currentText()),
            requires_single_control_source=self.requires_single_control_source.currentText() == "true",
            rt_network_tolerance_percent=int(self.rt_network_tolerance_percent.text()),
            joint_filter_hz=float(self.joint_filter_hz.text()),
            cart_filter_hz=float(self.cart_filter_hz.text()),
            torque_filter_hz=float(self.torque_filter_hz.text()),
            collision_detection_enabled=self.collision_enabled.currentText() == "true",
            collision_sensitivity=int(self.collision_sensitivity.text()),
            collision_behavior=self.collision_behavior.currentText(),
            collision_fallback_mm=float(self.collision_fallback_mm.text()),
            soft_limit_enabled=self.soft_limit_enabled.currentText() == "true",
            joint_soft_limit_margin_deg=float(self.soft_limit_margin_deg.text()),
            singularity_avoidance_enabled=self.singularity_avoidance_enabled.currentText() == "true",
            rl_project_name=self.rl_project_name.text().strip(),
            rl_task_name=self.rl_task_name.text().strip(),
            xpanel_vout_mode=self.xpanel_vout_mode.currentText(),
        )
        return RuntimeConfig.from_dict(payload)

    def _emit_config(self) -> None:
        config = self.read_config()
        self._base_config = config
        self.config_applied.emit(config)
