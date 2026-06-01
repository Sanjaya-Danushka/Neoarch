from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QRadioButton, QButtonGroup, QListWidget, QPushButton, QMenu
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction


class PluginsSidebar(QWidget):
    filter_changed = pyqtSignal(str, bool)  # search_text, installed_only
    install_requested = pyqtSignal(str)     # plugin_id
    uninstall_requested = pyqtSignal(str)   # plugin_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plugins = []
        self._selected_cats = set()
        self._category_menu = None
        self.category_btn = None
        self._build()
        self._apply_style()

    def _build(self):
        self.setObjectName("pluginsSidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel("Extensions")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search extensions")
        self.search.textChanged.connect(lambda _text: self._emit())
        try:
            self.search.setClearButtonEnabled(True)
        except Exception:
            pass
        try:
            self.search.setFixedHeight(34)
        except Exception:
            pass
        self.search.setObjectName("searchBox")
        layout.addWidget(self.search)

        self.group = QButtonGroup(self)
        self.rb_all = QRadioButton("All")
        self.rb_installed = QRadioButton("Installed")
        self.group.addButton(self.rb_all, 0)
        self.group.addButton(self.rb_installed, 1)
        self.rb_all.setChecked(True)
        self.group.buttonClicked.connect(lambda _: self._emit())

        row = QHBoxLayout()
        row.addWidget(self.rb_all)
        row.addWidget(self.rb_installed)
        row.addStretch()
        layout.addLayout(row)
        
        # Categories dropdown (saves horizontal space)
        self.category_btn = QPushButton("Categories: All")
        self.category_menu = QMenu(self)
        self.category_btn.setMenu(self.category_menu)
        try:
            self.category_btn.setFixedHeight(34)
        except Exception:
            pass
        self.category_btn.setObjectName("categoryBtn")
        layout.addWidget(self.category_btn)

        self.list = QListWidget()
        self.list.currentTextChanged.connect(self._on_select)
        try:
            self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        except Exception:
            pass
        try:
            self.list.setTextElideMode(Qt.TextElideMode.ElideRight)
        except Exception:
            pass
        try:
            self.list.setUniformItemSizes(True)
        except Exception:
            pass
        try:
            self.list.setSpacing(2)
        except Exception:
            pass
        self.list.setObjectName("pluginsList")
        layout.addWidget(self.list)
        
        self.install_btn = QPushButton("Install Selected")
        self.install_btn.clicked.connect(self._install_selected)
        try:
            self.install_btn.setFixedHeight(34)
        except Exception:
            pass
        self.install_btn.setObjectName("primaryBtn")
        layout.addWidget(self.install_btn)
        self.uninstall_btn = QPushButton("Uninstall Selected")
        self.uninstall_btn.clicked.connect(self._uninstall_selected)
        try:
            self.uninstall_btn.setFixedHeight(34)
        except Exception:
            pass
        self.uninstall_btn.setObjectName("dangerBtn")
        layout.addWidget(self.uninstall_btn)
        layout.addStretch()

    def _apply_style(self):
        try:
            self.setStyleSheet(self._style())
        except Exception:
            pass

    def _style(self):
        return (
            """
            QWidget#pluginsSidebar {
                background-color: transparent;
            }
            QLineEdit#searchBox {
                background-color: #151515;
                color: #F0F0F0;
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px;
                padding: 6px 10px;
            }
            QLineEdit#searchBox:focus {
                border: 1px solid #00BFAE;
                outline: none;
            }
            QPushButton#categoryBtn {
                background-color: #151515;
                color: #E0E0E0;
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px;
                padding: 6px 10px;
                text-align: left;
            }
            QPushButton#categoryBtn:hover {
                border-color: rgba(0,191,174,0.6);
            }
            QListWidget#pluginsList {
                background-color: #0f0f0f;
                color: #E0E0E0;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
            }
            QListWidget#pluginsList::item {
                padding: 6px 8px;
            }
            QListWidget#pluginsList::item:selected {
                background: rgba(0,191,174,0.15);
                color: #FFFFFF;
            }
            QPushButton#primaryBtn {
                background-color: #1a1a1a;
                color: #E0E0E0;
                border: 1px solid rgba(0,191,174,0.5);
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: 600;
            }
            QPushButton#primaryBtn:hover {
                background-color: rgba(0,191,174,0.15);
                border-color: #00BFAE;
            }
            QPushButton#dangerBtn {
                background-color: #1a1a1a;
                color: #E0E0E0;
                border: 1px solid rgba(229,57,53,0.5);
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: 600;
            }
            QPushButton#dangerBtn:hover {
                background-color: rgba(229,57,53,0.15);
                border-color: #E53935;
            }
            QRadioButton {
                color: #E0E0E0;
            }
            """
        )

    def set_plugins(self, plugins):
        self.plugins = plugins or []
        try:
            self.list.blockSignals(True)
            self.list.clear()
            for p in self.plugins:
                name = p.get('name') or p.get('id')
                self.list.addItem(name)
        finally:
            self.list.blockSignals(False)
    
    def set_categories(self, categories):
        # Build dropdown menu with checkable actions
        if self.category_menu is None:
            self.category_menu = QMenu(self)
            self.category_btn.setMenu(self.category_menu)
        self.category_menu.clear()
        self._selected_cats = set()
        if not categories:
            self._update_category_btn()
            return
        # Optional helper actions
        act_all = QAction("All Categories", self)
        act_all.triggered.connect(self._clear_categories)
        self.category_menu.addAction(act_all)
        self.category_menu.addSeparator()
        for cat in categories:
            action = QAction(cat, self)
            action.setCheckable(True)
            action.toggled.connect(lambda checked, c=cat: self._on_category_toggled(c, checked))
            self.category_menu.addAction(action)
        self._update_category_btn()
    
    def get_selected_categories(self):
        return list(self._selected_cats)

    def _on_category_toggled(self, cat, checked):
        if checked:
            self._selected_cats.add(cat)
        else:
            self._selected_cats.discard(cat)
        self._update_category_btn()
        self._emit()

    def _clear_categories(self):
        self._selected_cats.clear()
        # Uncheck all actions
        if self.category_menu:
            for act in self.category_menu.actions():
                if act.isCheckable():
                    act.setChecked(False)
        self._update_category_btn()
        self._emit()

    def _update_category_btn(self):
        if not self._selected_cats:
            self.category_btn.setText("Categories: All")
        else:
            # Show up to 2 names, then count
            cats = sorted(self._selected_cats)
            label = ", ".join(cats[:2]) + ("…" if len(cats) > 2 else "")
            self.category_btn.setText(f"Categories: {label}")

    def _emit(self):
        text = self.search.text().strip()
        installed_only = self.group.checkedId() == 1
        self.filter_changed.emit(text, installed_only)
    
    def _on_select(self, text):
        # Selecting an item narrows the filter to that name
        self.filter_changed.emit(text or "", self.group.checkedId() == 1)
    
    def _install_selected(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text()
        # Map back to id
        pid = None
        for p in self.plugins:
            n = p.get('name') or p.get('id')
            if n == name:
                pid = p.get('id')
                break
        if pid:
            self.install_requested.emit(pid)
    
    def _uninstall_selected(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text()
        pid = None
        for p in self.plugins:
            n = p.get('name') or p.get('id')
            if n == name:
                pid = p.get('id')
                break
        if pid:
            self.uninstall_requested.emit(pid)
