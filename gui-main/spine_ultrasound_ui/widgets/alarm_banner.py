from PySide6.QtWidgets import QLabel


class AlarmBanner(QLabel):
    def __init__(self):
        super().__init__("系统正常 · 所有关键模块处于待命状态")
        self.setObjectName("AlarmBanner")
        self.setProperty("severity", "ok")

    def set_alarm(self, severity: str, message: str):
        severity = (severity or "INFO").upper()
        state = {
            "INFO": "ok",
            "WARN": "warn",
            "WARNING": "warn",
            "ALARM": "danger",
            "ERROR": "danger",
            "ESTOP": "danger",
        }.get(severity, "warn")
        self.setProperty("severity", state)
        self.setText(f"{severity} · {message}")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_normal(self, message: str = "系统正常 · 所有关键模块处于待命状态"):
        self.setProperty("severity", "ok")
        self.setText(message)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
