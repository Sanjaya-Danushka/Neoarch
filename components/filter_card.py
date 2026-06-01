"""
FilterCard Component - Card-style container for filter options
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import pyqtSignal


class FilterCard(QWidget):
    """Card component for filter options"""

    filter_changed = pyqtSignal(dict)  # Emits dict of filter_name -> is_checked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters = {}
        self.init_ui()

    def init_ui(self):
        """Initialize the filter card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title_label = QLabel("Filters")
        title_label.setObjectName("filterCardTitle")
        header_layout.addWidget(title_label)

        layout.addWidget(header_widget)

        # Container for filter items
        self.filters_container = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_container)
        self.filters_layout.setContentsMargins(12, 0, 12, 8)
        self.filters_layout.setSpacing(6)

        layout.addWidget(self.filters_container)

        # Apply styling
        self.setStyleSheet(self.get_stylesheet())

    def add_filter(self, filter_name, checked=True):
        """Add a filter to the card"""
        checkbox = QCheckBox(filter_name)
        checkbox.setChecked(checked)
        checkbox.setObjectName("filterCheckbox")
        checkbox.stateChanged.connect(lambda: self.on_filter_changed())

        self.filters[filter_name] = checkbox
        self.filters_layout.addWidget(checkbox)

        # Initial state change emission
        self.on_filter_changed()

    def on_filter_changed(self):
        """Handle when any filter selection changes"""
        states = {name: checkbox.isChecked() for name, checkbox in self.filters.items()}
        self.filter_changed.emit(states)

    def get_selected_filters(self):
        """Return dict of selected filters"""
        return {name: checkbox.isChecked() for name, checkbox in self.filters.items()}

    def set_selected_filters(self, selected_dict):
        """Set which filters are selected"""
        for name, checked in selected_dict.items():
            if name in self.filters:
                self.filters[name].setChecked(checked)

    def get_stylesheet(self):
        """Get stylesheet for this component"""
        return """
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

            QCheckBox#filterCheckbox {
                color: #F0F0F0;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
                padding: 4px 8px;
                border-radius: 6px;
            }

            QCheckBox#filterCheckbox:hover {
                background-color: rgba(0, 191, 174, 0.05);
                border-radius: 6px;
            }

            QCheckBox#filterCheckbox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid rgba(0, 191, 174, 0.4);
                background-color: rgba(42, 45, 51, 0.8);
            }

            QCheckBox#filterCheckbox::indicator:checked {
                background-color: #00BFAE;
                border: 2px solid #00BFAE;
            }

            QCheckBox#filterCheckbox::indicator:unchecked {
                background-color: rgba(42, 45, 51, 0.8);
            }

            QCheckBox#filterCheckbox::indicator:hover {
                border-color: rgba(0, 191, 174, 0.8);
            }
        """
