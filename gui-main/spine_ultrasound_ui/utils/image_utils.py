import math
from PySide6.QtGui import QColor, QPainter, QPixmap


def generate_demo_pixmap(width: int, height: int, mode: str, phase: float = 0.0) -> QPixmap:
    pix = QPixmap(width, height)
    pix.fill(QColor("#0F172A"))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QColor("#1E293B"))
    for x in range(0, width, 30):
        painter.drawLine(x, 0, x, height)
    for y in range(0, height, 30):
        painter.drawLine(0, y, width, y)
    if mode == "camera":
        painter.setPen(QColor("#60A5FA"))
        painter.setBrush(QColor(96, 165, 250, 40))
        painter.drawRoundedRect(30, 30, width - 60, height - 60, 20, 20)
        painter.setPen(QColor("#22C55E"))
        cx = width // 2 + int(math.sin(phase) * 40)
        painter.drawLine(cx, 40, cx, height - 40)
        painter.drawText(20, 24, "Camera / 背部定位视图")
    elif mode == "ultrasound":
        painter.setPen(QColor("#E2E8F0"))
        painter.drawText(20, 24, "Ultrasound / 超声实时图像")
        for i in range(24):
            y = 40 + i * 12
            intensity = int(80 + 120 * abs(math.sin(i * 0.4 + phase)))
            painter.setPen(QColor(intensity, intensity, intensity))
            painter.drawLine(20, y, width - 20, y + int(math.sin(i + phase) * 6))
        painter.setPen(QColor("#F59E0B"))
        painter.drawEllipse(width // 2 - 30, height // 2 - 30, 60, 60)
    elif mode == "reconstruction":
        painter.setPen(QColor("#A78BFA"))
        painter.drawText(20, 24, "Reconstruction / 局部重建结果")
        points = []
        for i in range(12):
            x = 60 + i * ((width - 120) / 11)
            y = height // 2 + math.sin(i * 0.55 + phase) * 70
            points.append((x, y))
        for i in range(len(points) - 1):
            painter.drawLine(int(points[i][0]), int(points[i][1]), int(points[i + 1][0]), int(points[i + 1][1]))
        painter.setBrush(QColor("#8B5CF6"))
        for x, y in points:
            painter.drawEllipse(int(x) - 4, int(y) - 4, 8, 8)
    else:
        painter.setPen(QColor("#CBD5E1"))
        painter.drawText(20, 24, mode)
    painter.end()
    return pix
