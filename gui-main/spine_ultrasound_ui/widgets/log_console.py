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
            "INFO": "#67E8F9",
            "WARN": "#FBBF24",
            "ERROR": "#FCA5A5",
            "ALARM": "#F87171",
        }
        ts = datetime.now().strftime("%H:%M:%S")
        level = (level or "INFO").upper()
        color = colors.get(level, "#C7D2FE")
        self.append(
            f'<span style="color:#64748B;">[{ts}]</span> '
            f'<span style="color:{color}; font-weight:700;">[{level}]</span> '
            f'<span style="color:#E2E8F0;">{message}</span>'
        )
