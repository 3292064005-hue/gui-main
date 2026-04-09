from __future__ import annotations

import base64

try:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QGuiApplication
except ImportError:  # pragma: no cover
    QBuffer = QByteArray = QIODevice = QGuiApplication = None  # type: ignore


def _ensure_qt_app() -> bool:
    if QGuiApplication is None:
        return False
    app = QGuiApplication.instance()
    if app is None:
        QGuiApplication([])
    return True


class HeadlessFrameSurfaceService:
    """Render compatibility camera/ultrasound frames for headless feeds."""

    @staticmethod
    def static_png_base64() -> str:
        return 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Ww2cQAAAABJRU5ErkJggg=='

    def frame_base64(self, *, mode: str, phase: float) -> str:
        if not _ensure_qt_app() or QBuffer is None or QByteArray is None or QIODevice is None:
            return self.static_png_base64()
        from PySide6.QtCore import Qt, QRectF
        from PySide6.QtGui import QColor, QPainter, QPixmap

        pixmap = QPixmap(640, 360)
        pixmap.fill(QColor('#0F172A' if mode == 'camera' else '#111827'))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#38BDF8' if mode == 'camera' else '#A78BFA'))
        x = 40 + int((phase % 6.0) * 80)
        painter.drawRoundedRect(QRectF(x, 120, 180, 96), 22, 22)
        painter.end()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, 'PNG')
        return base64.b64encode(bytes(data)).decode('ascii')
