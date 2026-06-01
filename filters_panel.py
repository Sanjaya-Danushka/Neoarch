from PyQt6.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QLabel

class FiltersPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        sources_label = QLabel("Sources")
        layout.addWidget(sources_label)
        
        self.pacman_checkbox = QCheckBox("pacman")
        self.pacman_checkbox.setChecked(True)
        layout.addWidget(self.pacman_checkbox)
        
        self.aur_checkbox = QCheckBox("AUR")
        self.aur_checkbox.setChecked(True)
        layout.addWidget(self.aur_checkbox)
        
        self.setLayout(layout)
