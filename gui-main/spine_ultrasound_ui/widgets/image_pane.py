from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout


class ImagePane(QGroupBox):
    def __init__(self, title: str):
        super().__init__(title)
        layout = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumSize(360, 220)
        self.label.setStyleSheet("background:#0F172A; border-radius:8px;")
        layout.addWidget(self.label)

    def set_pixmap(self, pix: QPixmap):
        if pix.isNull():
            return
        self.label.setPixmap(pix.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        pixmap = self.label.pixmap()
        if pixmap is not None:
            self.label.setPixmap(pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        super().resizeEvent(event)
