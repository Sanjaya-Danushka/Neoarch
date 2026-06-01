# styles.py - Styles component for Aurora application

DARK_STYLESHEET = """
QMainWindow {
    background-color: #1E1E1E;
    color: #F0F0F0;
}

QWidget {
    background-color: #1E1E1E;
    color: #F0F0F0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

QLineEdit {
    background-color: rgba(42, 45, 51, 0.8);
    color: #F0F0F0;
    border: 2px solid rgba(0, 191, 174, 0.2);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 14px;
    selection-background-color: #00BFAE;
}

QLineEdit:focus {
    background-color: rgba(42, 45, 51, 0.9);
    border: 2px solid #00BFAE;
    outline: none;
}

QPushButton {
    background-color: rgba(42, 45, 51, 0.6);
    color: #F0F0F0;
    border: 1px solid rgba(0, 191, 174, 0.2);
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background-color: rgba(42, 45, 51, 0.8);
    border-color: rgba(0, 191, 174, 0.4);
}

QPushButton:pressed {
    background-color: rgba(42, 45, 51, 0.9);
}

QPushButton#sidebarBtn {
    background-color: transparent;
    border: none;
    color: #C9C9C9;
    padding: 12px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    border-radius: 6px;
}

QPushButton#sidebarBtn:hover {
    background-color: rgba(42, 45, 51, 0.5);
    color: #F0F0F0;
}

QPushButton#navBtn {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-size: 11px;
    font-weight: 500;
    padding: 0px;
    margin: 8px 0px;
    min-height: 100px;
    max-width: 150px;
    text-align: center;
}

QPushButton#navBtn:hover {
    background-color: rgba(0, 191, 174, 0.1);
    border: none;
}

QPushButton#navBtn:checked {
    background-color: rgba(0, 191, 174, 0.15);
    border: none;
}

QPushButton#navBtn:pressed {
}

QLabel#navIcon {
    background-color: transparent;
    border-radius: 8px;
    font-size: 26px;
    color: #e1e5e9;
}

/* Nav icon container and badge */
QWidget#navIconContainer {
    background-color: transparent;
}

QLabel#navBadge {
    background-color: #E53935;
    color: #FFFFFF;
    border-radius: 9px; /* keep circular for 18px height, will expand width */
    padding: 0px 4px; /* allow dynamic width for multi-digit counts */
    min-width: 18px;
    min-height: 18px;
}

QPushButton#navBtn:hover QLabel#navIcon {
    background-color: transparent;
    color: #ffffff;
}

QPushButton#navBtn:checked QLabel#navIcon {
    background-color: transparent;
    color: #ffffff;
}

QLabel#navText {
    color: #e1e5e9;
    font-weight: 400;
    font-size: 10px;
    letter-spacing: 0.8px;
    margin-top: 4px;
    text-transform: uppercase;
}

QPushButton#bottomCardBtn {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-size: 11px;
    font-weight: 500;
    padding: 0px;
    margin: 0px;
    min-height: 60px;
    max-width: 150px;
    text-align: center;
}

QPushButton#bottomCardBtn:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.2);
}

QPushButton#bottomCardBtn:pressed {
    background-color: rgba(255, 255, 255, 0.15);
}

QPushButton#bottomCardBtn QLabel {
    color: #ffffff;
}

QLabel#bottomCardIcon {
    background-color: transparent;
    border-radius: 6px;
    font-size: 18px;
    color: #ffffff;
}

QPushButton#bottomCardBtn:hover QLabel#bottomCardIcon {
    background-color: transparent;
}

QLabel#bottomCardText {
    color: #e1e5e9;
    font-weight: 400;
    font-size: 10px;
    letter-spacing: 0.8px;
    margin-top: 4px;
    text-transform: uppercase;
}

QPushButton#bottomCardBtn:hover QLabel#bottomCardText {
    color: #ffffff;
}

QWidget#sidebar {
    border-right: 1px solid rgba(0, 191, 174, 0.1);
}

QLabel#sidebarHeader {
    color: #ffffff;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: 1px;
    text-align: center;
    padding: 10px 0;
    margin-bottom: 10px;
}

QTableWidget {
    background-color: rgba(42, 45, 51, 0.8);
    alternate-background-color: #2B2E34;
    gridline-color: rgba(0, 191, 174, 0.1);
    border: 1px solid rgba(0, 191, 174, 0.1);
    border-radius: 8px;
    selection-background-color: rgba(0, 191, 174, 0.3);
    selection-color: #F0F0F0;
}

QTableWidget::item {
    padding: 12px 8px;
    border: none;
    border-bottom: 1px solid rgba(0, 191, 174, 0.05);
}

QTableWidget::item:selected {
    background-color: rgba(0, 191, 174, 0.2);
    color: #F0F0F0;
}

QTableWidget::item:alternate {
    background-color: #25282E;
}

QHeaderView::section {
    background-color: #33373E;
    color: #00BFAE;
    padding: 12px 8px;
    border: none;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 2px solid rgba(0, 191, 174, 0.2);
}

QTextEdit {
    background-color: rgba(42, 45, 51, 0.8);
    color: #C9C9C9;
    border: 1px solid rgba(0, 191, 174, 0.1);
    border-radius: 6px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    padding: 8px;
}

QLabel {
    color: #F0F0F0;
}

QLabel#headerLabel {
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
}

QLabel#sectionLabel {
    color: #00BFAE;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QFrame {
    background-color: transparent;
    border: none;
}

QCheckBox {
    color: #F0F0F0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid rgba(0, 191, 174, 0.4);
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox::indicator:checked {
    background-color: #00BFAE;
    border: 2px solid #00BFAE;
}

QCheckBox::indicator:unchecked {
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox::indicator:hover {
    border-color: rgba(0, 191, 174, 0.8);
}

QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget::item:hover {
    background-color: rgba(0, 191, 174, 0.1);
}

QListWidget::item:selected {
    background-color: rgba(0, 191, 174, 0.2);
    color: #00BFAE;
}

/* Discover section specific styling */
QTableWidget#discoverTable {
    background-color: #2A2D33;
    alternate-background-color: #2B2E34;
    border: 1px solid rgba(0, 191, 174, 0.1);
    border-radius: 4px;
    box-shadow: none;
}

QTableWidget#discoverTable::item {
    padding: 16px 14px;
    border-bottom: 1px solid rgba(0, 191, 174, 0.05);
}

QTableWidget#discoverTable::item:hover {
    background-color: rgba(0, 191, 174, 0.05);
}

QTableWidget#discoverTable::item:alternate {
    background-color: #25282E;
}

QTableWidget#discoverTable::item:selected {
background-color: rgba(0, 191, 174, 0.1);
border-left: 2px solid #00BFAE;
}

QHeaderView::section {
background-color: transparent;
color: #C9C9C9;
padding: 8px 12px;
border: none;
font-weight: 500;
font-size: 11px;
text-transform: uppercase;
letter-spacing: 0.5px;
border-bottom: 1px solid rgba(0, 191, 174, 0.1);
border-radius: 0px;
}

QWidget#sourceChip {
background-color: rgba(0, 191, 174, 0.12);
border: 1px solid rgba(0, 191, 174, 0.35);
border-radius: 12px;
}

QWidget#sourceChip QLabel {
color: #EAF6F5;
font-size: 12px;
padding: 0px;
margin: 0px;
}

QCheckBox#tableCheckbox {
    color: #F0F0F0;
    font-size: 13px;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox#tableCheckbox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 10px;
    border: 2px solid rgba(0, 191, 174, 0.4);
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox#tableCheckbox::indicator:checked {
    background-color: #00BFAE;
    border: 2px solid #00BFAE;
}

QCheckBox#tableCheckbox::indicator:unchecked {
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox#tableCheckbox::indicator:hover {
    border-color: rgba(0, 191, 174, 0.8);
}

/* Progress bar styling */
QProgressBar {
border: 2px solid rgba(0, 191, 174, 0.2);
border-radius: 4px;
text-align: center;
background-color: rgba(42, 45, 51, 0.6);
    background-color: rgba(42, 45, 51, 0.6);
}

QProgressBar::chunk {
    background-color: #00BFAE;
    border-radius: 2px;
}

/* Loading spinner styles */
QWidget#loadingSpinner {
    background-color: transparent;
    border: none;
}

QWidget#loadingSpinner QLabel {
    background-color: transparent;
    color: #00BFAE;
    font-size: 14px;
    font-weight: 500;
}

/* SourceItem component styles */
SourceItem {
    background-color: transparent;
    border-radius: 8px;
    margin: 2px 0px;
}

SourceItem:hover {
    background-color: rgba(0, 191, 174, 0.05);
    border-radius: 8px;
}

QWidget#sourceIconContainer {
    background-color: rgba(0, 191, 174, 0.1);
    border: 1px solid rgba(0, 191, 174, 0.3);
    border-radius: 8px;
}

QWidget#sourceIconContainer:checked {
    background-color: rgba(0, 191, 174, 0.2);
    border-color: rgba(0, 191, 174, 0.6);
}

QCheckBox#sourceCheckbox {
    color: #F0F0F0;
    font-size: 13px;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox#sourceCheckbox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 10px;
    border: 2px solid rgba(0, 191, 174, 0.4);
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox#sourceCheckbox::indicator:checked {
    background-color: #00BFAE;
    border: 2px solid #00BFAE;
}

QCheckBox#sourceCheckbox::indicator:unchecked {
    background-color: rgba(42, 45, 51, 0.8);
}

QCheckBox#sourceCheckbox::indicator:hover {
    border-color: rgba(0, 191, 174, 0.8);
}

/* SourceSelector component styles */
SourceSelector {
    background-color: rgba(42, 45, 51, 0.3);
    border-radius: 10px;
    border: 1px solid rgba(0, 191, 174, 0.1);
}

QLabel#sourceSelectorTitle {
    color: #00BFAE;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 8px 0px;
}

QPushButton#selectAllBtn {
    background-color: transparent;
    color: #00BFAE;
    border: 1px solid rgba(0, 191, 174, 0.3);
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QPushButton#selectAllBtn:hover {
    background-color: rgba(0, 191, 174, 0.1);
    border-color: rgba(0, 191, 174, 0.5);
}

QPushButton#selectAllBtn:pressed {
    background-color: rgba(0, 191, 174, 0.2);
}

/* SourceCard component styles */
SourceCard {
    background-color: rgba(42, 45, 51, 0.4);
    border-radius: 12px;
    border: 1px solid rgba(0, 191, 174, 0.2);
    margin: 4px 0px;
}

QLabel#sourceCardTitle {
    color: #00BFAE;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* FilterCard component styles */
FilterCard {
    background-color: rgba(42, 45, 51, 0.4);
    border-radius: 12px;
    border: 1px solid rgba(0, 191, 174, 0.2);
    margin: 4px 0px;
}

QLabel#filterCardTitle {
    color: #00BFAE;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Scroll Bar Styling - Dark Rounded */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 12px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: rgba(60, 60, 60, 0.7);
    border-radius: 6px;
    min-height: 20px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(80, 80, 80, 0.9);
}

QScrollBar::handle:vertical:pressed {
    background: rgba(100, 100, 100, 1);
}

QScrollBar::add-line:vertical {
    border: none;
    background: transparent;
    height: 0px;
}

QScrollBar::sub-line:vertical {
    border: none;
    background: transparent;
    height: 0px;
}

QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
    border: none;
    width: 0px;
    height: 0px;
    background: transparent;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 12px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal {
    background: rgba(60, 60, 60, 0.7);
    border-radius: 6px;
    min-width: 20px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(80, 80, 80, 0.9);
}

QScrollBar::handle:horizontal:pressed {
    background: rgba(100, 100, 100, 1);
}

QScrollBar::add-line:horizontal {
    border: none;
    background: transparent;
    width: 0px;
}

QScrollBar::sub-line:horizontal {
    border: none;
    background: transparent;
    width: 0px;
}

QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
    border: none;
    width: 0px;
    height: 0px;
    background: transparent;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}

QScrollArea::corner {
    background: transparent;
    border: none;
}
"""


class Styles:
    """Styles component for managing application styling"""

    @staticmethod
    def get_dark_stylesheet():
        """Return the main dark theme stylesheet"""
        return DARK_STYLESHEET

    @staticmethod
    def get_header_stylesheet():
        """Return stylesheet for header frame"""
        return """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #20232A, stop:1 #1E1E1E);
                border-bottom: 1px solid rgba(0, 191, 174, 0.1);
            }
        """

    @staticmethod
    def get_filters_panel_stylesheet():
        """Return stylesheet for filters panel"""
        return """
            QFrame {
                background-color: #0f0f0f;
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            }
        """

    @staticmethod
    def get_separator_stylesheet():
        """Return stylesheet for visual separator"""
        return """
            QFrame {
                color: rgba(0, 191, 174, 0.2);
                background-color: rgba(0, 191, 174, 0.1);
                margin: 8px 0;
                max-height: 1px;
            }
        """

    @staticmethod
    def get_spinner_label_stylesheet():
        """Return stylesheet for spinner label"""
        return """
            QLabel {
                font-size: 32px;
                color: #00BFAE;
            }
        """
