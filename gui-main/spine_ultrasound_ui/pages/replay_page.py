from PySide6.QtWidgets import QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget


class ReplayPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        box = QGroupBox("实验回放")
        v = QVBoxLayout(box)
        self.lbl_current = QLabel("未加载实验")
        self.timeline = QTextEdit()
        self.timeline.setReadOnly(True)
        self.timeline.setPlaceholderText("时间轴 / 告警点 / 低质量段将在这里显示。")
        v.addWidget(self.lbl_current)
        v.addWidget(self.timeline)
        layout.addWidget(box)
