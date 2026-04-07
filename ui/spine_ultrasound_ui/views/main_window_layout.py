from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from spine_ultrasound_ui.pages import (
    AssessmentPage,
    ExperimentPage,
    OverviewPage,
    PreparePage,
    ReconstructionPage,
    ReplayPage,
    RobotMonitorPage,
    ScanPage,
    SettingsPage,
    VisionPage,
)
from spine_ultrasound_ui.widgets import AlarmBanner, LogConsole, StatusCard


class MainWindowLayoutBuilder:
    """Build the main desktop shell while keeping MainWindow itself thin."""

    def __init__(self, window) -> None:
        self.window = window

    def build(self) -> None:
        w = self.window
        self.build_toolbar()
        self.build_statusbar()

        root = QWidget()
        root.setObjectName("MainShell")
        w.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        w.hero_card = self.build_header_banner()
        w.alarm_banner = AlarmBanner()
        main_layout.addWidget(w.hero_card)
        main_layout.addWidget(w.alarm_banner)

        w.main_splitter = QSplitter()
        w.main_splitter.setChildrenCollapsible(False)
        main_layout.addWidget(w.main_splitter, 1)
        for panel in (self.build_left_panel(), self.build_center_panel(), self.build_right_panel()):
            w.main_splitter.addWidget(panel)
        w.main_splitter.setSizes([360, 1020, 340])

        w.log_box = LogConsole()
        w.log_box.setMinimumHeight(88)
        main_layout.addWidget(w.log_box)

    def build_toolbar(self) -> None:
        w = self.window
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        w.addToolBar(toolbar)
        for text, fn in [
            ("新建实验", w.backend.create_experiment),
            ("刷新 SDK", w.backend.refresh_sdk_assets),
            ("应用主线基线", w.backend.apply_clinical_baseline),
            ("导出治理", w.backend.export_governance_snapshot),
            ("保存配置", w._save_runtime_config),
            ("保存结果", w.backend.save_results),
            ("导出摘要", w.backend.export_summary),
            ("安全退让", w.backend.safe_retreat),
        ]:
            action = QAction(text, w)
            action.triggered.connect(fn)
            toolbar.addAction(action)
        toolbar.addSeparator()
        estop = QAction("急停", w)
        estop.triggered.connect(w._confirm_estop)
        toolbar.addAction(estop)

    def build_statusbar(self) -> None:
        w = self.window
        status = QStatusBar()
        status.setSizeGripEnabled(False)
        w.setStatusBar(status)
        for attr, text, state in [
            ("system_state_label", "状态 · BOOT", "warn"),
            ("exp_id_label", "实验 · -", "ok"),
            ("readiness_label", "就绪 · 0%", "warn"),
        ]:
            label = QLabel(text)
            label.setObjectName("StatusPill")
            label.setProperty("state", state)
            setattr(w, attr, label)
            status.addPermanentWidget(label)
        status.addWidget(QLabel("桌面控制台已加载"), 1)

    def build_header_banner(self) -> QWidget:
        w = self.window
        card = QFrame()
        card.setObjectName("HeroCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        text_col = QVBoxLayout()
        title = QLabel("脊柱侧弯自动检测研究平台")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("单一控制面、单一证据链、单一状态入口。面向研究 / 临床演示 / 回放审阅的一体化桌面工作台。")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        pill_row = QHBoxLayout()
        pill_row.setSpacing(8)
        for attr, text, state in [
            ("header_state_pill", "系统 · BOOT", "warn"),
            ("header_mode_pill", "模式 · manual", "warn"),
            ("header_exp_pill", "实验 · -", "warn"),
            ("header_step_pill", "下一步 · 创建实验", "warn"),
        ]:
            pill = QLabel(text)
            pill.setObjectName("StatusPill")
            pill.setProperty("state", state)
            setattr(w, attr, pill)
            pill_row.addWidget(pill)
        pill_row.addStretch(1)
        text_col.addLayout(pill_row)
        text_col.addStretch(1)

        metrics_col = QHBoxLayout()
        w.header_cards = []
        for title_text, tone in [("机器人链路", "accent"), ("实时状态", "warning"), ("结果输出", "success")]:
            card_widget = StatusCard(title_text, tone=tone, compact=True)
            card_widget.setMinimumWidth(170)
            metrics_col.addWidget(card_widget)
            w.header_cards.append(card_widget)

        layout.addLayout(text_col, 3)
        layout.addLayout(metrics_col, 2)
        return card

    def build_left_panel(self) -> QWidget:
        w = self.window
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setMinimumWidth(340)
        panel.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        panel.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        device_box = QGroupBox("设备链路")
        device_layout = QVBoxLayout(device_box)
        w.badge_robot = self._device_badge(device_layout, "机器人")
        w.badge_cam = self._device_badge(device_layout, "相机")
        w.badge_ultra = self._device_badge(device_layout, "超声")
        layout.addWidget(device_box)

        for title, spec in self._action_groups().items():
            layout.addWidget(self._action_group(title, spec))

        governance = QGroupBox("治理与审计")
        governance_layout = QVBoxLayout(governance)
        governance_layout.setContentsMargins(8, 8, 8, 8)
        governance_layout.setSpacing(8)
        w.governance_summary = QLabel("控制面、控制权、证据链状态将在此处收敛显示。")
        w.governance_summary.setWordWrap(True)
        governance_layout.addWidget(w.governance_summary)
        governance_layout.addWidget(self._make_button("刷新治理", w.backend.refresh_session_governance))
        governance_layout.addWidget(self._make_button("导出治理", w.backend.export_governance_snapshot))
        if hasattr(w.backend, "browse_evidence_offline"):
            governance_layout.addWidget(self._make_button("离线证据浏览", w.backend.browse_evidence_offline))
        layout.addWidget(governance)
        layout.addStretch(1)
        return panel

    def build_center_panel(self) -> QWidget:
        w = self.window
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        w.tabs = QTabWidget()
        w.overview_page = OverviewPage()
        w.experiment_page = ExperimentPage(w.config_form, w.exp_model)
        w.prepare_page = PreparePage()
        w.scan_page = ScanPage()
        w.robot_monitor_page = RobotMonitorPage()
        w.vision_page = VisionPage()
        w.reconstruction_page = ReconstructionPage()
        w.assessment_page = AssessmentPage()
        w.replay_page = ReplayPage()
        w.settings_page = SettingsPage()
        w.tab_titles = [
            "系统总览",
            "实验配置",
            "系统准备",
            "自动扫查",
            "机器人监控",
            "视觉与路径",
            "图像与重建",
            "量化评估",
            "实验回放",
            "系统设置",
        ]
        for title, page in zip(
            w.tab_titles,
            [
                w.overview_page,
                w.experiment_page,
                w.prepare_page,
                w.scan_page,
                w.robot_monitor_page,
                w.vision_page,
                w.reconstruction_page,
                w.assessment_page,
                w.replay_page,
                w.settings_page,
            ],
        ):
            w.tabs.addTab(page, title)
        layout.addWidget(w.tabs)
        return container

    def build_right_panel(self) -> QWidget:
        w = self.window
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setMinimumWidth(320)
        panel.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        panel.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for attr, title, tone in [
            ("card_state", "系统状态", "accent"),
            ("card_exp", "实验编号", None),
            ("card_readiness", "流程就绪度", "warning"),
            ("card_pressure", "接触与压力", "success"),
            ("card_pose", "TCP 位姿", None),
            ("card_quality", "图像质量", "warning"),
            ("card_result", "结果摘要", None),
        ]:
            card = StatusCard(title, tone=tone, compact=True) if tone else StatusCard(title, compact=True)
            setattr(w, attr, card)
            layout.addWidget(card)
        layout.addStretch(1)
        return panel

    def _action_groups(self) -> dict[str, list[tuple[str, str, str]]]:
        return {
            "机器人控制": [
                ("btn_connect", "连接机器人", "connect_robot"),
                ("btn_disconnect", "断开机器人", "disconnect_robot"),
                ("btn_power_on", "上电", "power_on"),
                ("btn_power_off", "下电", "power_off"),
                ("btn_auto", "自动模式", "set_auto_mode"),
                ("btn_manual", "手动模式", "set_manual_mode"),
                ("btn_home", "回零 / Home", "go_home"),
                ("btn_retreat", "安全退让", "safe_retreat"),
            ],
            "实验主线": [
                ("btn_new_exp", "新建实验", "create_experiment"),
                ("btn_localize", "视觉定位", "run_localization"),
                ("btn_path", "生成路径", "generate_path"),
                ("btn_scan_start", "开始扫查", "start_scan"),
                ("btn_scan_pause", "暂停", "pause_scan"),
                ("btn_scan_resume", "恢复", "resume_scan"),
                ("btn_scan_stop", "停止", "stop_scan"),
            ],
            "图像与结果": [
                ("btn_pre", "预处理", "run_preprocess"),
                ("btn_recon", "重建", "run_reconstruction"),
                ("btn_assess", "评估", "run_assessment"),
                ("btn_export", "导出摘要", "export_summary"),
            ],
            "控制器资产": [
                ("btn_sdk_refresh", "刷新 SDK 资产", "refresh_sdk_assets"),
                ("btn_query_log", "读取控制器日志", "query_controller_log"),
                ("btn_run_rl", "运行 RL 工程", "run_rl_project"),
                ("btn_pause_rl", "暂停 RL", "pause_rl_project"),
                ("btn_enable_drag", "开启拖动", "enable_drag"),
                ("btn_disable_drag", "关闭拖动", "disable_drag"),
                ("btn_replay_path", "路径回放", "replay_path"),
            ],
        }

    def _action_group(self, title: str, spec: list[tuple[str, str, str]]) -> QWidget:
        w = self.window
        box = QGroupBox(title)
        grid = QGridLayout(box)
        grid.setContentsMargins(6, 8, 6, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        buttons = []
        for attr, text, backend_method in spec:
            button = self._make_button(text, getattr(w.backend, backend_method, lambda: QMessageBox.information(w, "提示", f"{text} 暂未接线")))
            setattr(w, attr, button)
            buttons.append(button)
        self._fill_grid(grid, buttons, columns=2, last_span=True)
        return box

    @staticmethod
    def _device_badge(layout: QVBoxLayout, name: str) -> QLabel:
        badge = QLabel(f"{name} · 未连接")
        badge.setObjectName("StatusPill")
        badge.setProperty("state", "warn")
        layout.addWidget(badge)
        return badge

    @staticmethod
    def _fill_grid(grid: QGridLayout, buttons: list[QPushButton], *, columns: int = 2, last_span: bool = False) -> None:
        row = 0
        col = 0
        for idx, button in enumerate(buttons):
            is_last = idx == len(buttons) - 1
            if last_span and is_last and (col != 0 or len(buttons) % columns == 1):
                grid.addWidget(button, row, 0, 1, columns)
                row += 1
                col = 0
                continue
            grid.addWidget(button, row, col)
            col += 1
            if col >= columns:
                row += 1
                col = 0

    @staticmethod
    def _make_button(text: str, callback, kind: str = "secondary") -> QPushButton:
        button = QPushButton(text)
        button.setProperty("kind", kind)
        button.clicked.connect(callback)
        return button
