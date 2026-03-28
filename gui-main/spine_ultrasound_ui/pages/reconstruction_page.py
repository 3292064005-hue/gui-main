from PySide6.QtWidgets import QGridLayout, QGroupBox, QVBoxLayout, QWidget
from spine_ultrasound_ui.widgets import ImagePane


class ReconstructionPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        group = QGroupBox("图像与重建")
        grid = QGridLayout(group)
        self.raw_pane = ImagePane("原始图像")
        self.pre_pane = ImagePane("预处理图像")
        self.feature_pane = ImagePane("关键结构提取")
        self.reconstruction_pane = ImagePane("局部重建结果")
        grid.addWidget(self.raw_pane, 0, 0)
        grid.addWidget(self.pre_pane, 0, 1)
        grid.addWidget(self.feature_pane, 1, 0)
        grid.addWidget(self.reconstruction_pane, 1, 1)
        layout.addWidget(group)
