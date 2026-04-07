from typing import Dict, Tuple

from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget

from spine_ultrasound_ui.widgets import StateTimeline


class OverviewPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("系统总览")
        title.setObjectName("PageTitle")
        subtitle = QLabel("集中展示设备连通性、状态迁移与本次任务关键摘要。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        top_grid = QGridLayout()
        top_grid.setSpacing(12)
        self.device_labels: Dict[str, Tuple[QLabel, QLabel]] = {}
        for i, name in enumerate(["robot", "camera", "pressure", "ultrasound"]):
            box = QGroupBox(name.upper())
            v = QVBoxLayout(box)
            v.setSpacing(8)
            lab = QLabel("OFFLINE")
            lab.setObjectName("DeviceIndicator")
            lab.setProperty("state", "danger")
            detail = QLabel("等待设备上报状态")
            detail.setObjectName("MutedLabel")
            detail.setWordWrap(True)
            v.addWidget(lab)
            v.addWidget(detail)
            top_grid.addWidget(box, i // 2, i % 2)
            self.device_labels[name] = (lab, detail)
        layout.addLayout(top_grid)

        middle_grid = QGridLayout()
        middle_grid.setSpacing(12)

        timeline_box = QGroupBox("系统状态流转")
        timeline_layout = QVBoxLayout(timeline_box)
        hint = QLabel("当前状态会在时间轴中高亮，用于快速判断流程进展。")
        hint.setObjectName("SectionHint")
        self.timeline = StateTimeline()
        timeline_layout.addWidget(hint)
        timeline_layout.addWidget(self.timeline)
        middle_grid.addWidget(timeline_box, 0, 0)

        info_box = QGroupBox("最近一次实验摘要")
        info_layout = QVBoxLayout(info_box)
        self.recommended_label = QLabel("建议下一步：等待系统满足条件")
        self.recommended_label.setObjectName("FieldValue")
        self.readiness_label = QLabel("流程就绪度：0 / 0")
        self.readiness_label.setObjectName("MutedLabel")
        self.overview_text = QTextEdit()
        self.overview_text.setReadOnly(True)
        self.overview_text.setMinimumHeight(180)
        self.overview_text.setPlaceholderText("实验摘要、接触状态、质量评分与建议动作将在这里汇总。")
        info_layout.addWidget(self.recommended_label)
        info_layout.addWidget(self.readiness_label)
        info_layout.addWidget(self.overview_text)
        middle_grid.addWidget(info_box, 0, 1)

        middle_grid.setColumnStretch(0, 2)
        middle_grid.setColumnStretch(1, 3)
        layout.addLayout(middle_grid)
