"""SourceCard Component - Premium card-style container for source selection"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from neoarch.frontend.components.source_item import SourceItem


class _SegmentedButton(QPushButton):
    """Individual segment for the search mode segmented control.

    macOS Settings-style: floating pill for active state with glass background.
    """

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(28)
        self.setObjectName("segmentBtn")
        self.setGraphicsEffect(None)
        self._shadow = None
        self.update_style()

    def update_style(self):
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton#segmentBtn {
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 0, y2: 1,
                        stop: 0 rgba(255, 255, 255, 0.12),
                        stop: 0.5 rgba(255, 255, 255, 0.08),
                        stop: 1 rgba(255, 255, 255, 0.04)
                    );
                    color: #EDEDEF;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 7px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0 14px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton#segmentBtn {
                    background-color: transparent;
                    color: #8B8D97;
                    border: 1px solid transparent;
                    border-radius: 7px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 0 14px;
                }
                QPushButton#segmentBtn:hover {
                    color: #EDEDEF;
                }
            """)

    def nextCheckState(self):
        pass


class SourceCard(QWidget):
    """Premium card component for source selection with elegant controls."""

    source_changed = pyqtSignal(dict)
    search_mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sources = {}
        self.search_mode = 'both'
        self.segment_buttons = []
        self.init_ui()

    def init_ui(self):
        self.setObjectName("SourceCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._build_header(layout)
        self._build_sources_container(layout)
        self._build_search_mode(layout)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        self.setStyleSheet(self._card_stylesheet())

    def _card_stylesheet(self):
        return """
            QWidget#SourceCard {
                background-color: rgba(22, 23, 26, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }
        """

    def _build_header(self, layout):
        header = QWidget()
        header.setObjectName("sourceCardHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("Sources")
        title.setObjectName("sourceCardTitle")
        title.setStyleSheet("""
            QLabel#sourceCardTitle {
                color: #EDEDEF;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.select_all_btn = QPushButton()
        self.select_all_btn.setObjectName("toggleAllBtn")
        self.select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_all_btn.setFixedHeight(22)
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        self.select_all_btn.setStyleSheet(self._toggle_all_style(True))
        header_layout.addWidget(self.select_all_btn)

        layout.addWidget(header)

    def _toggle_all_style(self, all_on):
        text = "Pause All" if all_on else "Enable All"
        self.select_all_btn.setText(text)
        return f"""
            QPushButton#toggleAllBtn {{
                background-color: rgba(0, 191, 174, 0.08);
                color: #00BFAE;
                border: 1px solid rgba(0, 191, 174, 0.2);
                border-radius: 5px;
                padding: 0 10px;
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton#toggleAllBtn:hover {{
                background-color: rgba(0, 191, 174, 0.15);
            }}
        """

    def _build_sources_container(self, layout):
        self.sources_container = QWidget()
        self.sources_container.setObjectName("sourcesContainer")
        self.sources_layout = QVBoxLayout(self.sources_container)
        self.sources_layout.setContentsMargins(8, 0, 8, 4)
        self.sources_layout.setSpacing(3)
        layout.addWidget(self.sources_container)

    def _build_search_mode(self, layout):
        self.search_mode_widget = QWidget()
        self.search_mode_widget.setObjectName("searchModeWidget")
        search_layout = QVBoxLayout(self.search_mode_widget)
        search_layout.setContentsMargins(12, 6, 12, 10)
        search_layout.setSpacing(6)

        search_title = QLabel("Search Mode")
        search_title.setObjectName("searchModeTitle")
        search_layout.addWidget(search_title)

        segment_container = QWidget()
        segment_container.setObjectName("segmentContainer")
        segment_layout = QHBoxLayout(segment_container)
        segment_layout.setContentsMargins(0, 0, 0, 0)
        segment_layout.setSpacing(2)

        self.segment_buttons = []
        for seg_id, seg_text in [("name", "Name"), ("id", "Package ID"), ("both", "Both")]:
            btn = _SegmentedButton(seg_text)
            btn.clicked.connect(lambda checked=False, s=seg_id: self._on_segment_clicked(s))
            btn.setChecked(seg_id == "both")
            segment_layout.addWidget(btn, 1)
            self.segment_buttons.append(btn)

        search_layout.addWidget(segment_container)
        layout.addWidget(self.search_mode_widget)

        shadow = QGraphicsDropShadowEffect(self.search_mode_widget)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.search_mode_widget.setGraphicsEffect(shadow)

        self.search_mode_widget.setStyleSheet("""
            QWidget#searchModeWidget {
                border-top: 1px solid rgba(255, 255, 255, 0.04);
            }
            QLabel#searchModeTitle {
                color: #8B8D97;
                font-size: 10px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
            QWidget#segmentContainer {
                background: rgba(14, 14, 16, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 9px;
                padding: 2px;
            }
        """)

    def _on_segment_clicked(self, seg_id):
        for btn in self.segment_buttons:
            btn.blockSignals(True)
        for btn in self.segment_buttons:
            btn.setChecked(False)
        for btn in self.segment_buttons:
            btn.update_style()
        target = None
        for btn, sid in zip(self.segment_buttons, ["name", "id", "both"]):
            if sid == seg_id:
                btn.setChecked(True)
                btn.update_style()
                target = btn
                break
        for btn in self.segment_buttons:
            btn.blockSignals(False)

        self.search_mode = seg_id
        self.search_mode_changed.emit(seg_id)

    def add_source(self, source_name, icon_path):
        source_item = SourceItem(source_name, icon_path, self)
        source_item.toggle.toggled.connect(lambda checked=False, s=source_name: self.on_source_changed())
        self.sources[source_name] = source_item
        self.sources_layout.addWidget(source_item)
        self.update_toggle_all_button()
        self.on_source_changed()

    def on_source_changed(self):
        states = {name: item.is_checked() for name, item in self.sources.items()}
        self.source_changed.emit(states)
        self.update_toggle_all_button()

    def update_toggle_all_button(self):
        checked_count = sum(1 for item in self.sources.values() if item.is_checked())
        total_count = len(self.sources)
        all_on = checked_count > 0
        self.select_all_btn.setStyleSheet(self._toggle_all_style(all_on))

    def toggle_select_all(self):
        checked_count = sum(1 for item in self.sources.values() if item.is_checked())
        total_count = len(self.sources)
        for item in self.sources.values():
            item.toggle.blockSignals(True)
        if checked_count == total_count:
            for item in self.sources.values():
                item.set_checked(False)
        else:
            for item in self.sources.values():
                item.set_checked(True)
        for item in self.sources.values():
            item.toggle.blockSignals(False)
        states = {name: item.is_checked() for name, item in self.sources.items()}
        self.source_changed.emit(states)
        self.update_toggle_all_button()

    def get_selected_sources(self):
        return {name: item.is_checked() for name, item in self.sources.items()}

    def get_search_mode(self):
        return self.search_mode

    def set_search_mode(self, mode):
        self.search_mode = mode
        for btn, sid in zip(self.segment_buttons, ["name", "id", "both"]):
            btn.blockSignals(True)
            btn.setChecked(sid == mode)
            btn.update_style()
            btn.blockSignals(False)
