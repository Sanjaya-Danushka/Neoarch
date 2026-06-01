from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QGridLayout, QSizePolicy, QMenu
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QAction
from .plugins_data import get_plugins_data, get_all_plugins_data
import os
import shutil
import re
import random


class CardState:
    """Encapsulates the state of a plugin card"""
    def __init__(self):
        self.is_installing = False
        self.is_installed_state = False
        self.matching_plugin = None
    
    def set_installing(self, installing):
        """Set the installing state"""
        self.is_installing = installing
    
    def get_installing(self):
        """Get the installing state"""
        return self.is_installing
    
    def set_installed_state(self, installed):
        """Set the installed state"""
        self.is_installed_state = installed
    
    def get_installed_state(self):
        """Get the installed state"""
        return self.is_installed_state
    
    def set_matching_plugin(self, plugin):
        """Set the matching plugin reference"""
        self.matching_plugin = plugin
    
    def get_matching_plugin(self):
        """Get the matching plugin reference"""
        return self.matching_plugin


class ElideLabel(QLabel):
    def __init__(self, text="", parent=None, max_lines=2):
        super().__init__(text, parent)
        self._full_text = text or ""
        self._max_lines = max(1, int(max_lines))
        try:
            self.setWordWrap(True)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        except Exception:
            pass

    def set_max_lines(self, n):
        try:
            self._max_lines = max(1, int(n))
        except Exception:
            self._max_lines = 1
        self._apply_elide()

    def setText(self, text):
        self._full_text = text or ""
        self._apply_elide()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply_elide()

    def _apply_elide(self):
        try:
            fm = self.fontMetrics()
            width = max(0, self.width())
            if width <= 0:
                QLabel.setText(self, self._full_text)
                return
            if self._max_lines <= 1:
                el = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, width)
                QLabel.setText(self, el)
                return
            words = (self._full_text or "").split()
            lines = []
            current = ""
            i = 0
            while i < len(words):
                w = words[i]
                trial = (current + " " + w).strip()
                if fm.horizontalAdvance(trial) <= width:
                    current = trial
                    i += 1
                else:
                    if current:
                        lines.append(current)
                    else:
                        lines.append(fm.elidedText(w, Qt.TextElideMode.ElideRight, width))
                        i += 1
                    current = ""
                if len(lines) == self._max_lines - 1:
                    remaining = " ".join(words[i:])
                    last = (current + (" " if current and remaining else "") + remaining).strip()
                    el = fm.elidedText(last, Qt.TextElideMode.ElideRight, width)
                    lines.append(el)
                    current = ""
                    break
            if current and len(lines) < self._max_lines:
                lines.append(current)
            QLabel.setText(self, "\n".join(lines[: self._max_lines]))
        except Exception:
            try:
                QLabel.setText(self, self._full_text)
            except Exception:
                pass

