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
        self._current_state = ""
        self.setAlternatingRowColors(True)
        self.setSpacing(2)
        for item in self.ORDER:
            self.addItem(QListWidgetItem(item))

    def set_current(self, state: str):
        if state == self._current_state:
            return
        self._current_state = state
        for i in range(self.count()):
            it = self.item(i)
            it.setSelected(it.text() == state)
