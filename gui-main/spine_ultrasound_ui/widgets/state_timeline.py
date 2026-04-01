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
        "CONTACT_STABLE",
        "SCANNING",
        "PAUSED_HOLD",
        "RETREATING",
        "SCAN_COMPLETE",
        "FAULT",
        "ESTOP",
    ]

    def __init__(self):
        super().__init__()
        self.setAlternatingRowColors(True)
        self.setSpacing(2)
        for item in self.ORDER:
            self.addItem(QListWidgetItem(item))

    def set_current(self, state: str):
        for i in range(self.count()):
            it = self.item(i)
            active = it.text() == state
            it.setSelected(active)
            if active:
                self.scrollToItem(it)
