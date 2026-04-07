from PySide6.QtWidgets import QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget


class ReplayPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("实验回放")
        title.setObjectName("PageTitle")
        subtitle = QLabel("查看时间轴、关键告警点、低质量片段、路径回放摘要、拖动示教状态和 RL 运行状态。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        box = QGroupBox("回放时间轴")
        v = QVBoxLayout(box)
        self.lbl_current = QLabel("未加载实验")
        self.lbl_current.setObjectName("FieldValue")
        self.timeline = QTextEdit()
        self.timeline.setReadOnly(True)
        self.timeline.setPlaceholderText("时间轴 / 告警点 / 低质量段将在这里显示。")
        v.addWidget(self.lbl_current)
        v.addWidget(self.timeline)
        layout.addWidget(box)

        sdk_box = QGroupBox("路径与协作资产")
        sdk_layout = QVBoxLayout(sdk_box)
        self.asset_view = QTextEdit()
        self.asset_view.setReadOnly(True)
        self.asset_view.setPlaceholderText("路径回放库、拖动示教状态、RL 工程状态将在这里显示。")
        sdk_layout.addWidget(self.asset_view)
        layout.addWidget(sdk_box)
