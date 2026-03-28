from typing import Dict, Tuple
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget
from spine_ultrasound_ui.widgets import StateTimeline


class OverviewPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        top_grid = QGridLayout()
        self.device_labels: Dict[str, Tuple[QLabel, QLabel]] = {}
        for i, name in enumerate(["robot", "camera", "pressure", "ultrasound"]):
            box = QGroupBox(name.upper())
            v = QVBoxLayout(box)
            lab = QLabel("offline")
            lab.setObjectName("DeviceIndicator")
            detail = QLabel("-")
            detail.setWordWrap(True)
            v.addWidget(lab)
            v.addWidget(detail)
            top_grid.addWidget(box, i // 2, i % 2)
            self.device_labels[name] = (lab, detail)
        layout.addLayout(top_grid)
        self.timeline = StateTimeline()
        layout.addWidget(self.timeline)
        info_box = QGroupBox("最近一次实验摘要")
        info_layout = QVBoxLayout(info_box)
        self.overview_text = QTextEdit()
        self.overview_text.setReadOnly(True)
        self.overview_text.setMinimumHeight(220)
        info_layout.addWidget(self.overview_text)
        layout.addWidget(info_box)
