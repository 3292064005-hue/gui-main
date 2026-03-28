MAIN_STYLESHEET = """
QMainWindow { background: #F7F9FC; }
QGroupBox {
    border: 1px solid #DCE3EC; border-radius: 10px; margin-top: 10px; font-weight: 700; background: #FFFFFF;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #0F172A; }
QPushButton {
    background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 8px 10px; font-weight: 600;
}
QPushButton:hover { background: #EFF6FF; }
QPushButton#DangerButton { background: #FEE2E2; border: 1px solid #FCA5A5; color: #991B1B; }
QTabWidget::pane { border: 1px solid #DCE3EC; border-radius: 8px; background: #FFFFFF; }
QTabBar::tab {
    background: #E2E8F0; padding: 10px 14px; margin-right: 4px; border-top-left-radius: 8px; border-top-right-radius: 8px;
}
QTabBar::tab:selected { background: #DBEAFE; color: #1D4ED8; font-weight: 700; }
QTextEdit, QLineEdit, QComboBox, QTableView { background: #FFFFFF; border: 1px solid #DCE3EC; border-radius: 8px; }
#LogBox { background: #0F172A; color: #E2E8F0; border-radius: 10px; border: 1px solid #1E293B; }
#StatusCard { background: #FFFFFF; border: 1px solid #DCE3EC; border-radius: 10px; }
#CardTitle { font-size: 13px; color: #475569; font-weight: 700; }
#CardValue { font-size: 18px; color: #0F172A; font-weight: 800; }
#CardExtra { font-size: 12px; color: #64748B; }
#DeviceIndicator { font-size: 16px; }
#AlarmBanner { background: #FDE68A; color: #92400E; padding: 8px; border-radius: 8px; font-weight: 700; }
"""
