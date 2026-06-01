from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from package_table import PackageTable
from search_bar import SearchBar
from filters_panel import FiltersPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aurora - Package Manager")
        self.setGeometry(100, 100, 1400, 900)
        
        self.layout = QVBoxLayout()
        self.search_bar = SearchBar()
        self.package_table = PackageTable()
        self.filters_panel = FiltersPanel()
        
        self.layout.addWidget(self.search_bar)
        self.layout.addWidget(self.filters_panel)
        self.layout.addWidget(self.package_table)
        
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.search_bar.search_triggered.connect(self.package_table.perform_search)
