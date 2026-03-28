from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatusCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("StatusCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")
        self.value_label = QLabel("-")
        self.value_label.setObjectName("CardValue")
        self.extra_label = QLabel("")
        self.extra_label.setObjectName("CardExtra")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.extra_label)

    def update_text(self, value: str, extra: str = ""):
        self.value_label.setText(value)
        self.extra_label.setText(extra)
