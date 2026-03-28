from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget
from spine_ultrasound_ui.widgets import ImagePane


class VisionPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.camera_pane = ImagePane("背部定位视图")
        layout.addWidget(self.camera_pane)
        note = QTextEdit()
        note.setReadOnly(True)
        note.setText(
            "视觉定位页用于显示：\n"
            "1. 背部区域识别结果\n"
            "2. 体表中线与脊柱走向估计\n"
            "3. 起止点与路径预览\n\n"
            "后续你只需把视觉节点输出叠加到这里即可。"
        )
        layout.addWidget(note)
