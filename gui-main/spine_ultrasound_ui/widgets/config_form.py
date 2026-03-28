from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLineEdit, QPushButton
from spine_ultrasound_ui.models import RuntimeConfig


class ConfigForm(QGroupBox):
    config_applied = Signal(RuntimeConfig)

    def __init__(self, config: RuntimeConfig):
        super().__init__("参数配置")
        layout = QFormLayout(self)
        self.pressure_target = QLineEdit(str(config.pressure_target))
        self.pressure_upper = QLineEdit(str(config.pressure_upper))
        self.pressure_lower = QLineEdit(str(config.pressure_lower))
        self.scan_speed = QLineEdit(str(config.scan_speed_mm_s))
        self.sample_step = QLineEdit(str(config.sample_step_mm))
        self.segment_length = QLineEdit(str(config.segment_length_mm))
        self.contact_seek_speed = QLineEdit(str(config.contact_seek_speed_mm_s))
        self.retreat_speed = QLineEdit(str(config.retreat_speed_mm_s))
        self.quality_threshold = QLineEdit(str(config.image_quality_threshold))
        self.smoothing_factor = QLineEdit(str(config.smoothing_factor))
        self.feature_threshold = QLineEdit(str(config.feature_threshold))
        self.network_stale_ms = QLineEdit(str(config.network_stale_ms))
        self.pressure_stale_ms = QLineEdit(str(config.pressure_stale_ms))
        self.telemetry_rate_hz = QLineEdit(str(config.telemetry_rate_hz))
        self.roi_mode = QComboBox(); self.roi_mode.addItems(["auto", "manual"]); self.roi_mode.setCurrentText(config.roi_mode)
        self.rt_mode = QComboBox(); self.rt_mode.addItems(["cartesianImpedance", "jointImpedance"]); self.rt_mode.setCurrentText(config.rt_mode)
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
        layout.addRow("RT 模式", self.rt_mode)
        layout.addRow("网络超时 (ms)", self.network_stale_ms)
        layout.addRow("压力超时 (ms)", self.pressure_stale_ms)
        layout.addRow("遥测频率 (Hz)", self.telemetry_rate_hz)
        layout.addRow("ROI 模式", self.roi_mode)
        self.apply_btn = QPushButton("应用参数")
        self.apply_btn.clicked.connect(self._emit_config)
        layout.addRow(self.apply_btn)

    def _emit_config(self):
        cfg = RuntimeConfig(
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
        )
        self.config_applied.emit(cfg)
