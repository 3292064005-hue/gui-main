from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QGroupBox,
    QMainWindow,
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

from spine_ultrasound_ui.models import ExperimentRecord
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
from spine_ultrasound_ui.styles import MAIN_STYLESHEET
from spine_ultrasound_ui.widgets import AlarmBanner, ConfigForm, ExperimentTableModel, LogConsole, StatusCard


class MainWindow(QMainWindow):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.setWindowTitle("脊柱侧弯自动检测研究平台")
        self.resize(1720, 1020)
        self.exp_model = ExperimentTableModel([])
        self.config_form = ConfigForm(self.backend.config)
        if hasattr(self.backend, "update_config"):
            self.config_form.config_applied.connect(self.backend.update_config)
        self._build_ui()
        self._connect_backend()
        self.setStyleSheet(MAIN_STYLESHEET)

    def _build_ui(self):
        self._build_toolbar()
        self._build_statusbar()
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        self.alarm_banner = AlarmBanner()
        main_layout.addWidget(self.alarm_banner)
        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        main_layout.addWidget(splitter)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_center_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([300, 980, 320])
        self.log_box = LogConsole()
        self.log_box.setMinimumHeight(150)
        main_layout.addWidget(self.log_box)

    def _build_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        actions = [
            ("新建实验", self.backend.create_experiment),
            ("保存结果", self.backend.save_results),
            ("导出摘要", self.backend.export_summary),
            ("安全退让", self.backend.safe_retreat),
        ]
        for text, fn in actions:
            act = QAction(text, self)
            act.triggered.connect(fn)
            toolbar.addAction(act)
        toolbar.addSeparator()
        estop = QAction("急停", self)
        estop.triggered.connect(self._confirm_estop)
        toolbar.addAction(estop)

    def _build_statusbar(self):
        status = QStatusBar()
        self.setStatusBar(status)
        self.system_state_label = QPushButton("状态：BOOT")
        self.system_state_label.setEnabled(False)
        self.exp_id_label = QPushButton("实验：-")
        self.exp_id_label.setEnabled(False)
        status.addPermanentWidget(self.system_state_label)
        status.addPermanentWidget(self.exp_id_label)

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        g1 = QGroupBox("机器人与系统")
        g1_layout = QVBoxLayout(g1)
        self.btn_connect = QPushButton("连接机器人")
        self.btn_disconnect = QPushButton("断开机器人")
        self.btn_power_on = QPushButton("上电")
        self.btn_power_off = QPushButton("下电")
        self.btn_auto = QPushButton("自动模式")
        self.btn_manual = QPushButton("手动模式")
        self.btn_connect.clicked.connect(self.backend.connect_robot)
        self.btn_disconnect.clicked.connect(self.backend.disconnect_robot)
        self.btn_power_on.clicked.connect(self.backend.power_on)
        self.btn_power_off.clicked.connect(self.backend.power_off)
        self.btn_auto.clicked.connect(self.backend.set_auto_mode)
        self.btn_manual.clicked.connect(self.backend.set_manual_mode)
        for btn in [self.btn_connect, self.btn_disconnect, self.btn_power_on, self.btn_power_off, self.btn_auto, self.btn_manual]:
            g1_layout.addWidget(btn)

        g2 = QGroupBox("实验与扫查")
        g2_layout = QVBoxLayout(g2)
        self.btn_new_exp = QPushButton("新建实验")
        self.btn_localize = QPushButton("开始视觉定位")
        self.btn_path = QPushButton("生成扫查路径")
        self.btn_scan_start = QPushButton("开始扫查")
        self.btn_scan_pause = QPushButton("暂停扫查")
        self.btn_scan_resume = QPushButton("恢复扫查")
        self.btn_scan_stop = QPushButton("停止扫查")
        self.btn_home = QPushButton("回初始位")
        self.btn_retreat = QPushButton("安全退让")
        self.btn_new_exp.clicked.connect(self.backend.create_experiment)
        self.btn_localize.clicked.connect(self.backend.run_localization)
        self.btn_path.clicked.connect(self.backend.generate_path)
        self.btn_scan_start.clicked.connect(self.backend.start_scan)
        self.btn_scan_pause.clicked.connect(self.backend.pause_scan)
        self.btn_scan_resume.clicked.connect(self.backend.resume_scan)
        self.btn_scan_stop.clicked.connect(self.backend.stop_scan)
        self.btn_home.clicked.connect(self.backend.go_home)
        self.btn_retreat.clicked.connect(self.backend.safe_retreat)
        for btn in [self.btn_new_exp, self.btn_localize, self.btn_path, self.btn_scan_start, self.btn_scan_pause, self.btn_scan_resume, self.btn_scan_stop, self.btn_home, self.btn_retreat]:
            g2_layout.addWidget(btn)

        g3 = QGroupBox("算法与导出")
        g3_layout = QVBoxLayout(g3)
        self.btn_pre = QPushButton("图像预处理")
        self.btn_recon = QPushButton("开始重建")
        self.btn_assess = QPushButton("计算 Cobb 角")
        self.btn_save = QPushButton("保存结果")
        self.btn_export = QPushButton("导出摘要")
        self.btn_pre.clicked.connect(self.backend.run_preprocess)
        self.btn_recon.clicked.connect(self.backend.run_reconstruction)
        self.btn_assess.clicked.connect(self.backend.run_assessment)
        self.btn_save.clicked.connect(self.backend.save_results)
        self.btn_export.clicked.connect(self.backend.export_summary)
        for btn in [self.btn_pre, self.btn_recon, self.btn_assess, self.btn_save, self.btn_export]:
            g3_layout.addWidget(btn)

        g4 = QGroupBox("安全控制")
        g4_layout = QVBoxLayout(g4)
        self.btn_estop = QPushButton("急停")
        self.btn_estop.setObjectName("DangerButton")
        self.btn_estop.clicked.connect(self._confirm_estop)
        g4_layout.addWidget(self.btn_estop)

        for g in [g1, g2, g3, g4]:
            layout.addWidget(g)
        layout.addStretch(1)
        return w

    def _build_center_panel(self) -> QWidget:
        self.tabs = QTabWidget()
        self.overview_page = OverviewPage()
        self.experiment_page = ExperimentPage(self.config_form, self.exp_model)
        self.prepare_page = PreparePage()
        self.scan_page = ScanPage()
        self.robot_monitor_page = RobotMonitorPage()
        self.vision_page = VisionPage()
        self.reconstruction_page = ReconstructionPage()
        self.assessment_page = AssessmentPage()
        self.replay_page = ReplayPage()
        self.settings_page = SettingsPage()
        pages = [
            ("系统总览", self.overview_page),
            ("实验配置", self.experiment_page),
            ("系统准备", self.prepare_page),
            ("自动扫查", self.scan_page),
            ("机器人监控", self.robot_monitor_page),
            ("视觉与路径", self.vision_page),
            ("图像与重建", self.reconstruction_page),
            ("量化评估", self.assessment_page),
            ("实验回放", self.replay_page),
            ("系统设置", self.settings_page),
        ]
        for title, page in pages:
            self.tabs.addTab(page, title)
        return self.tabs

    def _build_right_panel(self) -> QWidget:
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.card_state = StatusCard("系统状态")
        self.card_exp = StatusCard("实验编号")
        self.card_pressure = StatusCard("接触与压力")
        self.card_pose = StatusCard("TCP 位姿")
        self.card_quality = StatusCard("图像质量")
        self.card_result = StatusCard("结果摘要")
        for card in [self.card_state, self.card_exp, self.card_pressure, self.card_pose, self.card_quality, self.card_result]:
            layout.addWidget(card)
        layout.addStretch(1)
        panel.setWidget(content)
        return panel

    def _connect_backend(self):
        self.backend.status_updated.connect(self._on_status)
        self.backend.log_generated.connect(self._append_log)
        if hasattr(self.backend, "camera_pixmap_ready"):
            self.backend.camera_pixmap_ready.connect(self._update_camera_pixmap)
        if hasattr(self.backend, "ultrasound_pixmap_ready"):
            self.backend.ultrasound_pixmap_ready.connect(self._update_ultrasound_pixmap)
        if hasattr(self.backend, "reconstruction_pixmap_ready"):
            self.backend.reconstruction_pixmap_ready.connect(self._update_reconstruction_pixmap)
        self.backend.experiments_updated.connect(self._on_experiments)
        self.backend.system_state_changed.connect(self._on_system_state)
        if hasattr(self.backend, "alarm_raised"):
            self.backend.alarm_raised.connect(self._on_alarm)

    def _apply_permissions(self, payload: dict):
        perms = payload.get("permissions", {})
        mapping = {
            self.btn_connect: "connect_robot",
            self.btn_disconnect: "disconnect_robot",
            self.btn_power_on: "power_on",
            self.btn_power_off: "power_off",
            self.btn_auto: "set_auto_mode",
            self.btn_manual: "set_manual_mode",
            self.btn_new_exp: "create_experiment",
            self.btn_localize: "run_localization",
            self.btn_path: "generate_path",
            self.btn_scan_start: "start_scan",
            self.btn_scan_pause: "pause_scan",
            self.btn_scan_resume: "resume_scan",
            self.btn_scan_stop: "stop_scan",
            self.btn_home: "go_home",
            self.btn_retreat: "safe_retreat",
            self.btn_pre: "run_preprocess",
            self.btn_recon: "run_reconstruction",
            self.btn_assess: "run_assessment",
            self.btn_export: "export_summary",
        }
        for btn, key in mapping.items():
            btn.setEnabled(perms.get(key, True))

    @Slot(dict)
    def _on_status(self, payload: dict):
        devices = payload["devices"]
        metrics = payload["metrics"]
        current_exp = payload["current_experiment"]
        robot = payload.get("robot", {})
        safety = payload.get("safety", {})
        recording = payload.get("recording", {})
        config = payload.get("config", {})
        workflow = payload.get("workflow", {})
        self._apply_permissions(payload)
        for name, (lab, det) in self.overview_page.device_labels.items():
            status = devices[name]
            lab.setText(status["health"])
            det.setText(status["detail"])
            lab.setStyleSheet("color:#16A34A; font-weight:700;" if status["connected"] else "color:#DC2626; font-weight:700;")
        self.overview_page.timeline.set_current(payload["state"])
        self.scan_page.lbl_segment.setText(str(metrics["segment_id"]))
        self.scan_page.lbl_path_idx.setText(str(metrics["path_index"]))
        self.scan_page.lbl_frame_id.setText(str(metrics["frame_id"]))
        self.scan_page.progress.setValue(int(metrics["scan_progress"]))
        self.scan_page.lbl_pressure_current.setText(f"{metrics['pressure_current']:.2f} N")
        self.scan_page.lbl_pressure_target.setText(f"{metrics['pressure_target']:.2f} N")
        self.scan_page.lbl_contact_mode.setText(metrics["contact_mode"])
        self.scan_page.lbl_contact_conf.setText(f"{metrics['contact_confidence']:.2f}")
        pose = metrics["tcp_pose"]
        pose_text = f"x={pose['x']:.1f}, y={pose['y']:.1f}, z={pose['z']:.1f}, rx={pose['rx']:.1f}, ry={pose['ry']:.1f}, rz={pose['rz']:.1f}"
        self.scan_page.lbl_pose.setText(pose_text)
        self.robot_monitor_page.lbl_joint_pos.setText(str(metrics["joint_pos"]))
        self.robot_monitor_page.lbl_joint_vel.setText(str(metrics["joint_vel"]))
        self.robot_monitor_page.lbl_joint_torque.setText(str(metrics["joint_torque"]))
        self.robot_monitor_page.lbl_tcp.setText(pose_text)
        self.robot_monitor_page.lbl_cart_force.setText(str(metrics["cart_force"]))
        self.robot_monitor_page.lbl_operate_mode.setText(robot.get("operate_mode", "-"))
        self.robot_monitor_page.lbl_power_state.setText("ON" if robot.get("powered", False) else "OFF")
        self.assessment_page.lbl_cobb.setText(f"{metrics['cobb_angle']:.1f}°")
        self.assessment_page.lbl_feature_conf.setText(f"{metrics['feature_confidence']:.2f}")
        self.assessment_page.lbl_quality_score.setText(f"{metrics.get('quality_score', metrics['image_quality']):.2f}")
        self.assessment_page.lbl_assessment_state.setText(payload["state"])
        self.card_state.update_text(payload["state"], f"Operate mode: {robot.get('operate_mode', '-')}")
        self.card_exp.update_text(current_exp["exp_id"] if current_exp else "-", current_exp.get("session_id", "-") if current_exp else "尚未创建实验")
        self.card_pressure.update_text(f"{metrics['pressure_current']:.2f} / {metrics['pressure_target']:.2f} N", f"{metrics['contact_mode']} / {metrics.get('recommended_action', '-')}")
        self.card_pose.update_text(f"x={pose['x']:.1f}, y={pose['y']:.1f}, z={pose['z']:.1f}", f"rx={pose['rx']:.1f}, ry={pose['ry']:.1f}, rz={pose['rz']:.1f}")
        self.card_quality.update_text(f"图像 {metrics['image_quality']:.2f}", f"质量分 {metrics.get('quality_score', 0.0):.2f}")
        self.card_result.update_text(f"扫描进度 {metrics['scan_progress']:.0f}%", f"段 {metrics['segment_id']} / 录制 {'ON' if recording.get('recording', False) else 'OFF'}")
        summary_lines = [
            f"当前系统状态：{payload['state']}",
            f"当前实验：{current_exp['exp_id'] if current_exp else '-'}",
            f"当前会话：{current_exp.get('session_id', '-') if current_exp else '-'}",
            f"当前压力：{metrics['pressure_current']:.2f} N / 目标 {metrics['pressure_target']:.2f} N",
            f"接触状态：{metrics['contact_mode']} / 动作建议 {metrics.get('recommended_action', '-')}",
            f"当前图像质量：{metrics['image_quality']:.2f} / 综合 {metrics.get('quality_score', 0.0):.2f}",
            f"当前 Cobb角：{metrics['cobb_angle']:.1f}°",
            f"定位策略：{workflow.get('localization', {}).get('implementation', '-')} / {workflow.get('localization', {}).get('state', '-')}",
            f"路径策略：{workflow.get('scan_plan', {}).get('implementation', '-')} / {workflow.get('scan_plan', {}).get('state', '-')}",
            f"可扫查：{'YES' if safety.get('safe_to_scan', False) else 'NO'} / 联锁 {', '.join(safety.get('active_interlocks', [])) or '-'}",
        ]
        self.overview_page.overview_text.setText("\n".join(summary_lines))
        self.prepare_page.lbl_toolset.setText(str(config.get("tool_name", "-")))
        self.prepare_page.lbl_load.setText(f"{config.get('load_kg', '-') } kg")
        self.prepare_page.lbl_sdk.setText("ROKAE xCore SDK (integrated)")
        self.prepare_page.lbl_power.setText("ON" if robot.get("powered", False) else "OFF")
        self.prepare_page.lbl_mode.setText(robot.get("operate_mode", "-"))
        self.prepare_page.lbl_camera.setText(f"{devices['camera']['health']} / fresh={devices['camera'].get('fresh', False)}")
        self.prepare_page.lbl_ultrasound.setText(f"{devices['ultrasound']['health']} / fresh={devices['ultrasound'].get('fresh', False)}")
        self.prepare_page.lbl_pressure.setText(f"{devices['pressure']['health']} / fresh={devices['pressure'].get('fresh', False)}")
        self.system_state_label.setText(f"状态：{payload['state']}")
        self.exp_id_label.setText(f"实验：{current_exp['exp_id'] if current_exp else '-'}")

    @Slot(list)
    def _on_experiments(self, records: list[ExperimentRecord]):
        self.exp_model.set_records(records)

    @Slot(str)
    def _on_system_state(self, state: str):
        self.statusBar().showMessage(f"系统状态切换：{state}", 3000)

    @Slot(str)
    def _on_alarm(self, message: str):
        self.alarm_banner.set_alarm("ALARM", message)
        self._append_log("ALARM", message)

    @Slot(str, str)
    def _append_log(self, level: str, message: str):
        self.log_box.append_colored(level, message)
        self.robot_monitor_page.log_view.append(message)

    def _update_camera_pixmap(self, pix):
        self.scan_page.camera_pane.set_pixmap(pix)
        self.vision_page.camera_pane.set_pixmap(pix)
        self.reconstruction_page.raw_pane.set_pixmap(pix)

    def _update_ultrasound_pixmap(self, pix):
        self.scan_page.ultrasound_pane.set_pixmap(pix)
        self.reconstruction_page.pre_pane.set_pixmap(pix)
        self.reconstruction_page.feature_pane.set_pixmap(pix)

    def _update_reconstruction_pixmap(self, pix):
        self.reconstruction_page.reconstruction_pane.set_pixmap(pix)

    def _confirm_estop(self):
        ret = QMessageBox.warning(self, "急停确认", "确认执行急停？该操作将立即停止当前流程。", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.alarm_banner.set_alarm("ALARM", "急停触发，所有运动应立即中止。")
            if hasattr(self.backend, "emergency_stop"):
                self.backend.emergency_stop()
            else:
                self.backend.safe_retreat()
