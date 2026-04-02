MAIN_STYLESHEET = """
* {
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    color: #1F2937;
}

QMainWindow {
    background: #F3F4F6;
}

QWidget {
    background: transparent;
}

QWidget#MainShell {
    background: #F3F4F6;
}

QLabel {
    color: #1F2937;
    background: transparent;
}

QFrame#TopBanner,
QFrame#PanelCard,
QScrollArea,
QTabWidget::pane,
QGroupBox,
QFrame#StatusCard,
QFrame#HeroCard {
    background: #FFFFFF;
    border: 1px solid #D9DDE3;
    border-radius: 16px;
}

QFrame#HeroCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FBFBFC, stop:1 #EFF2F5);
    border: 1px solid #D7DCE2;
}

QLabel#HeroTitle {
    color: #111827;
    font-size: 24px;
    font-weight: 800;
}

QLabel#HeroSubtitle {
    color: #4B5563;
    font-size: 12px;
}

QFrame#StatusCard[tone="accent"],
QFrame#StatusCard[tone="success"],
QFrame#StatusCard[tone="warning"] {
    border: 1px solid #D8DDE4;
    background: #FBFBFC;
}

QFrame#StatusCard[tone="danger"] {
    border: 1px solid #DDC4C4;
    background: #F8F2F2;
}

QGroupBox {
    margin-top: 13px;
    padding: 11px 11px 9px 11px;
    font-size: 13px;
    font-weight: 700;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #111827;
}

QToolBar {
    background: #F7F8F9;
    border: none;
    border-bottom: 1px solid #D7DCE2;
    spacing: 6px;
    padding: 6px 8px;
}

QToolBar QToolButton {
    background: #FBFBFC;
    border: 1px solid #D3D8DF;
    border-radius: 10px;
    padding: 6px 10px;
    color: #1F2937;
    font-size: 13px;
    font-weight: 600;
}

QToolBar QToolButton:hover {
    background: #F1F3F5;
    border-color: #BCC3CC;
}

QToolBar QToolButton:pressed {
    background: #E7EAEE;
}

QPushButton {
    background: #F5F6F7;
    border: 1px solid #C9CFD6;
    border-radius: 10px;
    padding: 6px 10px;
    min-height: 14px;
    font-size: 13px;
    font-weight: 600;
    color: #1F2937;
}

QPushButton:hover {
    background: #ECEEF1;
    border-color: #B7BEC7;
}

QPushButton:pressed {
    background: #E2E6EA;
}

QPushButton:disabled {
    background: #F7F8F9;
    color: #9AA3AF;
    border-color: #E3E7EC;
}

QPushButton[kind="primary"] {
    background: #E5E7EB;
    border-color: #AAB1BB;
    color: #111827;
}

QPushButton[kind="primary"]:hover {
    background: #DDE1E6;
}

QPushButton[kind="success"] {
    background: #F5F6F7;
    border-color: #C9CFD6;
    color: #1F2937;
}

QPushButton[kind="success"]:hover {
    background: #ECEEF1;
}

QPushButton[kind="warning"] {
    background: #F5F6F7;
    border-color: #C9CFD6;
    color: #1F2937;
}

QPushButton[kind="warning"]:hover {
    background: #ECEEF1;
}

QPushButton[kind="danger"] {
    background: #F6EEEE;
    border-color: #D4B4B4;
    color: #5B1F1F;
}

QPushButton[kind="danger"]:hover {
    background: #F2E4E4;
}

QPushButton[kind="ghost"] {
    background: #FFFFFF;
    border: 1px solid #D6DBE1;
    color: #4B5563;
}

QStatusBar {
    background: #F7F8F9;
    border-top: 1px solid #D7DCE2;
    color: #6B7280;
}

QStatusBar::item {
    border: none;
}

QLabel#StatusPill,
QLabel#HeaderPill,
QLabel#DeviceIndicator,
QLabel#MetricChip {
    padding: 5px 10px;
    border-radius: 10px;
    background: #F5F6F8;
    border: 1px solid #D3D7DE;
    color: #4B5563;
    font-weight: 600;
}

QLabel#HeaderPill {
    padding: 6px 11px;
    border-radius: 12px;
}

QLabel#StatusPill[state="ok"],
QLabel#HeaderPill[state="ok"],
QLabel#DeviceIndicator[state="ok"] {
    background: #EEF3EF;
    border-color: #BFCCBF;
    color: #425B49;
}

QLabel#StatusPill[state="warn"],
QLabel#HeaderPill[state="warn"],
QLabel#DeviceIndicator[state="warn"] {
    background: #F5F0E6;
    border-color: #D9C7A4;
    color: #79643D;
}

QLabel#StatusPill[state="danger"],
QLabel#HeaderPill[state="danger"],
QLabel#DeviceIndicator[state="danger"] {
    background: #F5ECEC;
    border-color: #D9B8B8;
    color: #7B4A4A;
}

QLabel#PageTitle {
    color: #111827;
    font-size: 20px;
    font-weight: 800;
}

QLabel#PageSubtitle,
QLabel#MutedLabel,
QLabel#CardExtra,
QLabel#SectionHint {
    color: #6B7280;
    font-size: 12px;
}

QLabel#SectionTitle {
    color: #111827;
    font-size: 15px;
    font-weight: 700;
}

QLabel#CardTitle {
    font-size: 11px;
    color: #6B7280;
    font-weight: 700;
}

QLabel#CardValue,
QLabel#MetricValue,
QLabel#NumericValue {
    color: #111827;
    font-size: 18px;
    font-weight: 800;
}

QLabel#MetricValue {
    font-size: 16px;
}

QLabel#FieldValue {
    color: #111827;
    font-size: 13px;
    font-weight: 600;
}

QTextEdit,
QLineEdit,
QComboBox,
QTableView,
QListWidget {
    background: #FCFCFD;
    border: 1px solid #D7DCE2;
    border-radius: 12px;
    padding: 8px 10px;
    selection-background-color: #D1D5DB;
    selection-color: #111827;
}

QTextEdit:focus,
QLineEdit:focus,
QComboBox:focus,
QTableView:focus,
QListWidget:focus {
    border: 1px solid #A8B0BA;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QStackedWidget,
QStackedWidget > QWidget {
    background: #FFFFFF;
}

QHeaderView::section {
    background: #F1F3F5;
    color: #374151;
    border: none;
    border-right: 1px solid #D7DCE2;
    border-bottom: 1px solid #D7DCE2;
    padding: 10px 8px;
    font-weight: 700;
}

QTableView {
    gridline-color: #E2E6EA;
    alternate-background-color: #F7F8FA;
}

QProgressBar {
    background: #EEF1F4;
    border: 1px solid #D0D6DD;
    border-radius: 9px;
    text-align: center;
    min-height: 20px;
    color: #374151;
    font-weight: 700;
}

QProgressBar::chunk {
    background: #4B5563;
    border-radius: 8px;
}

QTabBar::tab {
    background: #F1F3F5;
    color: #6B7280;
    border: 1px solid #D7DCE2;
    border-bottom: none;
    padding: 7px 12px;
    margin-right: 6px;
    min-width: 88px;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}

QTabBar::tab:selected {
    background: #FFFFFF;
    color: #111827;
    border-color: #C9CFD6;
    font-weight: 700;
}

QTabBar::tab:hover:!selected {
    background: #ECEFF2;
    color: #374151;
}

QSplitter::handle {
    background: #E5E7EB;
}

QSplitter::handle:horizontal {
    width: 8px;
}

QSplitter::handle:vertical {
    height: 8px;
}

QScrollArea {
    padding: 0px;
}

QScrollBar:vertical {
    background: #F3F4F6;
    width: 12px;
    margin: 4px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #C1C7D0;
    min-height: 40px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #AEB6C0;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical,
QScrollBar:horizontal {
    background: transparent;
    border: none;
    height: 0px;
}

QTextEdit#LogBox {
    background: #F8F9FA;
    color: #374151;
    border-radius: 14px;
    border: 1px solid #D7DCE2;
    font-family: "Consolas", "JetBrains Mono", monospace;
}

QLabel#AlarmBanner {
    border-radius: 14px;
    padding: 9px 14px;
    font-weight: 700;
    background: #EEF3EF;
    border: 1px solid #BFCCBF;
    color: #425B49;
}

QLabel#AlarmBanner[severity="warn"] {
    background: #F5F0E6;
    border-color: #D9C7A4;
    color: #79643D;
}

QLabel#AlarmBanner[severity="danger"] {
    background: #F5ECEC;
    border-color: #D9B8B8;
    color: #7B4A4A;
}

#ImageViewport {
    background: #F7F8FA;
    border: 1px dashed #CBD2D9;
    border-radius: 14px;
    color: #8A94A3;
    font-size: 13px;
    font-weight: 600;
}

QLabel#ImageCaption {
    color: #6B7280;
    font-size: 12px;
}

QListWidget::item {
    padding: 8px 10px;
    margin: 3px 0;
    border-radius: 10px;
}

QListWidget::item:selected {
    background: #E5E7EB;
    color: #111827;
    border: 1px solid #C3C9D1;
}
"""
