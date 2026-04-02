from datetime import datetime

from PySide6.QtWidgets import QTextEdit


class LogConsole(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setObjectName("LogBox")
        self.setPlaceholderText("系统日志、事件流与安全提示将在这里显示。")

    def append_colored(self, level: str, message: str):
        colors = {
            "INFO": "#4B5563",
            "WARN": "#79643D",
            "ERROR": "#7B4A4A",
            "ALARM": "#7B4A4A",
        }
        ts = datetime.now().strftime("%H:%M:%S")
        level = (level or "INFO").upper()
        color = colors.get(level, "#4B5563")
        self.append(
            f'<span style="color:#6B7280;">[{ts}]</span> '
            f'<span style="color:{color}; font-weight:700;">[{level}]</span> '
            f'<span style="color:#1F2937;">{message}</span>'
        )