class PluginCard(QFrame):
    def __init__(self, spec: dict, icon: QIcon, installed: bool, on_install, on_open, on_uninstall, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.on_install = on_install
        self.on_open = on_open
        self.on_uninstall = on_uninstall
        self.setObjectName("pluginCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(self._style())
        # Fix height so all cards are uniform regardless of content/state
        self.setFixedHeight(148)
        # Prevent vertical stretch so grid vertical spacing is visible
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.icon_label = QLabel()
        try:
            if icon and not icon.isNull():
                self.icon_label.setPixmap(icon.pixmap(36, 36))
            else:
                self.icon_label.setText("🧩")
        except Exception:
            self.icon_label.setText("🧩")
        layout.addWidget(self.icon_label)

        text_col = QVBoxLayout()
        title_text = spec.get('name', spec.get('id'))
        title = ElideLabel(title_text, self, max_lines=1)
        title.setObjectName("pluginTitle")
        try:
            title.setToolTip(title_text)
        except Exception:
            pass
        desc_text = spec.get('desc', "")
        desc = ElideLabel(desc_text, self, max_lines=2)
        desc.setObjectName("pluginDesc")
        try:
            desc.setToolTip(desc_text)
        except Exception:
            pass
        text_col.addWidget(title)
        text_col.addWidget(desc)
        layout.addLayout(text_col, 1)

        self.action_btn = QPushButton()
        self.status_label = QLabel()
        self.status_label.setObjectName("pluginStatus")
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.setVisible(False)
        btn_col = QVBoxLayout()
        btn_col.addWidget(self.action_btn)
        btn_col.addWidget(self.uninstall_btn)
        btn_col.addWidget(self.status_label)
        btn_col.addStretch()
        layout.addLayout(btn_col)

        self.update_state(installed)

    def update_icon(self, icon: QIcon):
        try:
            if icon and not icon.isNull():
                self.icon_label.setPixmap(icon.pixmap(36, 36))
            else:
                self.icon_label.setText("🧩")
        except Exception:
            try:
                self.icon_label.setText("🧩")
            except Exception:
                pass

    def update_state(self, installed: bool):
        self.status_label.setText("Installed" if installed else "Not installed")
        if installed:
            self.action_btn.setText("Open")
            self.action_btn.clicked.disconnect() if self.action_btn.receivers(self.action_btn.clicked) else None
            self.action_btn.clicked.connect(lambda: self.on_open(self.spec))
            self.uninstall_btn.setVisible(True)
            self.uninstall_btn.clicked.disconnect() if self.uninstall_btn.receivers(self.uninstall_btn.clicked) else None
            self.uninstall_btn.clicked.connect(lambda: self.on_uninstall(self.spec))
        else:
            self.action_btn.setText("Install")
            self.action_btn.clicked.disconnect() if self.action_btn.receivers(self.action_btn.clicked) else None
            self.action_btn.clicked.connect(lambda: self.on_install(self.spec))
            self.uninstall_btn.setVisible(False)

    def set_installing(self, installing: bool):
        try:
            if installing:
                self.action_btn.setEnabled(False)
                self.uninstall_btn.setEnabled(False)
                self.action_btn.setText("Installing…")
                self.status_label.setText("Installing…")
            else:
                self.action_btn.setEnabled(True)
                self.uninstall_btn.setEnabled(True)
                # Restore text based on state
                self.update_state(self.status_label.text().lower().startswith("installed"))
        except Exception:
            pass

    def _style(self):
        return """
        QFrame#pluginCard {
            background-color: #0f0f0f;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.06);
            margin: 10px;
        }
        QLabel#pluginTitle {
            color: #F0F0F0;
            font-size: 13px;
            font-weight: 600;
        }
        QLabel#pluginDesc {
            color: #A0A0A0;
            font-size: 11px;
        }
        QLabel#pluginStatus {
            color: #00BFAE;
            font-size: 10px;
        }
        """


class DraggableScrollArea(QScrollArea):
    """Custom scroll area that supports drag scrolling"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_start_pos = None
        self._drag_start_value = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self._drag_start_value = self.horizontalScrollBar().value()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is not None:
            delta = event.pos().x() - self._drag_start_pos.x()
            new_value = self._drag_start_value - delta
            self.horizontalScrollBar().setValue(new_value)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        self._drag_start_value = None
        super().mouseReleaseEvent(event)


class PluginsView(QWidget):
    install_requested = pyqtSignal(str)   # plugin id
    launch_requested = pyqtSignal(str)    # plugin id
    uninstall_requested = pyqtSignal(str) # plugin id

    def __init__(self, main_app, get_icon_callback, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.get_icon_callback = get_icon_callback
        self._filter_text = ""
        self._installed_only = False
        self._categories = set()
        self._selected_category = None  # Track selected category
        self._current_cols = 2  # Track current column count
        self._all_cards = []  # Store all created cards for performance
        self._current_filter_states = {}  # Track current filter states
        self._current_source_states = {"pacman": True, "AUR": True, "Flatpak": True, "npm": True}  # Track source states
        
        # Pagination variables for infinite scrolling
        self._all_plugins = []  # All available plugins
        self._loaded_count = 0  # Number of plugins currently loaded
        self._batch_size = 4  # Load 4 plugins at a time for better performance
        self._is_loading = False  # Prevent multiple simultaneous loads
        self._loading_indicator = None  # Loading indicator widget
        self._load_timer = None  # Timer for deferred loading
        self._card_cache = {}
        self._category_filtered_plugins = []
        self._category_loaded_count = 0
        self._is_layouting = False  # Guard to avoid loading during relayout
        
        # Debounce timer for resize events
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._handle_resize)
        
        # UI components initialized in _init_ui
        self.slider_layout = None
        self.grid_layout = None
        self._loading_container = None
        self._scroll_area = None
        
        self._init_specs()
        self._init_ui()

    def _init_specs(self):
        """Initialize plugin specifications from external data file"""
        self.plugins = get_plugins_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        # Popular Apps Slider Section
        self.create_popular_slider(layout)
        
        # Filter Buttons Row
        self.create_filter_buttons(layout)
        
        # Apps Grid
        self.create_apps_grid(layout)
        QTimer.singleShot(100, self.populate_app_cards)

    def create_popular_slider(self, parent_layout):
        """Create the popular apps slider at the top"""
        slider_container = QWidget()
        slider_container.setFixedHeight(220)  # Increased height for larger cards
        slider_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(20, 25, 35, 0.9),
                    stop:1 rgba(25, 30, 40, 0.9));
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        # Create draggable scroll area for horizontal scrolling
        scroll_area = DraggableScrollArea()
        scroll_area.setFixedHeight(220)  # Increased height for larger cards
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        # Enable scroll bar interaction
        scroll_area.horizontalScrollBar().setCursor(Qt.CursorShape.PointingHandCursor)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea::corner {
                background: transparent;
                border: none;
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
        """)
        
        # Create content widget for the scroll area
        scroll_content = QWidget()
        self.slider_layout = QHBoxLayout(scroll_content)
        self.slider_layout.setContentsMargins(20, 20, 20, 20)
        self.slider_layout.setSpacing(16)
        
        # Popular apps data - curated selection with image filenames
        popular_apps = [
            {"name": "Firefox", "desc": "Fast, private & safe web browser", "category": "Internet", "rating": 4.6, "image": "firefox.jpg"},
            {"name": "Visual Studio Code", "desc": "Powerful code editor", "category": "Development", "rating": 4.8, "image": "vscode.jpg"},
            {"name": "Timeshift", "desc": "System restore utility", "category": "System Tools", "rating": 4.5, "image": "timeshift.jpg"},
            {"name": "BleachBit", "desc": "System cleaner & privacy tool", "category": "System Tools", "rating": 4.3, "image": "bleachbit.jpg"},
            {"name": "GIMP", "desc": "GNU Image Manipulation Program", "category": "Graphics", "rating": 4.4, "image": "gimp.jpg"},
            {"name": "VLC Media Player", "desc": "Universal media player", "category": "Multimedia", "rating": 4.7, "image": "vlc.jpg"},
            {"name": "Discord", "desc": "Voice, video and text chat", "category": "Communication", "rating": 4.2, "image": "discode.jpg"},
            {"name": "Krita", "desc": "Digital painting application", "category": "Graphics", "rating": 4.6, "image": "krita.jpg"},
            {"name": "Spotify", "desc": "Music streaming service", "category": "Multimedia", "rating": 4.1, "image": "spotify.jpg"},
            {"name": "Telegram", "desc": "Fast and secure messaging", "category": "Communication", "rating": 4.4, "image": "telegram.jpg"},
            {"name": "Google Chrome", "desc": "Fast and secure web browser", "category": "Internet", "rating": 4.3, "image": "chrome.jpg"},
            {"name": "Kitty", "desc": "Fast, feature-rich terminal", "category": "System Tools", "rating": 4.5, "image": "kitty.jpg"}
        ]
        
        # Shuffle the apps list to randomize the order
        shuffled_apps = popular_apps.copy()
        random.shuffle(shuffled_apps)
        
        for app in shuffled_apps:
            card = self.create_slider_card(app)
            self.slider_layout.addWidget(card)
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(scroll_content)
        scroll_content.setCursor(Qt.CursorShape.OpenHandCursor)
        
        # Add scroll area to the main container
        container_layout = QVBoxLayout(slider_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)
        
        parent_layout.addWidget(slider_container)

    def create_slider_card(self, app_data):
        """Create a card for the popular apps slider with background image"""
        card = QFrame()
        card.setFixedSize(240, 180)  # Larger size for better visibility
        
        # Find matching plugin for this app
        matching_plugin = None
        app_name = app_data.get('name', '').lower()
        
        # Try exact name match first
        for plugin in self.plugins:
            if plugin.get('name', '').lower() == app_name:
                matching_plugin = plugin
                break
        
        # If no exact match, try partial/fuzzy matching
        if not matching_plugin:
            for plugin in self.plugins:
                plugin_name = plugin.get('name', '').lower()
                # Check if app_name is contained in plugin name or vice versa
                if app_name in plugin_name or plugin_name in app_name:
                    # Prefer exact word matches
                    if app_name.split()[0] in plugin_name.split():
                        matching_plugin = plugin
                        break
        
        # Last resort: try ID matching
        if not matching_plugin:
            app_id = app_data.get('name', '').lower().replace(' ', '-')
            for plugin in self.plugins:
                if plugin.get('id', '').lower() == app_id or app_id in plugin.get('id', '').lower():
                    matching_plugin = plugin
                    break
        
        # Check if app is installed
        is_installed = False
        if matching_plugin:
            is_installed = self.is_installed(matching_plugin)
        
        # Get background image path
        image_filename = app_data.get("image", "")
        background_image_path = os.path.join(os.path.dirname(__file__), "..", "assets", "plugins", "slidebar", image_filename)
        
        # Create background image label
        background_label = QLabel(card)
        background_label.setGeometry(0, 0, 240, 180)
        
        # Load and scale the background image
        if os.path.exists(background_image_path):
            pixmap = QPixmap(background_image_path)
            if not pixmap.isNull():
                # Scale the pixmap to cover the entire card while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(240, 180, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                
                # If the scaled image is larger than the card, crop it to center
                if scaled_pixmap.width() > 240 or scaled_pixmap.height() > 180:
                    x_offset = max(0, (scaled_pixmap.width() - 240) // 2)
                    y_offset = max(0, (scaled_pixmap.height() - 180) // 2)
                    cropped_pixmap = scaled_pixmap.copy(x_offset, y_offset, 240, 180)
                    background_label.setPixmap(cropped_pixmap)
                else:
                    background_label.setPixmap(scaled_pixmap)
        
        # Style the card frame
        card.setStyleSheet("""
            QFrame {
                border-radius: 12px;
                border: none;
            }
        """)
        
        # Create overlay container for text content
        overlay = QWidget(card)
        overlay.setGeometry(0, 0, 240, 180)
        overlay.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 0, 0, 0.1),
                    stop:0.6 rgba(0, 0, 0, 0.3),
                    stop:1 rgba(0, 0, 0, 0.8));
                border: none;
            }
        """)
        
        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # Add stretch to push content to bottom
        layout.addStretch()
        
        # App name
        name_label = QLabel(app_data["name"])
        name_label.setStyleSheet("""
            color: white;
            font-weight: 700;
            font-size: 16px;
            background: transparent;
        """)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(name_label)
        
        # App description
        desc_label = QLabel(app_data["desc"])
        desc_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9);
            font-size: 12px;
            font-weight: 400;
            background: transparent;
        """)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        desc_label.setMaximumHeight(32)
        layout.addWidget(desc_label)
        
        # Bottom row with rating and install button
        bottom_row = QWidget()
        bottom_row.setStyleSheet("background: transparent;")
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 8, 0, 0)
        bottom_layout.setSpacing(8)
        
        # Rating
        rating_label = QLabel(f"⭐ {app_data['rating']}")
        rating_label.setStyleSheet("""
            color: #FFD700;
            font-size: 12px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)
        bottom_layout.addWidget(rating_label)
        
        bottom_layout.addStretch()
        
        # Install/Open button
        button_text = "Open" if is_installed else "Install"
        action_btn = QPushButton(button_text)
        action_btn.setFixedSize(80, 32)
        action_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 30, 30, 0.9);
                color: white;
                border: none;
                border-radius: 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(50, 50, 50, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(20, 20, 20, 0.9);
            }
        """)
        
        # Connect button to appropriate action
        if matching_plugin:
            if is_installed:
                action_btn.clicked.connect(lambda: self.launch_requested.emit(matching_plugin['id']))
            else:
                action_btn.clicked.connect(lambda: (card.set_installing(True), self.install_requested.emit(matching_plugin['id'])))
        
        bottom_layout.addWidget(action_btn)
        
        layout.addWidget(bottom_row)
        
        # Store state using CardState class for proper encapsulation
        card_state = CardState()
        card_state.set_installed_state(is_installed)
        card_state.set_matching_plugin(matching_plugin)
        card.card_state = card_state
        
        def set_card_installing(installing):
            card_state.set_installing(installing)
            if installing:
                for widget in card.findChildren(QPushButton):
                    widget.setEnabled(False)
                    widget.setText("Installing…")
            else:
                for widget in card.findChildren(QPushButton):
                    widget.setEnabled(True)
                    widget.setText("Open" if card_state.get_installed_state() else "Install")
        card.set_installing = set_card_installing
        
        return card

    def _get_or_create_card(self, plugin_spec):
        """Return cached card data for a plugin or create it."""
        try:
            pid = plugin_spec.get('id')
        except Exception:
            pid = None
        if pid and pid in getattr(self, '_card_cache', {}):
            return self._card_cache[pid]
        installed = self.is_installed(plugin_spec)
        icon = self._icon_for(plugin_spec)
        card = self.create_app_card(plugin_spec, icon, installed)
        data = {
            'plugin': plugin_spec,
            'widget': card,
            'installed': installed
        }
        try:
            if pid:
                self._card_cache[pid] = data
        except Exception:
            pass
        return data

    def create_filter_buttons(self, parent_layout):
        """Create the main filter buttons row"""
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(12)
        
        filters = ["All", "Popular", "Updated", "Categories"]
        
        for i, filter_name in enumerate(filters):
            btn = QPushButton(filter_name)
            btn.setFixedHeight(36)
            
            # Special handling for Categories button
            if filter_name == "Categories":
                # Create dropdown menu for categories
                categories_menu = QMenu(self)
                categories_menu.setStyleSheet("""
                    QMenu {
                        background-color: #1a1a1a;
                        color: #E0E0E0;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        border-radius: 8px;
                        padding: 4px;
                    }
                    QMenu::item {
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QMenu::item:selected {
                        background-color: rgba(0, 191, 174, 0.2);
                    }
                """)
                
                # Add "All Categories" option first
                all_action = QAction("All Categories", self)
                all_action.triggered.connect(self.show_all_apps)
                categories_menu.addAction(all_action)
                categories_menu.addSeparator()
                
                # Get unique categories from plugins using normalized mapping
                unique_categories = sorted({self._category_for(p) for p in self.plugins})
                
                for category in unique_categories:
                    action = QAction(category, self)
                    action.triggered.connect(lambda checked, cat=category: self.filter_by_category(cat))
                    categories_menu.addAction(action)
                
                btn.setMenu(categories_menu)
            
            if i == 0:  # "All" button selected by default
                btn.clicked.connect(self.show_all_apps)  # Connect All button to show all apps
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #00BFAE;
                        color: white;
                        border: none;
                        border-radius: 18px;
                        padding: 0 20px;
                        font-weight: 600;
                        font-size: 13px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.1);
                        color: #E0E0E0;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        border-radius: 18px;
                        padding: 0 20px;
                        font-weight: 500;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: rgba(0, 191, 174, 0.2);
                        border-color: rgba(0, 191, 174, 0.4);
                    }
                """)
            
            filter_layout.addWidget(btn)
        
        filter_layout.addStretch()
        parent_layout.addWidget(filter_container)


    @staticmethod
    def _get_scrollbar_stylesheet():
        """Return beautiful scrollbar stylesheet with dark rounded corners"""
        return """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea::corner {
                background: transparent;
                border: none;
            }
            /* Vertical Scrollbar */
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
            
            /* Horizontal Scrollbar */
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
        """

    def create_apps_grid(self, parent_layout):
        """Create the apps grid section"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Enable scroll bar interaction
        scroll.verticalScrollBar().setCursor(Qt.CursorShape.PointingHandCursor)
        scroll.horizontalScrollBar().setCursor(Qt.CursorShape.PointingHandCursor)
        scroll.setStyleSheet(self._get_scrollbar_stylesheet())
        
        # Connect scroll event to detect when user reaches bottom
        scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)
        
        # Create grid container
        grid_container = QWidget()
        # Use Minimum vertical policy so content grows naturally and scrollbars appear when needed
        grid_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        # Dynamic column stretching will be set in populate_app_cards
        
        # Add loading indicator container at the bottom
        self._loading_container = QWidget()
        self._loading_container.setVisible(False)
        loading_layout = QVBoxLayout(self._loading_container)
        loading_layout.setContentsMargins(20, 10, 20, 10)
        loading_layout.setSpacing(8)
        
        loading_text = QLabel("Loading more plugins...")
        loading_text.setStyleSheet("""
            QLabel {
                color: #00BFAE;
                font-size: 12px;
                font-weight: 600;
                text-align: center;
            }
        """)
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(loading_text)
        
        # Add grid and loading indicator to scroll layout
        scroll_layout.addWidget(grid_container)
        scroll_layout.addWidget(self._loading_container)
        
        scroll.setWidget(scroll_widget)
        self._scroll_area = scroll  # Store reference for scroll handling
        parent_layout.addWidget(scroll)

    def populate_app_cards(self):
        """Populate the grid with real plugin cards filtered by category"""
        # For category filtering, show all cards that match the category
        if self._selected_category:
            if not self._all_cards:
                self._create_all_cards()
            while self.grid_layout.count():
                _ = self.grid_layout.takeAt(0)
            self._reset_row_stretches()
            for card_data in self._all_cards:
                card_data['widget'].hide()
            try:
                viewport_w = self._scroll_area.viewport().width()
                viewport_h = self._scroll_area.viewport().height()
            except Exception:
                viewport_w = self.width()
                viewport_h = self.height()
            cols = self._calc_cols(viewport_w)
            visible_rows = self._calc_visible_rows(viewport_h)
            initial_rows = visible_rows + 2
            self._current_cols = cols
            # Ensure full dataset is available for categories
            if not self._all_plugins:
                self._all_plugins = get_all_plugins_data()
            # Build filtered plugin list from the full dataset
            self._category_filtered_plugins = [p for p in self._all_plugins if self._category_for(p) == self._selected_category]
            for i in range(cols):
                self.grid_layout.setColumnStretch(i, 1)
                try:
                    self.grid_layout.setColumnMinimumWidth(i, 340)
                except Exception:
                    pass
            initial_batch = min(len(self._category_filtered_plugins), cols * initial_rows)
            self._category_loaded_count = 0
            self._load_initial_category_batch(initial_batch)
            QTimer.singleShot(10, self._ensure_category_scrollbar_visible)
        else:
            # For "All" tab, use pagination system
            if not self._all_plugins:
                # Initialize pagination if not already done
                self.show_all_apps()
            else:
                # Just refresh the current view
                self._update_grid_layout()
    
    def _create_all_cards(self):
        """Create all plugin cards once for better performance"""
        self._all_cards = []
        for plugin in self.plugins:
            installed = self.is_installed(plugin)
            icon = self._icon_for(plugin)
            card = self.create_app_card(plugin, icon, installed)
            self._all_cards.append({
                'plugin': plugin,
                'widget': card,
                'installed': installed
            })

    @staticmethod
    def _get_package_source(plugin_spec):
        """Determine package source from plugin spec"""
        pkg = plugin_spec.get('pkg', '').lower()
        if pkg.startswith('npm-') or 'npm' in pkg:
            return 'npm'
        elif pkg.startswith('aur/') or 'aur' in pkg:
            return 'aur'
        elif pkg.endswith('.flatpak') or 'flatpak' in pkg:
            return 'flatpak'
        elif pkg.startswith('brew-') or 'brew' in pkg:
            return 'brew'
        else:
            return 'pacman'
    
    @staticmethod
    def _category_for(plugin):
        cat = (plugin.get('category') or '').strip()
        if cat:
            c = cat.lower()
            synonyms = {
                'system': 'System Tools',
                'system tool': 'System Tools',
                'system tools': 'System Tools',
                'utility': 'Utility',
                'utilities': 'Utility',
                'dev': 'Development',
                'development': 'Development',
                'internet': 'Internet',
                'network': 'Internet',
                'graphics': 'Graphics',
                'multimedia': 'Multimedia',
                'audio': 'Multimedia',
                'video': 'Multimedia',
                'office': 'Office',
                'productivity': 'Office',
                'education': 'Education',
                'game': 'Games',
                'games': 'Games',
                'security': 'Security',
                'communication': 'Communication',
                'chat': 'Communication',
            }
            return synonyms.get(c, cat)
        tags = plugin.get('tags') or []
        tags_text = ' '.join(tags) if isinstance(tags, (list, tuple, set)) else str(tags)
        text = ' '.join([
            plugin.get('name', ''),
            plugin.get('desc', ''),
            plugin.get('id', ''),
            plugin.get('pkg', ''),
            tags_text,
        ]).lower()
        patterns = [
            (('vscode','visual studio','code','editor','ide','developer','dev','git','node','npm','python','qt','gcc','make','electron','android studio'), 'Development'),
            (('browser','firefox','chrome','web','network','mail','torrent','internet','ftp'), 'Internet'),
            (('image','photo','graphic','draw','paint','gimp','krita','inkscape','blender'), 'Graphics'),
            (('video','music','audio','player','vlc','mpv','spotify','media','ffmpeg'), 'Multimedia'),
            (('chat','telegram','discord','slack','message','voip','call','communication'), 'Communication'),
            (('system','monitor','btop','htop','terminal','shell','backup','timeshift','disk','partition','gparted','bleachbit'), 'System Tools'),
            (('game','steam','lutris','retroarch','games'), 'Games'),
            (('office','libreoffice','document','spreadsheet','writer','calc','pdf'), 'Office'),
            (('learn','education','anki','study'), 'Education'),
            (('password','privacy','guard','vpn','security','encrypt'), 'Security'),
        ]
        for kws, label in patterns:
            for kw in kws:
                if kw in text:
                    return label
        return 'Utility'
    
    @staticmethod
    def _get_source_icon(source):
        """Get icon path for package source"""
        base_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "discover")
        icons = {
            'pacman': os.path.join(base_path, 'pacman.svg'),
            'aur': os.path.join(base_path, 'aur.svg'),
            'flatpak': os.path.join(base_path, 'flatpack.svg'),
            'npm': os.path.join(base_path, 'node.svg'),
            'brew': os.path.join(base_path, 'pacman.svg'),
            'pip': os.path.join(base_path, 'pacman.svg')
        }
        return icons.get(source, os.path.join(base_path, 'pacman.svg'))

    # --- Layout helpers to keep calculations consistent ---
    def _layout_spacing(self):
        try:
            return self.grid_layout.spacing() if self.grid_layout else 20
        except Exception:
            return 20

    def _calc_cols(self, viewport_width):
        spacing = self._layout_spacing()
        unit_w = 340 + spacing
        # Cap columns to 5 to avoid tight packing on very wide screens
        return max(1, min(5, (max(0, viewport_width) + spacing) // unit_w))

    def _calc_visible_rows(self, viewport_height):
        spacing = self._layout_spacing()
        row_h = 140 + spacing
        return max(1, (max(0, viewport_height) + spacing) // row_h)

    def _enforce_row_min_heights(self, upto_row):
        if not hasattr(self, 'grid_layout'):
            return
        try:
            for r in range(0, max(0, int(upto_row)) + 1):
                self.grid_layout.setRowMinimumHeight(r, 140)
        except Exception:
            pass
    
    def _stop_deferred_loads(self):
        try:
            if self._load_timer is not None:
                self._load_timer.stop()
                self._load_timer = None
        except Exception:
            self._load_timer = None

    def _begin_layout_update(self):
        if self._is_layouting:
            return False
        self._is_layouting = True
        self._stop_deferred_loads()
        try:
            self.setUpdatesEnabled(False)
        except Exception:
            pass
        try:
            if hasattr(self, '_scroll_area') and self._scroll_area:
                self._scroll_area.setUpdatesEnabled(False)
                self._scroll_area.viewport().setUpdatesEnabled(False)
        except Exception:
            pass
        return True

    def _finish_layout_update(self):
        try:
            if hasattr(self, '_scroll_area') and self._scroll_area:
                self._scroll_area.viewport().setUpdatesEnabled(True)
                self._scroll_area.setUpdatesEnabled(True)
                self._scroll_area.viewport().update()
        except Exception:
            pass
        try:
            self.setUpdatesEnabled(True)
        except Exception:
            pass
        self._is_layouting = False

    def create_app_card(self, plugin_spec, icon, installed):
        """Create a medium-sized app card with enhanced styling"""
        card = QFrame()
        card.setFixedSize(340, 140)
        # Ensure the widget paints its own background to avoid transparency/bleed issues
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setAutoFillBackground(True)
            card.setObjectName("appCard")
        except Exception:
            pass
        
        # Store state using CardState class for proper encapsulation
        card_state = CardState()
        card_state.set_installed_state(installed)
        card.card_state = card_state
        
        def set_card_installing(installing):
            card_state.set_installing(installing)
            if installing:
                for widget in card.findChildren(QPushButton):
                    widget.setEnabled(False)
                    if widget.text() in ("Install", "Open"):
                        widget.setText("Installing…")
                    elif widget.text() == "Uninstall":
                        widget.setText("Uninstalling…")
            else:
                for widget in card.findChildren(QPushButton):
                    widget.setEnabled(True)
                    if "Installing" in widget.text() or "Uninstalling" in widget.text():
                        if "Uninstalling" in widget.text():
                            widget.setText("Uninstall")
                        else:
                            widget.setText("Install" if not card_state.get_installed_state() else "Open")
        card.set_installing = set_card_installing
        bg_image_path = os.path.join(os.path.dirname(__file__), "..", "assets", "plugins", "cardbackground.jpg")
        bg_image_url = bg_image_path.replace("\\", "/")
        card.setStyleSheet(f"""
            QFrame#appCard {{
                background-image: url('{bg_image_url}');
                background-position: center;
                background-repeat: no-repeat;
                background-color: rgb(15, 20, 30);
                border-radius: 14px;
                border: 1px solid rgba(0, 191, 174, 0.15);
            }}
            QFrame#appCard:hover {{
                border: 1px solid rgba(0, 191, 174, 0.4);
                background-color: rgb(20, 25, 35);
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Left side: Icon and text
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        
        # Icon and name row
        icon_name_layout = QHBoxLayout()
        icon_name_layout.setContentsMargins(0, 0, 0, 0)
        icon_name_layout.setSpacing(10)
        
        # Icon with shadow effect
        icon_label = QLabel()
        icon_label.setFixedSize(52, 52)
        icon_label.setStyleSheet("""
            QLabel {
                border: none;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 2px;
            }
        """)
        if icon and not icon.isNull():
            icon_label.setPixmap(icon.pixmap(48, 48))
        else:
            icon_label.setText("🧩")
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("""
                QLabel {
                    font-size: 28px;
                    border: none;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 10px;
                }
            """)
        icon_name_layout.addWidget(icon_label)
        
        # Name and source column
        name_source_layout = QVBoxLayout()
        name_source_layout.setContentsMargins(0, 0, 0, 0)
        name_source_layout.setSpacing(2)
        
        # Name
        name_label = QLabel(plugin_spec.get('name', plugin_spec.get('id')))
        name_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
                border: none;
                background: transparent;
            }
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        name_source_layout.addWidget(name_label)
        
        # Source (package manager) with icon
        source = self._get_package_source(plugin_spec)
        source_icon_path = self._get_source_icon(source)
        
        # Create source layout with icon and text
        source_layout = QHBoxLayout()
        source_layout.setContentsMargins(6, 2, 6, 2)
        source_layout.setSpacing(4)
        
        # Source icon
        source_icon_label = QLabel()
        source_icon_label.setFixedSize(12, 12)
        try:
            source_pixmap = QPixmap(source_icon_path)
            if not source_pixmap.isNull():
                source_icon_label.setPixmap(source_pixmap.scaled(12, 12, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                source_icon_label.setText("📦")
                source_icon_label.setStyleSheet("font-size: 10px;")
        except Exception:
            source_icon_label.setText("📦")
            source_icon_label.setStyleSheet("font-size: 10px;")
        
        # Source text
        source_text_label = QLabel(source)
        source_text_label.setStyleSheet("""
            QLabel {
                color: #00BFAE;
                font-size: 9px;
                font-weight: 600;
                border: none;
                background: transparent;
            }
        """)
        
        source_layout.addWidget(source_icon_label)
        source_layout.addWidget(source_text_label)
        source_layout.addStretch()
        
        # Source container with background
        source_container = QWidget()
        source_container.setLayout(source_layout)
        source_container.setStyleSheet("""
            QWidget {
                background: rgba(0, 191, 174, 0.1);
                border-radius: 6px;
            }
        """)
        name_source_layout.addWidget(source_container)
        
        icon_name_layout.addLayout(name_source_layout, 1)
        left_layout.addLayout(icon_name_layout)
        
        # Description
        desc_label = QLabel(plugin_spec.get('desc', ''))
        desc_label.setStyleSheet("""
            QLabel {
                color: #B0B0B0;
                font-size: 10px;
                border: none;
                background: transparent;
                line-height: 1.3;
            }
        """)
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(28)
        left_layout.addWidget(desc_label)
        
        left_layout.addStretch()
        layout.addLayout(left_layout, 1)
        
        # Right side: Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        
        if installed:
            # Open button (filled white)
            open_btn = QPushButton("Open")
            open_btn.setFixedHeight(34)
            open_btn.setMinimumWidth(85)
            open_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #1a1a1a;
                    border: none;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 12px;
                    padding: 0px 12px;
                }
                QPushButton:hover {
                    background-color: #F5F5F5;
                    color: #000000;
                }
                QPushButton:pressed {
                    background-color: #E8E8E8;
                }
            """)
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.clicked.connect(lambda: self.launch_requested.emit(plugin_spec['id']))
            btn_layout.addWidget(open_btn)
            
            # Uninstall button (outlined)
            uninstall_btn = QPushButton("Uninstall")
            uninstall_btn.setFixedHeight(32)
            uninstall_btn.setMinimumWidth(85)
            uninstall_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #E0E0E0;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 11px;
                    padding: 0px 12px;
                }
                QPushButton:hover {
                    border: 1px solid rgba(0, 191, 174, 0.8);
                    color: #00BFAE;
                    background-color: rgba(0, 191, 174, 0.1);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 191, 174, 0.2);
                    border: 1px solid rgba(0, 191, 174, 1.0);
                }
            """)
            uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            uninstall_btn.clicked.connect(lambda: (card.set_installing(True), self.uninstall_requested.emit(plugin_spec['id'])))
            btn_layout.addWidget(uninstall_btn)
        else:
            # Install button (filled teal)
            install_btn = QPushButton("Install")
            install_btn.setFixedHeight(34)
            install_btn.setMinimumWidth(85)
            install_btn.setStyleSheet("""
                QPushButton {
                    background-color: #00BFAE;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 12px;
                    padding: 0px 12px;
                }
                QPushButton:hover {
                    background-color: #00D4C4;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #009080;
                }
            """)
            install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            install_btn.clicked.connect(lambda: (card.set_installing(True), self.install_requested.emit(plugin_spec['id'])))
            btn_layout.addWidget(install_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return card

    def _icon_for(self, spec):
        try:
            path = spec.get('icon')
            if path and os.path.exists(path):
                return self.get_icon_callback(os.path.normpath(path), 36)

            # Try to resolve using available files (supports svg/png/jpg/jpeg) with aliases
            resolved = self._find_plugin_icon_file(spec)
            if resolved and os.path.exists(resolved):
                return self.get_icon_callback(os.path.normpath(resolved), 36)

            # Fallback to default plugin icon
            fallback = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "plugins.svg")
            return self.get_icon_callback(os.path.normpath(fallback), 36)
        except Exception:
            return QIcon()

    def _normalize_name(self, s: str) -> str:
        try:
            return re.sub(r'[^a-z0-9]', '', (s or '').lower())
        except Exception:
            s = (s or '').lower()
            return s.replace('-', '').replace('_', '').replace(' ', '')

    def _candidate_aliases(self, spec) -> list:
        pid = (spec.get('id') or '')
        name = (spec.get('name') or '')
        aliases = []

        def add(x):
            if x and x not in aliases:
                aliases.append(x)

        # Base identifiers
        add(pid)
        add(name)
        add(pid.replace('-', ''))
        add(pid.replace('-', '_'))
        add(pid.replace('_', ''))
        add((name or '').replace(' ', ''))
        add((name or '').replace(' ', '-').lower())
        add((name or '').replace(' ', '').lower())

        # Explicit aliases for known mismatches and alt names
        alias_map = {
            'bleachbit': ['BleachBit', 'bleachbit'],
            'timeshift': ['timeshift'],
            'baobab': ['diskusageanalyzer', 'baobab'],
            'deja-dup': ['dejadup', 'DejaDup'],
            'gparted': ['gparted'],
            'gnome-disk-utility': ['gnome-disks', 'gnomedisks', 'gnomeDis'],
            'pavucontrol': ['pavucontrol', 'pulseaudio'],
            'system-config-printer': ['printer', 'printers'],
            'btop': ['btop'],
            'htop': ['htop'],
            'gnome-system-monitor': ['system-monitor', 'gnomesystemmonitor', 'gnomeSystemMonitor'],
            'simple-scan': ['simple-scan', 'documentscanner'],
            'file-roller': ['file-roller', 'archive', 'achive', 'archivemanager', 'archiver'],
            'nvidia-settings': ['nvidia-settings', 'nvidia', 'nvideasettings', 'nvidiasettings'],
            'nvtop': ['nvtop'],
        }
        for a in alias_map.get(pid, []):
            add(a)

        return aliases

    def _find_plugin_icon_file(self, spec):
        icons_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "plugins"))
        try:
            files = []
            try:
                files = os.listdir(icons_dir)
            except Exception:
                files = []
            if not files:
                return None

            # Build index by normalized stem per extension, prefer svg, then png, jpeg, jpg
            exts = ['.svg', '.png', '.jpeg', '.jpg']
            index = {e: {} for e in exts}
            for fname in files:
                path = os.path.join(icons_dir, fname)
                if not os.path.isfile(path):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext not in index:
                    continue
                stem = os.path.splitext(fname)[0]
                key = self._normalize_name(stem)
                # Do not overwrite existing mapping for same key/ext to keep first-found
                index[ext].setdefault(key, path)

            candidates = [self._normalize_name(a) for a in self._candidate_aliases(spec) if a]

            # Exact match by preference order
            for ext in exts:
                for key in candidates:
                    if key in index[ext]:
                        return index[ext][key]

            # Fallback: partial contains match (still following ext preference)
            for ext in exts:
                for key in candidates:
                    for k2, p2 in index[ext].items():
                        if key and (k2.startswith(key) or key in k2):
                            return p2
            return None
        except Exception:
            return None

    def is_installed(self, spec):
        cmd = spec.get('cmd')
        pkg = spec.get('pkg')
        # Prefer which on the launch command; fallback to pacman -Qi
        try:
            if cmd and shutil.which(cmd):
                return True
        except Exception:
            pass
        try:
            import subprocess
            r = subprocess.run(["pacman", "-Qi", pkg], capture_output=True, text=True)
            return r.returncode == 0
        except Exception:
            return False

    def refresh_all(self):
        """Refresh all plugin cards to reflect current installation state"""
        try:
            # Refresh slider cards to update Open/Install buttons
            try:
                if hasattr(self, 'slider_layout'):
                    for i in range(self.slider_layout.count()):
                        card = self.slider_layout.itemAt(i).widget()
                        if card and hasattr(card, 'card_state'):
                            plugin = card.card_state.get_matching_plugin()
                            if plugin:
                                # Re-check if app is installed
                                is_now_installed = self.is_installed(plugin)
                                # Update button text
                                buttons = card.findChildren(QPushButton)
                                if buttons:
                                    btn = buttons[0]
                                    btn.setText("Open" if is_now_installed else "Install")
                                    # Update the stored state for animation
                                    card.card_state.set_installed_state(is_now_installed)
            except Exception:
                pass
            
            # Clear grid layout
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Clear and rebuild all cards with updated installation status
            self._all_cards = []
            for plugin in self.plugins:
                installed = self.is_installed(plugin)
                icon = self._icon_for(plugin)
                card = self.create_app_card(plugin, icon, installed)
                self._all_cards.append({
                    'plugin': plugin,
                    'widget': card,
                    'installed': installed
                })
            
            # Rebuild grid with updated cards
            cols = self._current_cols
            for i in range(cols):
                self.grid_layout.setColumnStretch(i, 1)
            
            for i, card_data in enumerate(self._all_cards):
                row = i // cols
                col = i % cols
                self.grid_layout.addWidget(card_data['widget'], row, col)
        except Exception:
            pass

    def get_plugin(self, plugin_id):
        for spec in self.plugins:
            if spec['id'] == plugin_id:
                return spec
        return None

    def set_filter(self, text: str, installed_only: bool, categories=None):
        self._filter_text = (text or "").strip().lower()
        self._installed_only = bool(installed_only)
        self._categories = set((categories or []))
        self.apply_filter()

    def apply_filter(self):
        """Apply text, installed, and category filters to the plugins view"""
        # Create cards if not already created
        if not self._all_cards:
            self._create_all_cards()
        
        # Clear the grid layout
        while self.grid_layout.count():
            _ = self.grid_layout.takeAt(0)
        
        # Reset row stretches before re-adding cards
        self._reset_row_stretches()
        
        # Hide all cards first
        for card_data in self._all_cards:
            card_data['widget'].hide()
        
        # Filter and display cards based on search text, installed status, and categories
        filtered_cards = []
        for card_data in self._all_cards:
            plugin = card_data['plugin']
            is_installed = card_data['installed']
            
            # Check installed filter
            if self._installed_only and not is_installed:
                continue
            
            # Check category filter
            if self._categories:
                plugin_category = plugin.get('category', '')
                if plugin_category not in self._categories:
                    continue
            
            # Check search text filter
            if self._filter_text:
                name = (plugin.get('name', '') or '').lower()
                desc = (plugin.get('desc', '') or '').lower()
                plugin_id = (plugin.get('id', '') or '').lower()
                
                # Match if search text is in name, description, or id
                if not (self._filter_text in name or self._filter_text in desc or self._filter_text in plugin_id):
                    continue
            
            filtered_cards.append(card_data)
        
        # Use tracked column count
        cols = self._current_cols
        
        # Set column stretching dynamically
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
        
        # Add filtered cards to layout and show them
        for i, card_data in enumerate(filtered_cards):
            row = i // cols
            col = i % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)
        # Ensure the layout can scroll and does not keep a big empty bottom gap
        max_row = ((len(filtered_cards) - 1) // cols) if filtered_cards else 0
        self.grid_layout.setRowStretch(max_row + 1, 1)
        if not self._selected_category:
            QTimer.singleShot(50, self._ensure_scrollbar_visible)
        QTimer.singleShot(10, self._adjust_bottom_stretch)

    def set_installing(self, plugin_id: str, installing: bool):
        """Update installing state for a plugin card"""
        try:
            # Find the card with this plugin_id
            for card_data in self._all_cards:
                if card_data['plugin'].get('id') == plugin_id:
                    card = card_data['widget']
                    if hasattr(card, 'set_installing'):
                        card.set_installing(installing)
                    break
        except Exception:
            pass
    
    def filter_by_category(self, category):
        """Handle category selection from dropdown menu"""
        self._selected_category = category
        self._category_filtered_plugins = []
        self._category_loaded_count = 0
        self.populate_app_cards()
    
    def show_all_apps(self):
        """Show all apps by clearing category filter and initializing pagination"""
        self._selected_category = None
        
        # Initialize pagination for "All" tab
        if not self._all_plugins:
            self._all_plugins = get_all_plugins_data()
            self._loaded_count = 0
            self._all_cards = []
            
            # Clear existing grid
            while self.grid_layout.count():
                _ = self.grid_layout.takeAt(0)
            
            # Load first batch sized to fill visible rows on current viewport
            try:
                viewport_w = self._scroll_area.viewport().width()
                viewport_h = self._scroll_area.viewport().height()
            except Exception:
                viewport_w = self.width()
                viewport_h = self.height()
            cols = self._calc_cols(viewport_w)
            visible_rows = self._calc_visible_rows(viewport_h)
            initial_rows = visible_rows + 2  # fill screen + buffer
            initial_batch = min(len(self._all_plugins), cols * initial_rows)
            self._load_initial_batch(initial_batch)
        else:
            # Just refresh the current view
            self._update_grid_layout()
    
    def _load_initial_batch(self, batch_size):
        """Load the initial batch of plugins for the All tab"""
        self._is_loading = True
        self._begin_layout_update()
        self._loading_container.setVisible(True)
        
        # Get initial batch
        new_plugins = self._all_plugins[:batch_size]
        
        # Create cards for initial plugins
        new_cards = []
        for plugin in new_plugins:
            installed = self.is_installed(plugin)
            icon = self._icon_for(plugin)
            card = self.create_app_card(plugin, icon, installed)
            card_data = {
                'plugin': plugin,
                'widget': card,
                'installed': installed
            }
            new_cards.append(card_data)
        
        # Reset any previous row stretch factors
        try:
            rc = max(0, self.grid_layout.rowCount())
            for r in range(rc + 4):
                self.grid_layout.setRowStretch(r, 0)
        except Exception:
            pass

        # Add cards to grid using optimized positioning
        cols = self._current_cols
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
            try:
                self.grid_layout.setColumnMinimumWidth(i, 340)
            except Exception:
                pass
        
        # Pre-calculate maximum row needed for initial batch
        max_position = len(new_cards) - 1
        max_row_needed = max_position // cols
        
        # Add cards to positions
        for i, card_data in enumerate(new_cards):
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card_data['widget'], row, col)
        self.grid_layout.setRowStretch(max_row_needed + 1, 1)
        self._enforce_row_min_heights(max_row_needed)
        
        self._all_cards.extend(new_cards)
        self._loaded_count = batch_size
        
        # Hide loading indicator
        QTimer.singleShot(300, self._hide_loading_indicator)
        QTimer.singleShot(20, self._ensure_scrollbar_visible)
        self._is_loading = False
        self._finish_layout_update()
    
    def _load_initial_category_batch(self, batch_size):
        if self._is_loading:
            return
        self._is_loading = True
        self._begin_layout_update()
        self._loading_container.setVisible(True)
        cols = self._current_cols
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
        max_position = batch_size - 1
        max_row_needed = max(0, max_position // max(1, cols))
        for i in range(batch_size):
            plugin = self._category_filtered_plugins[i]
            card_data = self._get_or_create_card(plugin)
            row = i // cols
            col = i % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)
        self.grid_layout.setRowStretch(max_row_needed + 1, 1)
        QTimer.singleShot(10, self._adjust_bottom_stretch)
        self._category_loaded_count = batch_size
        self._enforce_row_min_heights(max_row_needed)
        QTimer.singleShot(300, self._hide_loading_indicator)
        self._is_loading = False
        self._finish_layout_update()
    
    def _hide_loading_indicator(self):
        """Hide the loading indicator widget"""
        if hasattr(self, '_loading_container'):
            self._loading_container.setVisible(False)
    
    def _reset_row_stretches(self):
        if not hasattr(self, 'grid_layout'):
            return
        try:
            rc = max(0, self.grid_layout.rowCount())
            for r in range(rc + 4):
                self.grid_layout.setRowStretch(r, 0)
        except Exception:
            pass
    
    def _adjust_bottom_stretch(self):
        """Keep a stretch row only when no scrollbar; remove it when scrolling is available."""
        if not hasattr(self, 'grid_layout'):
            return
        try:
            last_row = max(0, self.grid_layout.rowCount() - 1)
            sb = None
            try:
                sb = self._scroll_area.verticalScrollBar() if hasattr(self, '_scroll_area') else None
            except Exception:
                sb = None
            if sb and sb.maximum() > 0:
                # Scrolling available, remove artificial stretch row
                self.grid_layout.setRowStretch(last_row, 0)
            else:
                # No scrolling; keep stretch so content fills viewport cleanly
                self.grid_layout.setRowStretch(last_row, 1)
        except Exception:
            pass
    
    def _ensure_scrollbar_visible(self):
        """Auto-load more batches until the scrollbar appears (or we run out of items)."""
        # Only applies for the infinite-scroll 'All' view
        if getattr(self, '_selected_category', None):
            return
        if not hasattr(self, '_scroll_area'):
            return
        
        state = {'attempts': 0}
        
        def _step():
            if state['attempts'] >= 10:
                self._adjust_bottom_stretch()
                return
            sb = self._scroll_area.verticalScrollBar()
            if (sb.maximum() > 0) or (self._loaded_count >= len(self._all_plugins)):
                # If last row is not full, top it off to avoid a one-time gap
                try:
                    viewport_w = self._scroll_area.viewport().width()
                    cols = self._calc_cols(viewport_w)
                except Exception:
                    cols = max(1, int(self._current_cols) if hasattr(self, '_current_cols') else 1)
                remaining = len(self._all_plugins) - self._loaded_count
                need = (cols - (self._loaded_count % cols)) % cols
                if need > 0 and remaining > 0:
                    if self._is_loading:
                        QTimer.singleShot(120, _step)
                        return
                    state['attempts'] += 1
                    self._load_more_plugins()
                    QTimer.singleShot(120, _step)
                    return
                self._adjust_bottom_stretch()
                return
            if self._is_loading:
                QTimer.singleShot(120, _step)
                return
            state['attempts'] += 1
            self._load_more_plugins()
            QTimer.singleShot(120, _step)
        
        QTimer.singleShot(50, _step)
    
    def _ensure_category_scrollbar_visible(self):
        if not hasattr(self, '_scroll_area'):
            return
        if not getattr(self, '_selected_category', None):
            return
        state = {'attempts': 0}
        def _step():
            if state['attempts'] >= 10:
                self._adjust_bottom_stretch()
                return
            sb = self._scroll_area.verticalScrollBar()
            if (sb.maximum() > 0) or (self._category_loaded_count >= len(self._category_filtered_plugins)):
                try:
                    viewport_w = self._scroll_area.viewport().width()
                    cols = self._calc_cols(viewport_w)
                except Exception:
                    cols = max(1, int(self._current_cols) if hasattr(self, '_current_cols') else 1)
                remaining = len(self._category_filtered_plugins) - self._category_loaded_count
                need = (cols - (self._category_loaded_count % cols)) % cols
                if need > 0 and remaining > 0:
                    if self._is_loading:
                        QTimer.singleShot(120, _step)
                        return
                    state['attempts'] += 1
                    self._load_more_category()
                    QTimer.singleShot(120, _step)
                    return
                self._adjust_bottom_stretch()
                return
            if self._is_loading:
                QTimer.singleShot(120, _step)
                return
            state['attempts'] += 1
            self._load_more_category()
            QTimer.singleShot(120, _step)
        QTimer.singleShot(50, _step)
    
    def resizeEvent(self, event):
        """Handle window resize to update grid layout"""
        super().resizeEvent(event)
        # Debounce resize events to prevent performance issues
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()
            self._resize_timer.start(150)  # Wait 150ms after resize stops
    
    def _handle_resize(self):
        """Handle debounced resize event"""
        if not hasattr(self, 'grid_layout') or not self.plugins:
            return
            
        # Determine new column count using actual viewport width
        try:
            viewport_width = self._scroll_area.viewport().width() if self._scroll_area else self.width()
        except Exception:
            viewport_width = self.width()
        new_cols = self._calc_cols(viewport_width)
        
        # Only rebuild if column count changed
        if new_cols != self._current_cols:
            self._current_cols = new_cols
            self._stop_deferred_loads()
            # Use optimized layout update instead of full rebuild
            self._update_grid_layout()
    
    def _update_grid_layout(self):
        """Update grid layout without recreating cards"""
        if not self._all_cards:
            self.populate_app_cards()
            return
        if self._is_layouting:
            return
        self._begin_layout_update()
        
        try:
            # Clear layout items
            while self.grid_layout.count():
                _ = self.grid_layout.takeAt(0)
            
            # Reset row stretches before re-layout
            self._reset_row_stretches()
            
            # Get filtered cards
            filtered_cards = self._all_cards
            if self._selected_category:
                if hasattr(self, '_category_filtered_plugins') and self._category_loaded_count:
                    filtered_cards = [self._get_or_create_card(p) for p in self._category_filtered_plugins[:self._category_loaded_count]]
                else:
                    # Fallback build from full dataset
                    if not self._all_plugins:
                        self._all_plugins = get_all_plugins_data()
                    filtered_cards = [self._get_or_create_card(p) for p in self._all_plugins if self._category_for(p) == self._selected_category]
            
            # Re-layout with new column count
            cols = self._current_cols
            for i in range(cols):
                self.grid_layout.setColumnStretch(i, 1)
                try:
                    self.grid_layout.setColumnMinimumWidth(i, 340)
                except Exception:
                    pass
            
            for i, card_data in enumerate(filtered_cards):
                row = i // cols
                col = i % cols
                self.grid_layout.addWidget(card_data['widget'], row, col)
            max_row = ((len(filtered_cards) - 1) // cols) if filtered_cards else 0
            self.grid_layout.setRowStretch(max_row + 1, 1)
            self._enforce_row_min_heights(max_row)
            # Adjust the bottom stretch so we don't keep a big empty row once scrolling is available
            QTimer.singleShot(10, self._adjust_bottom_stretch)
            if self._selected_category:
                QTimer.singleShot(50, self._ensure_category_scrollbar_visible)
            else:
                QTimer.singleShot(50, self._ensure_scrollbar_visible)
        finally:
            self._finish_layout_update()
    
    def _on_scroll(self, value):
        """Handle scroll events to detect when user reaches bottom"""
        if self._is_loading or self._is_layouting or not hasattr(self, '_scroll_area'):
            return
            
        scrollbar = self._scroll_area.verticalScrollBar()
        max_value = scrollbar.maximum()
        
        if self._selected_category:
            if max_value - value <= 150 and self._category_loaded_count < len(self._category_filtered_plugins):
                if self._load_timer is not None:
                    self._load_timer.stop()
                self._load_timer = QTimer()
                self._load_timer.setSingleShot(True)
                self._load_timer.timeout.connect(self._load_more_category)
                self._load_timer.start(100)
        else:
            if max_value - value <= 150 and self._loaded_count < len(self._all_plugins):
                if self._load_timer is not None:
                    self._load_timer.stop()
                self._load_timer = QTimer()
                self._load_timer.setSingleShot(True)
                self._load_timer.timeout.connect(self._load_more_plugins)
                self._load_timer.start(100)
    
    def _load_more_plugins(self):
        """Load next batch of plugins with optimized performance"""
        if self._is_loading or self._loaded_count >= len(self._all_plugins):
            return
            
        self._is_loading = True
        self._begin_layout_update()
        self._loading_container.setVisible(True)
        
        # Calculate how many more plugins to load; align with row boundaries
        remaining = len(self._all_plugins) - self._loaded_count
        try:
            viewport_w = self._scroll_area.viewport().width()
        except Exception:
            viewport_w = self.width()
        cols = self._calc_cols(viewport_w)
        target_total = ((self._loaded_count + self._batch_size + cols - 1) // cols) * cols
        min_needed = max(cols, target_total - self._loaded_count)
        batch_size = min(remaining, min_needed)
        
        # Get next batch of plugins
        start_idx = self._loaded_count
        end_idx = start_idx + batch_size
        new_plugins = self._all_plugins[start_idx:end_idx]
        
        # Create cards for new plugins
        new_cards = []
        for plugin in new_plugins:
            installed = self.is_installed(plugin)
            icon = self._icon_for(plugin)
            card = self.create_app_card(plugin, icon, installed)
            card_data = {
                'plugin': plugin,
                'widget': card,
                'installed': installed
            }
            new_cards.append(card_data)
        
        # Add new cards to the grid - optimized positioning
        cols = self._current_cols
        
        # Pre-calculate maximum row needed
        max_position = self._loaded_count + len(new_cards) - 1
        max_row_needed = max_position // cols
        
        # Reset previous stretches so we don't leave a stretched empty row in the middle
        self._reset_row_stretches()
        
        # Add cards to grid positions
        for i, card_data in enumerate(new_cards):
            total_position = self._loaded_count + i
            row = total_position // cols
            col = total_position % cols
            self.grid_layout.addWidget(card_data['widget'], row, col)
        
        # Add a final stretch row to enable scrolling
        self.grid_layout.setRowStretch(max_row_needed + 1, 1)
        QTimer.singleShot(10, self._adjust_bottom_stretch)
        self._enforce_row_min_heights(max_row_needed)
        
        # Add to all_cards list
        self._all_cards.extend(new_cards)
        self._loaded_count += batch_size
        
        # Hide loading indicator after a short delay
        QTimer.singleShot(100, self._hide_loading_indicator)
        self._is_loading = False
        self._finish_layout_update()
    
    def _load_more_category(self):
        if self._is_loading or self._category_loaded_count >= len(self._category_filtered_plugins):
            return
        self._is_loading = True
        self._begin_layout_update()
        self._loading_container.setVisible(True)
        remaining = len(self._category_filtered_plugins) - self._category_loaded_count
        try:
            viewport_w = self._scroll_area.viewport().width()
        except Exception:
            viewport_w = self.width()
        cols = self._calc_cols(viewport_w)
        target_total = ((self._category_loaded_count + self._batch_size + cols - 1) // cols) * cols
        min_needed = max(cols, target_total - self._category_loaded_count)
        batch_size = min(remaining, min_needed)
        max_position = self._category_loaded_count + batch_size - 1
        max_row_needed = max_position // cols
        self._reset_row_stretches()
        for i in range(batch_size):
            total_position = self._category_loaded_count + i
            plugin = self._category_filtered_plugins[total_position]
            card_data = self._get_or_create_card(plugin)
            row = total_position // cols
            col = total_position % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)
        self.grid_layout.setRowStretch(max_row_needed + 1, 1)
        QTimer.singleShot(10, self._adjust_bottom_stretch)
        self._category_loaded_count += batch_size
        self._enforce_row_min_heights(max_row_needed)
        QTimer.singleShot(100, self._hide_loading_indicator)
        self._is_loading = False
    
    def apply_filters(self, filter_states):
        """Apply Available/Installed filters to the plugins view"""
        # Store current filter states
        self._current_filter_states = filter_states
        # Re-apply all filters (both status and source)
        self._apply_combined_filters()
    
    def apply_source_filters(self, source_states):
        """Apply source filters (pacman, AUR, Flatpak, npm) to the plugins view"""
        # Store current source states
        self._current_source_states = source_states
        # Re-apply all filters (both status and source)
        self._apply_combined_filters()
    
    def _apply_combined_filters(self):
        """Apply both status and source filters together"""
        # Create cards if not already created
        if not self._all_cards:
            self._create_all_cards()
        
        # Clear the grid layout
        while self.grid_layout.count():
            _ = self.grid_layout.takeAt(0)
        
        # Get filter states
        show_available = self._current_filter_states.get('Available', True)
        show_installed = self._current_filter_states.get('Installed', True)
        
        # Get source states
        show_pacman = self._current_source_states.get('pacman', True)
        show_aur = self._current_source_states.get('AUR', True)
        show_flatpak = self._current_source_states.get('Flatpak', True)
        show_npm = self._current_source_states.get('npm', True)
        
        # Filter cards based on both status and source
        filtered_cards = []
        for card_data in self._all_cards:
            plugin = card_data['plugin']
            is_installed = card_data['installed']
            
            # Check status filter
            status_match = (is_installed and show_installed) or (not is_installed and show_available)
            
            # Check source filter
            source = self._get_package_source(plugin).lower()
            source_match = False
            if source == 'pacman' and show_pacman:
                source_match = True
            elif source == 'aur' and show_aur:
                source_match = True
            elif source == 'flatpak' and show_flatpak:
                source_match = True
            elif source == 'npm' and show_npm:
                source_match = True
            
            # Include card only if both filters match
            if status_match and source_match:
                filtered_cards.append(card_data)
        
        # Use tracked column count
        cols = self._current_cols
        
        # Set column stretching dynamically
        for i in range(cols):
            self.grid_layout.setColumnStretch(i, 1)
        
        # Add filtered cards to layout and show them
        for i, card_data in enumerate(filtered_cards):
            row = i // cols
            col = i % cols
            card_data['widget'].show()
            self.grid_layout.addWidget(card_data['widget'], row, col)
