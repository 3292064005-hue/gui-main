from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget


class PreparePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        box = QGroupBox("系统准备与自检")
        form = QFormLayout(box)
        self.lbl_toolset = QLabel("-")
        self.lbl_load = QLabel("-")
        self.lbl_sdk = QLabel("-")
        self.lbl_power = QLabel("-")
        self.lbl_mode = QLabel("-")
        self.lbl_camera = QLabel("-")
        self.lbl_ultrasound = QLabel("-")
        self.lbl_pressure = QLabel("-")
        form.addRow("Toolset", self.lbl_toolset)
        form.addRow("Load", self.lbl_load)
        form.addRow("SDK", self.lbl_sdk)
        form.addRow("Power", self.lbl_power)
        form.addRow("Operate mode", self.lbl_mode)
        form.addRow("Camera", self.lbl_camera)
        form.addRow("Ultrasound", self.lbl_ultrasound)
        form.addRow("Pressure", self.lbl_pressure)
        layout.addWidget(box)
