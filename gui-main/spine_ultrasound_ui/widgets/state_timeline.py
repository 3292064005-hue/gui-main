from PySide6.QtWidgets import QListWidget, QListWidgetItem


class StateTimeline(QListWidget):
    ORDER = [
        "DISCONNECTED",
        "CONNECTED",
        "POWERED",
        "AUTO_READY",
        "SESSION_LOCKED",
        "PATH_VALIDATED",
        "APPROACHING",
        "CONTACT_SEEKING",
        "SCANNING",
        "PAUSED_HOLD",
        "RETREATING",
        "SCAN_COMPLETE",
        "FAULT",
        "ESTOP",
    ]

    def __init__(self):
        super().__init__()
        for item in self.ORDER:
            self.addItem(QListWidgetItem(item))

    def set_current(self, state: str):
        for i in range(self.count()):
            it = self.item(i)
            it.setSelected(it.text() == state)
