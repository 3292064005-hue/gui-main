from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from spine_ultrasound_ui.widgets import ImagePane


class ReconstructionPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("图像与重建")
        title.setObjectName("PageTitle")
        subtitle = QLabel("展示原始图像、预处理结果、特征提取以及局部重建过程。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        group = QGroupBox("重建工作区")
        grid = QGridLayout(group)
        grid.setSpacing(12)
        self.raw_pane = ImagePane("原始图像", "输入帧")
        self.pre_pane = ImagePane("预处理图像", "滤波、增强、ROI 裁剪结果")
        self.feature_pane = ImagePane("关键结构提取", "骨性标志点或轮廓")
        self.reconstruction_pane = ImagePane("局部重建结果", "局部三维或拼接重建视图")
        grid.addWidget(self.raw_pane, 0, 0)
        grid.addWidget(self.pre_pane, 0, 1)
        grid.addWidget(self.feature_pane, 1, 0)
        grid.addWidget(self.reconstruction_pane, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        layout.addWidget(group, 1)
