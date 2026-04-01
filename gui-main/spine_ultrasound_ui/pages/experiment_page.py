from PySide6.QtWidgets import QGroupBox, QHeaderView, QLabel, QSplitter, QVBoxLayout, QWidget, QTableView

from spine_ultrasound_ui.widgets import ConfigForm, ExperimentTableModel


class ExperimentPage(QWidget):
    def __init__(self, config_form: ConfigForm, exp_model: ExperimentTableModel):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("实验配置")
        title.setObjectName("PageTitle")
        subtitle = QLabel("管理扫查参数模板、实时运行配置与实验记录。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        note = QLabel("建议将常用参数配置保存为标准模板，保证不同受试者间的流程一致性。")
        note.setObjectName("MutedLabel")
        left_layout.addWidget(note)
        left_layout.addWidget(config_form)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        exp_box = QGroupBox("实验记录")
        exp_layout = QVBoxLayout(exp_box)
        self.exp_table = QTableView()
        self.exp_table.setModel(exp_model)
        self.exp_table.setAlternatingRowColors(True)
        self.exp_table.setSelectionBehavior(QTableView.SelectRows)
        self.exp_table.setSelectionMode(QTableView.SingleSelection)
        self.exp_table.verticalHeader().setVisible(False)
        self.exp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        exp_layout.addWidget(self.exp_table)
        right_layout.addWidget(exp_box)
        splitter.addWidget(right)

        splitter.setSizes([440, 760])
