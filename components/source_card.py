"""
SourceCard Component - Card-style container for source selection
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QButtonGroup, QGraphicsDropShadowEffect
from PyQt6.QtCore import pyqtSignal
from .source_item import SourceItem


class SourceCard(QWidget):
    """Card component for source selection with select/deselect functionality"""

    source_changed = pyqtSignal(dict)  # Emits dict of source_name -> is_checked
    search_mode_changed = pyqtSignal(str)  # Emits search mode: 'name', 'id', or 'both'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sources = {}
        self.search_mode = 'both'  # Default search mode
        self.radio_group = None
        self.init_ui()

    def init_ui(self):
        """Initialize the source card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header with select/deselect button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title_label = QLabel("Sources")
        title_label.setObjectName("sourceCardTitle")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setObjectName("selectAllBtn")
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        header_layout.addWidget(self.select_all_btn)

        layout.addWidget(header_widget)

        # Container for source items
        self.sources_container = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_container)
        self.sources_layout.setContentsMargins(6, 4, 6, 4)
        self.sources_layout.setSpacing(6)

        layout.addWidget(self.sources_container)

        # Search Mode Section
        search_mode_widget = QWidget()
        search_layout = QVBoxLayout(search_mode_widget)
        search_layout.setContentsMargins(12, 8, 12, 8)
        search_layout.setSpacing(6)

        search_title = QLabel("Search Mode")
        search_title.setObjectName("searchModeTitle")
        search_layout.addWidget(search_title)

        # Radio button container
        radio_container = QWidget()
        radio_layout = QHBoxLayout(radio_container)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        radio_layout.setSpacing(12)

        # Create button group for radio buttons
        self.radio_group = QButtonGroup(self)

        # Name radio button
        self.name_radio = QRadioButton("Name")
        self.name_radio.setObjectName("searchModeRadio")
        self.radio_group.addButton(self.name_radio, 0)
        radio_layout.addWidget(self.name_radio)

        # Package ID radio button
        self.id_radio = QRadioButton("Package ID")
        self.id_radio.setObjectName("searchModeRadio")
        self.radio_group.addButton(self.id_radio, 1)
        radio_layout.addWidget(self.id_radio)

        # Both radio button (default)
        self.both_radio = QRadioButton("Both")
        self.both_radio.setObjectName("searchModeRadio")
        self.both_radio.setChecked(True)  # Default selection
        self.radio_group.addButton(self.both_radio, 2)
        radio_layout.addWidget(self.both_radio)

        radio_layout.addStretch()
        search_layout.addWidget(radio_container)

        layout.addWidget(search_mode_widget)

        # Connect radio button signals
        self.radio_group.buttonClicked.connect(self.on_search_mode_changed)

        # Subtle drop shadow for the entire card
        try:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(18)
            shadow.setOffset(0, 2)
            from PyQt6.QtGui import QColor as _QColor
            shadow.setColor(_QColor(0, 0, 0, 80))
            self.setGraphicsEffect(shadow)
        except ImportError:
            # Handle missing graphics effect support gracefully
            pass

        # Apply styling
        self.setStyleSheet(self.get_stylesheet())

    def add_source(self, source_name, icon_path):
        """Add a source to the card"""
        source_item = SourceItem(source_name, icon_path, self)
        source_item.checkbox.stateChanged.connect(lambda: self.on_source_changed())
        self.sources[source_name] = source_item
        self.sources_layout.addWidget(source_item)

        # Initial state change emission
        self.on_source_changed()

    def on_source_changed(self):
        """Handle when any source selection changes"""
        states = {name: item.checkbox.isChecked() for name, item in self.sources.items()}
        self.source_changed.emit(states)
        self.update_select_all_button()

    def update_select_all_button(self):
        """Update the select all button text based on current state"""
        checked_count = sum(1 for item in self.sources.values() if item.checkbox.isChecked())
        total_count = len(self.sources)

        if checked_count == total_count:
            self.select_all_btn.setText("Deselect All")
        elif checked_count == 0:
            self.select_all_btn.setText("Select All")
        else:
            self.select_all_btn.setText(f"Selected ({checked_count}/{total_count})")

    def toggle_select_all(self):
        """Toggle select all/deselect all"""
        checked_count = sum(1 for item in self.sources.values() if item.is_checked())
        total_count = len(self.sources)

        # Block signals during bulk changes
        for item in self.sources.values():
            item.checkbox.blockSignals(True)
        
        if checked_count == total_count:
            # All selected, deselect all
            for item in self.sources.values():
                item.set_checked(False)
        else:
            # Not all selected, select all
            for item in self.sources.values():
                item.set_checked(True)
        
        # Unblock signals
        for item in self.sources.values():
            item.checkbox.blockSignals(False)
        
        # Emit signal once with final state
        states = {name: item.checkbox.isChecked() for name, item in self.sources.items()}
        self.source_changed.emit(states)
        self.update_select_all_button()

    def get_selected_sources(self):
        """Return dict of selected sources"""
        return {name: item.checkbox.isChecked() for name, item in self.sources.items()}

    def on_search_mode_changed(self, button):
        """Handle search mode radio button changes"""
        if button == self.name_radio:
            self.search_mode = 'name'
        elif button == self.id_radio:
            self.search_mode = 'id'
        elif button == self.both_radio:
            self.search_mode = 'both'

        self.search_mode_changed.emit(self.search_mode)

    def get_search_mode(self):
        """Return the current search mode"""
        return self.search_mode

    def set_search_mode(self, mode):
        """Set the search mode"""
        self.search_mode = mode
        if mode == 'name':
            self.name_radio.setChecked(True)
        elif mode == 'id':
            self.id_radio.setChecked(True)
        elif mode == 'both':
            self.both_radio.setChecked(True)

    def get_stylesheet(self):
        """Get stylesheet for this component"""
        return """
            SourceCard {
                background-color: #0f0f0f;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                margin: 4px 0px;
            }

            QLabel#sourceCardTitle {
                color: #00BFAE;
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            QLabel#searchModeTitle {
                color: #00BFAE;
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
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

            QRadioButton#searchModeRadio {
                color: #F0F0F0;
                font-size: 12px;
                font-weight: 500;
                spacing: 8px;
                padding: 6px 12px;
                border-radius: 6px;
                background-color: #0f0f0f;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }

            QRadioButton#searchModeRadio:hover {
                background-color: #121212;
                border-color: rgba(0, 191, 174, 0.4);
            }

            QRadioButton#searchModeRadio:checked {
                background-color: #121212;
                border-color: #00BFAE;
                color: #00BFAE;
                font-weight: 600;
            }

            QRadioButton#searchModeRadio::indicator {
                width: 0px;
                height: 0px;
                margin: 0px;
            }
        """
