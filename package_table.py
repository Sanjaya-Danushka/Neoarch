from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QCheckBox
from PyQt6.QtCore import pyqtSignal

class PackageTable(QTableWidget):
    search_triggered = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["", "Package Name", "Package ID", "Version", "Description", "Source"])

    def perform_search(self, query):
        # Placeholder for search logic
        print(f"Searching for: {query}")

    def add_discover_row(self, pkg):
        row = self.rowCount()
        self.insertRow(row)
        
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        self.setCellWidget(row, 0, checkbox)
        
        name_item = QTableWidgetItem(pkg['name'])
        name_item.setToolTip(pkg['name'])
        self.setItem(row, 1, name_item)
        self.setItem(row, 2, QTableWidgetItem(pkg['id']))
        self.setItem(row, 3, QTableWidgetItem(pkg['version']))
        self.setItem(row, 4, QTableWidgetItem(pkg.get('description', '')))
        self.setItem(row, 5, QTableWidgetItem(pkg['source']))
