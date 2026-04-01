from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class SettingsPage(QWidget):
    save_requested = Signal()
    reload_requested = Signal()
    restore_defaults_requested = Signal()
    save_layout_requested = Signal()
    apply_baseline_requested = Signal()
    export_governance_requested = Signal()
    refresh_governance_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("系统设置")
        title.setObjectName("PageTitle")
        subtitle = QLabel("集中管理全局配置、SDK 主线约束、持久化状态、工作区位置与运行参数恢复策略。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        runtime_box = QGroupBox("配置持久化")
        runtime_form = QFormLayout(runtime_box)
        self.lbl_workspace = QLabel("-")
        self.lbl_workspace.setObjectName("FieldValue")
        self.lbl_backend = QLabel("-")
        self.lbl_backend.setObjectName("FieldValue")
        self.lbl_config_path = QLabel("-")
        self.lbl_config_path.setObjectName("FieldValue")
        self.lbl_ui_path = QLabel("-")
        self.lbl_ui_path.setObjectName("FieldValue")
        self.lbl_last_saved = QLabel("-")
        self.lbl_last_saved.setObjectName("FieldValue")
        self.lbl_profile_state = QLabel("未加载")
        self.lbl_profile_state.setObjectName("MetricChip")
        self.lbl_backend_link = QLabel("-")
        self.lbl_backend_link.setObjectName("FieldValue")
        self.lbl_backend_stream = QLabel("-")
        self.lbl_backend_stream.setObjectName("FieldValue")
        runtime_form.addRow("工作区", self.lbl_workspace)
        runtime_form.addRow("后端模式", self.lbl_backend)
        runtime_form.addRow("链路状态", self.lbl_backend_link)
        runtime_form.addRow("流连接", self.lbl_backend_stream)
        runtime_form.addRow("运行配置", self.lbl_config_path)
        runtime_form.addRow("界面布局", self.lbl_ui_path)
        runtime_form.addRow("最近保存", self.lbl_last_saved)
        runtime_form.addRow("当前状态", self.lbl_profile_state)
        layout.addWidget(runtime_box)

        sdk_box = QGroupBox("SDK 主线对齐")
        sdk_form = QFormLayout(sdk_box)
        self.lbl_sdk_family = QLabel("-")
        self.lbl_sdk_family.setObjectName("FieldValue")
        self.lbl_sdk_summary = QLabel("-")
        self.lbl_sdk_summary.setObjectName("MetricChip")
        self.lbl_robot_profile = QLabel("-")
        self.lbl_robot_profile.setObjectName("FieldValue")
        self.lbl_ip_link = QLabel("-")
        self.lbl_ip_link.setObjectName("FieldValue")
        sdk_form.addRow("SDK", self.lbl_sdk_family)
        sdk_form.addRow("对齐状态", self.lbl_sdk_summary)
        sdk_form.addRow("机器人主线", self.lbl_robot_profile)
        sdk_form.addRow("网络链路", self.lbl_ip_link)
        layout.addWidget(sdk_box)

        action_box = QGroupBox("设置操作")
        action_layout = QVBoxLayout(action_box)
        self.btn_save = QPushButton("保存当前配置")
        self.btn_save.setProperty("kind", "primary")
        self.btn_save.clicked.connect(self.save_requested.emit)
        self.btn_reload = QPushButton("重新加载已保存配置")
        self.btn_reload.clicked.connect(self.reload_requested.emit)
        self.btn_defaults = QPushButton("恢复默认配置")
        self.btn_defaults.setProperty("kind", "warning")
        self.btn_defaults.clicked.connect(self.restore_defaults_requested.emit)
        self.btn_layout = QPushButton("保存界面布局")
        self.btn_layout.setProperty("kind", "ghost")
        self.btn_layout.clicked.connect(self.save_layout_requested.emit)
        self.btn_apply_baseline = QPushButton("应用 xMate 主线基线")
        self.btn_apply_baseline.setProperty("kind", "primary")
        self.btn_apply_baseline.clicked.connect(self.apply_baseline_requested.emit)
        self.btn_export_governance = QPushButton("导出治理快照")
        self.btn_export_governance.setProperty("kind", "success")
        self.btn_export_governance.clicked.connect(self.export_governance_requested.emit)
        self.btn_refresh_governance = QPushButton("刷新会话治理")
        self.btn_refresh_governance.clicked.connect(self.refresh_governance_requested.emit)
        for btn in [self.btn_save, self.btn_reload, self.btn_defaults, self.btn_layout, self.btn_apply_baseline, self.btn_export_governance, self.btn_refresh_governance]:
            action_layout.addWidget(btn)
        layout.addWidget(action_box)

        note_box = QGroupBox("SDK 治理说明")
        note_layout = QVBoxLayout(note_box)
        self.note_view = QTextEdit()
        self.note_view.setReadOnly(True)
        self.note_view.setPlaceholderText("SDK 主线治理摘要、模块覆盖率、阻塞项与告警将在这里显示。")
        note_layout.addWidget(self.note_view)
        layout.addWidget(note_box)
        layout.addStretch(1)

    def set_runtime_info(
        self,
        *,
        workspace: str,
        backend: str,
        config_path: str,
        ui_path: str,
        last_saved: str,
        profile_state: str,
        sdk_family: str = "-",
        sdk_summary: str = "-",
        robot_profile: str = "-",
        ip_link: str = "-",
        sdk_note: str = "",
        backend_link_state: str = "-",
        backend_stream_state: str = "-",
    ) -> None:
        self.lbl_workspace.setText(workspace)
        self.lbl_backend.setText(backend)
        self.lbl_config_path.setText(config_path)
        self.lbl_ui_path.setText(ui_path)
        self.lbl_last_saved.setText(last_saved)
        self.lbl_profile_state.setText(profile_state)
        self.lbl_backend_link.setText(backend_link_state)
        self.lbl_backend_stream.setText(backend_stream_state)
        self.lbl_sdk_family.setText(sdk_family)
        self.lbl_sdk_summary.setText(sdk_summary)
        self.lbl_robot_profile.setText(robot_profile)
        self.lbl_ip_link.setText(ip_link)
        if sdk_note:
            self.note_view.setPlainText(sdk_note)
