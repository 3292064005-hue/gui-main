from PySide6.QtWidgets import QFormLayout, QGridLayout, QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget


class AssessmentPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel("量化评估")
        title.setObjectName("PageTitle")
        subtitle = QLabel("汇总 Cobb 角、特征置信度、图像质量和评估状态。")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(12)

        result_box = QGroupBox("核心结果")
        form = QFormLayout(result_box)
        self.lbl_cobb = QLabel("0.0°")
        self.lbl_cobb.setObjectName("NumericValue")
        self.lbl_feature_conf = QLabel("0.00")
        self.lbl_feature_conf.setObjectName("MetricValue")
        self.lbl_quality_score = QLabel("0.00")
        self.lbl_quality_score.setObjectName("MetricValue")
        self.lbl_assessment_state = QLabel("未评估")
        self.lbl_assessment_state.setObjectName("MetricChip")
        form.addRow("Cobb角", self.lbl_cobb)
        form.addRow("特征置信度", self.lbl_feature_conf)
        form.addRow("图像质量评分", self.lbl_quality_score)
        form.addRow("评估状态", self.lbl_assessment_state)
        grid.addWidget(result_box, 0, 0)

        summary_box = QGroupBox("评估说明")
        summary_layout = QVBoxLayout(summary_box)
        self.assessment_text = QTextEdit()
        self.assessment_text.setReadOnly(True)
        self.assessment_text.setText(
            "量化评估页建议包含：\n"
            "1. 角度标注示意图\n"
            "2. 关键点手动校正入口\n"
            "3. 评估结论（轻度 / 中度 / 重度）\n"
            "4. 导出图像与导出表格\n"
        )
        summary_layout.addWidget(self.assessment_text)
        grid.addWidget(summary_box, 0, 1)

        layout.addLayout(grid)
