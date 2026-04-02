from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget

from spine_ultrasound_ui.widgets import ImagePane


class VisionPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("视觉与路径")
        title.setObjectName("PageTitle")
        subtitle = QLabel("显示体表定位、脊柱走向估计、预览/执行路径、Planner 选择依据与 xMateModel 前检结果。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.camera_pane = ImagePane("背部定位视图", "建议叠加 ROI、中线、起止点和路径轨迹")
        layout.addWidget(self.camera_pane, 3)

        grid = QGridLayout()
        grid.setSpacing(12)

        plan_box = QGroupBox("路径与 Planner 摘要")
        plan_layout = QVBoxLayout(plan_box)
        self.plan_view = QTextEdit()
        self.plan_view.setReadOnly(True)
        self.plan_view.setPlaceholderText("预览路径、执行候选、S 曲线规划摘要和选择依据将在这里显示。")
        plan_layout.addWidget(self.plan_view)
        grid.addWidget(plan_box, 0, 0)

        model_box = QGroupBox("xMateModel 前检")
        model_layout = QVBoxLayout(model_box)
        self.model_view = QTextEdit()
        self.model_view.setReadOnly(True)
        self.model_view.setPlaceholderText("DH 参数、包络盒、连续性与工作区检查将在这里显示。")
        model_layout.addWidget(self.model_view)
        grid.addWidget(model_box, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        layout.addLayout(grid, 2)
