from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget


class AssessmentPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        result_box = QGroupBox("量化评估结果")
        form = QFormLayout(result_box)
        self.lbl_cobb = QLabel("0.0°")
        self.lbl_feature_conf = QLabel("0.00")
        self.lbl_quality_score = QLabel("0.00")
        self.lbl_assessment_state = QLabel("未评估")
        form.addRow("Cobb角", self.lbl_cobb)
        form.addRow("特征置信度", self.lbl_feature_conf)
        form.addRow("图像质量评分", self.lbl_quality_score)
        form.addRow("评估状态", self.lbl_assessment_state)
        layout.addWidget(result_box)
        self.assessment_text = QTextEdit()
        self.assessment_text.setReadOnly(True)
        self.assessment_text.setText(
            "量化评估页包含：\n"
            "1. 角度标注示意图\n"
            "2. 关键点手动校正按钮（待接入）\n"
            "3. 评估结论（轻度/中度/重度，可后续接入）\n"
            "4. 导出图像与导出表格\n"
        )
        layout.addWidget(self.assessment_text)
