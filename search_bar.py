from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import pyqtSignal, QTimer

class SearchBar(QLineEdit):
    search_triggered = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Type a package name to search in AUR and official repositories")
        
        self.timer = QTimer()
        self.timer.setInterval(300)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.emit_search)
        self.textChanged.connect(self.timer.start)

    def emit_search(self):
        query = self.text().strip()
        if len(query) >= 3:
            self.search_triggered.emit(query)
