from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget


class RobotMonitorPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        group = QGroupBox("机器人监控")
        form = QFormLayout(group)
        self.lbl_joint_pos = QLabel("-")
        self.lbl_joint_vel = QLabel("-")
        self.lbl_joint_torque = QLabel("-")
        self.lbl_tcp = QLabel("-")
        self.lbl_cart_force = QLabel("-")
        self.lbl_operate_mode = QLabel("-")
        self.lbl_power_state = QLabel("-")
        form.addRow("Joint Pos", self.lbl_joint_pos)
        form.addRow("Joint Vel", self.lbl_joint_vel)
        form.addRow("Joint Torque", self.lbl_joint_torque)
        form.addRow("TCP Pose", self.lbl_tcp)
        form.addRow("Cartesian Force", self.lbl_cart_force)
        form.addRow("Operate Mode", self.lbl_operate_mode)
        form.addRow("Power", self.lbl_power_state)
        layout.addWidget(group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("控制器日志 / 事件流")
        layout.addWidget(self.log_view)
