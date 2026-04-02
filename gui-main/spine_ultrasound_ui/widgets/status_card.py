from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatusCard(QFrame):
    def __init__(self, title: str, tone: str = "default", *, compact: bool = False):
        super().__init__()
        self.setObjectName("StatusCard")
        self.setProperty("tone", tone)
        self.setProperty("compact", compact)
        layout = QVBoxLayout(self)
        if compact:
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(4)
        else:
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")
        self.value_label = QLabel("-")
        self.value_label.setObjectName("CardValue")
        self.value_label.setWordWrap(True)
        self.extra_label = QLabel("")
        self.extra_label.setObjectName("CardExtra")
        self.extra_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.extra_label)

    def update_text(self, value: str, extra: str = ""):
        self.value_label.setText(value)
        self.extra_label.setText(extra)

    def set_tone(self, tone: str):
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
