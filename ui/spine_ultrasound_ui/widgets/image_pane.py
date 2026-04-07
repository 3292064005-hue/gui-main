from __future__ import annotations

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget


class _PixmapViewport(QWidget):
    def __init__(self, placeholder_text: str):
        super().__init__()
        self._placeholder_text = placeholder_text
        self._pixmap: QPixmap | None = None
        self.setObjectName("ImageViewport")
        self.setMinimumSize(360, 220)

    def sizeHint(self) -> QSize:
        return QSize(720, 405)

    def minimumSizeHint(self) -> QSize:
        return QSize(360, 220)

    def set_display_pixmap(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        self.update()

    def pixmap(self) -> QPixmap | None:
        return self._pixmap

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        frame_rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QColor("#F7F8FA"))
        painter.setPen(QPen(QColor("#CBD2D9"), 1, Qt.DashLine))
        painter.drawRoundedRect(frame_rect, 14, 14)

        if self._pixmap is not None and not self._pixmap.isNull():
            x = max(0, (self.width() - self._pixmap.width()) // 2)
            y = max(0, (self.height() - self._pixmap.height()) // 2)
            painter.drawPixmap(x, y, self._pixmap)
        else:
            painter.setPen(QColor("#8A94A3"))
            painter.drawText(self.rect(), Qt.AlignCenter, self._placeholder_text)
        painter.end()


class ImagePane(QGroupBox):
    def __init__(self, title: str, caption: str = "等待图像流接入"):
        super().__init__(title)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 10)
        layout.setSpacing(10)
        self._source_pixmap: QPixmap | None = None
        self._last_render_size: tuple[int, int] | None = None
        self._defer_render = True
        self._resize_timer = QTimer(self)
        if hasattr(self._resize_timer, "setSingleShot"):
            self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._flush_deferred_refresh)
        self.label = _PixmapViewport("等待图像流")
        self.caption_label = QLabel(caption)
        self.caption_label.setObjectName("ImageCaption")
        self.caption_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.caption_label.setWordWrap(True)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.caption_label)

    def set_pixmap(self, pix: QPixmap):
        if pix.isNull():
            return
        self._source_pixmap = pix
        self._last_render_size = None
        self.caption_label.setText("实时图像已更新")
        if not self.isVisible():
            return
        if self._defer_render or self._timer_is_active():
            return
        self._refresh_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_refresh(260)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._defer_render = True
        self._last_render_size = None
        if hasattr(self._resize_timer, "stop"):
            self._resize_timer.stop()

    def _schedule_refresh(self, delay_ms: int = 260) -> None:
        self._defer_render = True
        if hasattr(self._resize_timer, "stop"):
            self._resize_timer.stop()
        self._resize_timer.start(delay_ms)

    def _flush_deferred_refresh(self) -> None:
        self._defer_render = False
        self._refresh_pixmap()

    def _timer_is_active(self) -> bool:
        is_active = getattr(self._resize_timer, "isActive", None)
        if callable(is_active):
            return bool(is_active())
        return False

    def _refresh_pixmap(self) -> None:
        if self._source_pixmap is None or self._source_pixmap.isNull():
            return
        if not self.isVisible():
            return

        target_size = self.label.size()
        if target_size.width() < 8 or target_size.height() < 8:
            return

        render_size = (target_size.width(), target_size.height())
        if self._last_render_size == render_size:
            return

        self.label.set_display_pixmap(
            self._source_pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self._last_render_size = render_size
