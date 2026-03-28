from PySide6.QtWidgets import QTextEdit


class LogConsole(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setObjectName("LogBox")

    def append_colored(self, level: str, message: str):
        colors = {
            "INFO": "#0F766E",
            "WARN": "#B45309",
            "ERROR": "#B91C1C",
            "ALARM": "#DC2626",
        }
        color = colors.get(level, "#334155")
        self.append(f'<span style="color:{color};">{message}</span>')
