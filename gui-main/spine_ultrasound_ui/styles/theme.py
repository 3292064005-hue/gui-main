MAIN_STYLESHEET = """
* {
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    color: #D9E2F2;
}

QMainWindow {
    background: #0B1220;
}

QWidget {
    background: transparent;
}

QLabel {
    color: #D9E2F2;
}

QFrame#TopBanner,
QFrame#PanelCard,
QScrollArea,
QTabWidget::pane,
QGroupBox,
QFrame#StatusCard,
QFrame#HeroCard {
    background: #121A2A;
    border: 1px solid #23324B;
    border-radius: 16px;
}

QFrame#HeroCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #14213A, stop:1 #101827);
    border: 1px solid #2B4167;
}

QFrame#StatusCard[tone="accent"] {
    border: 1px solid #335A9A;
    background: #111D34;
}

QFrame#StatusCard[tone="success"] {
    border: 1px solid #1C6A57;
    background: #0F221F;
}

QFrame#StatusCard[tone="warning"] {
    border: 1px solid #8A5A1F;
    background: #251B10;
}

QFrame#StatusCard[tone="danger"] {
    border: 1px solid #8C3441;
    background: #2A1218;
}

QGroupBox {
    margin-top: 16px;
    padding: 14px 14px 12px 14px;
    font-size: 14px;
    font-weight: 700;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: #F8FAFC;
}

QToolBar {
    background: #0E1626;
    border: none;
    border-bottom: 1px solid #23324B;
    spacing: 6px;
    padding: 8px 10px;
}

QToolBar QToolButton {
    background: #121A2A;
    border: 1px solid #2A3954;
    border-radius: 10px;
    padding: 9px 14px;
    color: #E8EEF8;
    font-weight: 600;
}

QToolBar QToolButton:hover {
    background: #16233A;
    border-color: #3A5E9D;
}

QToolBar QToolButton:pressed {
    background: #1A2E4E;
}

QPushButton {
    background: #162033;
    border: 1px solid #2E405F;
    border-radius: 10px;
    padding: 10px 14px;
    min-height: 18px;
    font-weight: 600;
    color: #E5ECF7;
}

QPushButton:hover {
    background: #1A2841;
    border-color: #40669F;
}

QPushButton:pressed {
    background: #1E3354;
}

QPushButton:disabled {
    background: #101826;
    color: #60708D;
    border-color: #213148;
}

QPushButton[kind="primary"] {
    background: #1D4ED8;
    border-color: #2563EB;
    color: white;
}

QPushButton[kind="primary"]:hover {
    background: #2563EB;
}

QPushButton[kind="success"] {
    background: #0F766E;
    border-color: #14B8A6;
    color: white;
}

QPushButton[kind="success"]:hover {
    background: #0D8B81;
}

QPushButton[kind="warning"] {
    background: #9A3412;
    border-color: #EA580C;
    color: white;
}

QPushButton[kind="warning"]:hover {
    background: #B45309;
}

QPushButton[kind="danger"] {
    background: #991B1B;
    border-color: #DC2626;
    color: white;
}

QPushButton[kind="danger"]:hover {
    background: #B91C1C;
}

QPushButton[kind="ghost"] {
    background: transparent;
    border: 1px dashed #425B82;
    color: #BFD0E9;
}

QStatusBar {
    background: #0E1626;
    border-top: 1px solid #23324B;
    color: #A6B4CA;
}

QStatusBar::item {
    border: none;
}

QLabel#StatusPill,
QLabel#HeaderPill,
QLabel#DeviceIndicator,
QLabel#MetricChip {
    padding: 6px 10px;
    border-radius: 10px;
    background: #162033;
    border: 1px solid #293B59;
    color: #DCE6F5;
    font-weight: 600;
}

QLabel#HeaderPill {
    padding: 8px 12px;
    border-radius: 12px;
}

QLabel#StatusPill[state="ok"],
QLabel#HeaderPill[state="ok"],
QLabel#DeviceIndicator[state="ok"] {
    background: #102621;
    border-color: #1C6A57;
    color: #6EE7B7;
}

QLabel#StatusPill[state="warn"],
QLabel#HeaderPill[state="warn"],
QLabel#DeviceIndicator[state="warn"] {
    background: #271C11;
    border-color: #8A5A1F;
    color: #FBBF24;
}

QLabel#StatusPill[state="danger"],
QLabel#HeaderPill[state="danger"],
QLabel#DeviceIndicator[state="danger"] {
    background: #2A1218;
    border-color: #8C3441;
    color: #FCA5A5;
}

QLabel#PageTitle {
    color: #F8FAFC;
    font-size: 24px;
    font-weight: 800;
}

QLabel#PageSubtitle,
QLabel#MutedLabel,
QLabel#CardExtra,
QLabel#SectionHint {
    color: #8FA2BF;
    font-size: 12px;
}

QLabel#SectionTitle {
    color: #F8FAFC;
    font-size: 15px;
    font-weight: 700;
}

QLabel#CardTitle {
    font-size: 12px;
    color: #93A5C2;
    font-weight: 700;
}

QLabel#CardValue,
QLabel#MetricValue,
QLabel#NumericValue {
    color: #F8FAFC;
    font-size: 22px;
    font-weight: 800;
}

QLabel#MetricValue {
    font-size: 18px;
}

QLabel#FieldValue {
    color: #F8FAFC;
    font-size: 14px;
    font-weight: 600;
}

QTextEdit,
QLineEdit,
QComboBox,
QTableView,
QListWidget {
    background: #0F1726;
    border: 1px solid #253752;
    border-radius: 12px;
    padding: 8px 10px;
    selection-background-color: #1D4ED8;
    selection-color: white;
}

QTextEdit:focus,
QLineEdit:focus,
QComboBox:focus,
QTableView:focus,
QListWidget:focus {
    border: 1px solid #3B82F6;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QHeaderView::section {
    background: #131E31;
    color: #D6E2F2;
    border: none;
    border-right: 1px solid #24364E;
    border-bottom: 1px solid #24364E;
    padding: 10px 8px;
    font-weight: 700;
}

QTableView {
    gridline-color: #22324A;
    alternate-background-color: #111B2B;
}

QProgressBar {
    background: #0E1522;
    border: 1px solid #253752;
    border-radius: 9px;
    text-align: center;
    min-height: 20px;
    color: #E6EEF8;
    font-weight: 700;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0EA5E9, stop:1 #2563EB);
    border-radius: 8px;
}

QTabBar::tab {
    background: #111A29;
    color: #91A4C1;
    border: 1px solid #22324A;
    border-bottom: none;
    padding: 10px 16px;
    margin-right: 6px;
    min-width: 96px;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}

QTabBar::tab:selected {
    background: #16253B;
    color: #F8FAFC;
    border-color: #3A5E9D;
    font-weight: 700;
}

QTabBar::tab:hover:!selected {
    background: #142033;
    color: #D7E5F7;
}

QSplitter::handle {
    background: #0E1626;
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
    background: #0E1626;
    width: 12px;
    margin: 4px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #324967;
    min-height: 40px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #40669F;
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
    background: #09111D;
    color: #D8E5F4;
    border-radius: 14px;
    border: 1px solid #22324A;
    font-family: "Consolas", "JetBrains Mono", monospace;
}

QLabel#AlarmBanner {
    border-radius: 14px;
    padding: 12px 16px;
    font-weight: 700;
    background: #102621;
    border: 1px solid #1C6A57;
    color: #6EE7B7;
}

QLabel#AlarmBanner[severity="warn"] {
    background: #271C11;
    border-color: #8A5A1F;
    color: #FBBF24;
}

QLabel#AlarmBanner[severity="danger"] {
    background: #2A1218;
    border-color: #8C3441;
    color: #FCA5A5;
}

QLabel#ImageViewport {
    background: #09111D;
    border: 1px dashed #304865;
    border-radius: 14px;
    color: #7F95B7;
    font-size: 13px;
    font-weight: 600;
}

QLabel#ImageCaption {
    color: #8FA2BF;
    font-size: 12px;
}

QListWidget::item {
    padding: 8px 10px;
    margin: 3px 0;
    border-radius: 10px;
}

QListWidget::item:selected {
    background: #17325E;
    color: #FFFFFF;
    border: 1px solid #3A5E9D;
}
"""
