from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("系统设置页：全局配置 / 设备配置 / 扫查配置 / 接触配置 / 质量配置 / 导出配置"))
