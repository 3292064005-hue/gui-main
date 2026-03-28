from PySide6.QtWidgets import QGroupBox, QHeaderView, QLabel, QSplitter, QVBoxLayout, QWidget, QTableView
from spine_ultrasound_ui.widgets import ConfigForm, ExperimentTableModel


class ExperimentPage(QWidget):
    def __init__(self, config_form: ConfigForm, exp_model: ExperimentTableModel):
        super().__init__()
        layout = QVBoxLayout(self)
        splitter = QSplitter()
        layout.addWidget(splitter)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("实验配置与参数模板"))
        left_layout.addWidget(config_form)
        splitter.addWidget(left)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        exp_box = QGroupBox("实验记录")
        exp_layout = QVBoxLayout(exp_box)
        self.exp_table = QTableView()
        self.exp_table.setModel(exp_model)
        self.exp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        exp_layout.addWidget(self.exp_table)
        right_layout.addWidget(exp_box)
        splitter.addWidget(right)
        splitter.setSizes([420, 640])
