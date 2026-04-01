from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout


class ImagePane(QGroupBox):
    def __init__(self, title: str, caption: str = "等待图像流接入"):
        super().__init__(title)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        self.label = QLabel("等待图像流")
        self.label.setObjectName("ImageViewport")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumSize(360, 240)
        self.caption_label = QLabel(caption)
        self.caption_label.setObjectName("ImageCaption")
        self.caption_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.label)
        layout.addWidget(self.caption_label)

    def set_pixmap(self, pix: QPixmap):
        if pix.isNull():
            return
        self.caption_label.setText("实时图像已更新")
        self.label.setPixmap(pix.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        pixmap = self.label.pixmap()
        if pixmap is not None:
            self.label.setPixmap(pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        super().resizeEvent(event)
