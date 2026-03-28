from PySide6.QtWidgets import QLabel


class AlarmBanner(QLabel):
    def __init__(self):
        super().__init__("系统正常")
        self.setObjectName("AlarmBanner")

    def set_alarm(self, severity: str, message: str):
        self.setText(f"{severity}: {message}")
