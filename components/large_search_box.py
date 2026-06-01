"""
LargeSearchBox Component - Large search box for package discovery
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QFrame, QGridLayout, QProgressBar, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor, QResizeEvent
from PyQt6.QtSvg import QSvgRenderer
import os
import psutil
import platform
import subprocess
import datetime
import re


class LargeSearchBox(QWidget):
    """Large search box component for discover page"""

    search_requested = pyqtSignal(str)  # Emits query for auto-search
    search_submitted = pyqtSignal(str)  # Emits query for explicit submit (enter/button)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_timer = QTimer()
        self.search_timer.setInterval(800)  # Faster response
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.on_auto_search)
        self.highlight_widgets = []
        self.compact_mode = False
        self.is_maximized_layout = False
        self.current_width = 0
        self.main_layout = None
        self.hero_card = None
        self.expanded_sections = None
        self.cpu_value_label = None
        self.memory_progress = None
        self.memory_percentage_label = None
        self.cpu_progress = None
        self.disk_progress = None
        self.disk_percentage_label = None
        self.system_update_timer = QTimer()
        self.progress_animations = []
        self.recent_updates_container = None
        self.recent_updates_layout = None
        self.recent_updates = []
        self.system_data_cache = {}
        self.cache_timestamp = 0
        self.cache_duration = 30  # Cache for 30 seconds
        self.layout_switching = False
        self.updates_timer = None
        self.system_update_timer.setInterval(2000)  # Update every 2 seconds
        self.system_update_timer.timeout.connect(self.update_system_health)
        self.init_ui()

    def init_ui(self):
        """Initialize the large search box UI with responsive design"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 30, 20, 30)
        self.main_layout.setSpacing(20)
        
        # Create main hero card
        self.create_hero_card()
        
        # Create expanded sections (initially hidden)
        self.create_expanded_sections()
        
        # Set initial layout - force compact mode initially
        self.current_width = 800  # Start with a typical window width
        self.is_maximized_layout = False
        self.rebuild_layout()
        self.setStyleSheet(self.get_stylesheet())

    def create_hero_card(self):
        """Create the main search card"""
        self.hero_card = QFrame()
        self.hero_card.setObjectName("largeSearchCard")
        self.hero_card_layout = QVBoxLayout(self.hero_card)
        
        # Initial layout - will be updated in update_hero_card_layout
        self.hero_card_layout.setContentsMargins(36, 40, 36, 40)
        self.hero_card_layout.setSpacing(24)

        # Title and subtitle
        self.title_label = QLabel("Discover New Packages")
        self.title_label.setObjectName("heroTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_card_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Search across pacman, AUR, Flatpak, and npm repositories")
        self.subtitle_label.setObjectName("heroSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_card_layout.addWidget(self.subtitle_label)

        # Search container
        self.create_search_container(self.hero_card_layout)
        
        # Highlights container
        self.create_highlights_container(self.hero_card_layout)

    def update_hero_card_layout(self):
        """Update hero card layout based on current mode"""
        if self.is_maximized_layout:
            # Much tighter spacing for maximized layout to fit 4 cards
            self.hero_card_layout.setContentsMargins(28, 24, 28, 24)
            self.hero_card_layout.setSpacing(14)
        else:
            # Normal spacing for compact layout
            self.hero_card_layout.setContentsMargins(36, 40, 36, 40)
            self.hero_card_layout.setSpacing(24)

    def create_search_container(self, parent_layout):
        """Create the search input container"""
        search_container = QWidget()
        search_container.setObjectName("largeSearchContainer")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(24, 18, 24, 18)
        search_layout.setSpacing(16)

        self.search_icon = QLabel()
        self.search_icon.setFixedSize(40, 40)
        self.search_icon.setObjectName("searchIconBubble")
        self.set_search_icon()
        search_layout.addWidget(self.search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Try \"system monitor\" or \"AUR helpers\"")
        self.search_input.setObjectName("largeSearchInput")
        self.search_input.setFixedHeight(48)
        self.search_input.returnPressed.connect(self.on_search_triggered)
        self.search_input.textChanged.connect(self.on_text_changed)
        search_layout.addWidget(self.search_input, 1)

        self.search_button = QPushButton("Search")
        self.search_button.setMinimumWidth(110)
        self.search_button.setFixedHeight(48)
        self.search_button.setObjectName("largeSearchButton")
        self.search_button.clicked.connect(self.on_search_triggered)
        self.set_button_icon()
        search_layout.addWidget(self.search_button)

        parent_layout.addWidget(search_container)

    def create_highlights_container(self, parent_layout):
        """Create highlights/feature cards container"""
        self.highlights_container = QWidget()
        self.highlights_container.setObjectName("highlightsContainer")
        
        # This will be dynamically set based on layout mode
        self.highlights_layout = QHBoxLayout(self.highlights_container)
        self.highlights_layout.setContentsMargins(0, 0, 0, 0)
        self.highlights_layout.setSpacing(18)

        parent_layout.addWidget(self.highlights_container)
        self.create_highlight_cards()

    def create_highlight_cards(self):
        """Create feature highlight cards"""
        # Clear existing widgets
        for widget in self.highlight_widgets:
            widget["card"].setParent(None)
        self.highlight_widgets.clear()

        # Define highlights based on layout mode
        if self.is_maximized_layout:
            highlights = [
                ("🚀", "Blazing Fast search", "Instant multi-repo search"),
                ("⭕", "Curated Collections", "Handpicked package sets"),
                ("⭐", "Curated results", "Trusted package picks"),
                ("⚙️", "Advanced User Tools", "Power user controls")
            ]
            # Adjust spacing for 4 cards
            self.highlights_layout.setSpacing(8)
        else:
            highlights = [
                ("🚀", "Instant multi repo search", "Instant unified search"),
                ("⭐", "Curated results", "Trusted package picks"),
                ("⚙️", "Power user ready", "Advanced user control")
            ]
            # Normal spacing for 3 cards
            self.highlights_layout.setSpacing(18)

        for highlight_data in highlights:
            emoji, title, description = highlight_data
            highlight_card = QFrame()
            highlight_card.setObjectName("highlightCard")
            
            # Set card height constraints based on layout mode
            if self.is_maximized_layout:
                highlight_card.setMinimumHeight(80)
                highlight_card.setMaximumHeight(100)
            else:
                highlight_card.setMinimumHeight(120)
                highlight_card.setMaximumHeight(150)
            
            # Adjust card margins for maximized layout
            if self.is_maximized_layout:
                card_layout_inner = QVBoxLayout(highlight_card)
                card_layout_inner.setContentsMargins(12, 10, 12, 10)
                card_layout_inner.setSpacing(3)
            else:
                card_layout_inner = QVBoxLayout(highlight_card)
                card_layout_inner.setContentsMargins(20, 20, 20, 20)
                card_layout_inner.setSpacing(8)

            icon_label = QLabel(emoji)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            icon_label.setObjectName("highlightIcon")
            
            # Set font sizes based on layout mode
            if self.is_maximized_layout:
                # Smaller fonts for 4-card layout
                icon_font = icon_label.font()
                icon_font.setPointSize(18)
                icon_label.setFont(icon_font)
            else:
                # Larger fonts for 3-card layout
                icon_font = icon_label.font()
                icon_font.setPointSize(24)
                icon_label.setFont(icon_font)
            
            card_layout_inner.addWidget(icon_label)

            title_label = QLabel(title)
            title_label.setObjectName("highlightTitle")
            title_label.setWordWrap(True)
            
            # Set title font size based on layout mode
            if self.is_maximized_layout:
                title_font = title_label.font()
                title_font.setPointSize(11)
                title_font.setBold(True)
                title_label.setFont(title_font)
            else:
                title_font = title_label.font()
                title_font.setPointSize(15)
                title_font.setBold(True)
                title_label.setFont(title_font)
            
            card_layout_inner.addWidget(title_label)

            description_label = QLabel(description)
            description_label.setObjectName("highlightDescription")
            description_label.setWordWrap(True)
            
            # Set description font size based on layout mode
            if self.is_maximized_layout:
                desc_font = description_label.font()
                desc_font.setPointSize(8)
                description_label.setFont(desc_font)
            else:
                desc_font = description_label.font()
                desc_font.setPointSize(11)
                description_label.setFont(desc_font)
            
            card_layout_inner.addWidget(description_label)

            # Add stretch to push content to top
            card_layout_inner.addStretch()

            self.highlight_widgets.append({
                "card": highlight_card,
                "icon": icon_label,
                "title": title_label,
                "desc": description_label,
            })

            self.highlights_layout.addWidget(highlight_card, 1)

    def create_expanded_sections(self):
        """Create additional sections for maximized layout"""
        self.expanded_sections = QWidget()
        self.expanded_sections.setObjectName("expandedSections")
        expanded_layout = QHBoxLayout(self.expanded_sections)
        expanded_layout.setContentsMargins(0, 20, 0, 0)
        expanded_layout.setSpacing(20)

        # Recent Updates section
        recent_updates = self.create_recent_updates_section()
        expanded_layout.addWidget(recent_updates, 1)

        # System Health section
        system_health = self.create_system_health_section()
        expanded_layout.addWidget(system_health, 1)

        self.expanded_sections.hide()  # Initially hidden
        
        # Initialize system health data
        self.update_system_health()
        
        # Set up timer to refresh updates periodically
        self.updates_timer = QTimer()
        self.updates_timer.setInterval(300000)  # Refresh every 5 minutes
        self.updates_timer.timeout.connect(self.refresh_updates)
        
    def refresh_updates(self):
        """Refresh the recent updates display"""
        if self.is_maximized_layout and self.recent_updates_container:
            self.load_recent_updates()

    def create_recent_updates_section(self):
        """Create enhanced Recent Updates section with real package data"""
        section = QFrame()
        section.setObjectName("recentUpdatesSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Header with title and refresh button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title = QLabel("Recent Updates")
        title.setObjectName("recentUpdatesTitle")
        header_layout.addWidget(title)

        # Last updated indicator
        last_updated = QLabel("Live")
        last_updated.setObjectName("lastUpdatedLabel")
        header_layout.addWidget(last_updated)
        
        header_layout.addStretch()
        layout.addWidget(header_container)

        # Updates container (will be populated dynamically)
        self.recent_updates_container = QWidget()
        self.recent_updates_layout = QVBoxLayout(self.recent_updates_container)
        self.recent_updates_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_updates_layout.setSpacing(12)
        
        layout.addWidget(self.recent_updates_container)
        
        # Add subtle shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        section.setGraphicsEffect(shadow)

        # Load initial updates
        self.load_recent_updates()

        return section

    @staticmethod
    def get_package_icon(package_name):
        """Get appropriate icon for package type"""
        package_name = package_name.lower()
        
        # System packages
        if any(sys_pkg in package_name for sys_pkg in ['kernel', 'systemd', 'glibc', 'gcc']):
            return "⚙️"  # Gear for system packages
        # Development tools
        elif any(dev_pkg in package_name for dev_pkg in ['python', 'nodejs', 'git', 'vim', 'code', 'gcc', 'make']):
            return "🛠️"  # Hammer and wrench for dev tools
        # Media packages
        elif any(media_pkg in package_name for media_pkg in ['ffmpeg', 'vlc', 'gimp', 'blender']):
            return "🎨"  # Artist palette for media
        # Network/web packages
        elif any(net_pkg in package_name for net_pkg in ['firefox', 'chrome', 'wget', 'curl', 'nginx']):
            return "🌐"  # Globe for network
        # Gaming
        elif any(game_pkg in package_name for game_pkg in ['steam', 'wine', 'lutris']):
            return "🎮"  # Game controller
        # Security
        elif any(sec_pkg in package_name for sec_pkg in ['gpg', 'ssh', 'openssl']):
            return "🔒"  # Lock for security
        else:
            return "📦"  # Package for general packages

    @staticmethod
    def format_time_ago(timestamp):
        """Format timestamp to human-readable time ago"""
        try:
            now = datetime.datetime.now()
            diff = now - timestamp
            
            if diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours}h ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            else:
                return "Just now"
        except Exception:
            return "Unknown"

    def load_recent_updates(self):
        """Load recent package updates from system logs"""
        try:
            # Clear existing updates
            while self.recent_updates_layout.count():
                child = self.recent_updates_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Get recent pacman updates from log
            updates = self.get_pacman_updates()
            
            if not updates:
                # Show system status instead of empty message
                self.show_system_status()
                return
            
            # Display up to 4 most recent updates
            for update in updates[:4]:
                self.create_update_item(update)
                
        except Exception:
            self.show_system_status()  # Show system status instead of error

    @staticmethod
    def get_pacman_updates():
        """Get recent pacman updates from system log"""
        updates = []
        try:
            # Try to read pacman log
            result = subprocess.run(
                ['/usr/bin/tail', '-n', '50', '/var/log/pacman.log'],
                capture_output=True, text=True, timeout=5, check=False
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if '[ALPM] upgraded' in line or '[ALPM] installed' in line:
                        match = re.search(r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}).*\] \[ALPM\] (upgraded|installed) ([^\s]+) \(([^)]+)\)', line)
                        if match:
                            timestamp_str, action, package, version = match.groups()
                            timestamp = datetime.datetime.fromisoformat(timestamp_str)
                            updates.append({
                                'package': package,
                                'version': version,
                                'action': action,
                                'timestamp': timestamp
                            })
            
            # Sort by timestamp (newest first)
            updates.sort(key=lambda x: x['timestamp'], reverse=True)
            
        except Exception:
            # Return empty list to show system status instead
            updates = []
        
        return updates

    def create_update_item(self, update_data):
        """Create a modern update item widget"""
        item = QFrame()
        item.setObjectName("modernUpdateItem")
        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(16, 12, 16, 12)
        item_layout.setSpacing(14)

        # Package icon with background
        icon_container = QFrame()
        icon_container.setObjectName("updateIconContainer")
        icon_container.setFixedSize(40, 40)
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel(self.get_package_icon(update_data['package']))
        icon_label.setObjectName("updatePackageIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        item_layout.addWidget(icon_container)

        # Package info container
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        # Package name and action
        name_action = QLabel(f"{update_data['package']} {update_data['action']}")
        name_action.setObjectName("updatePackageName")
        info_layout.addWidget(name_action)

        # Version info
        version_label = QLabel(f"Version {update_data['version']}")
        version_label.setObjectName("updateVersion")
        info_layout.addWidget(version_label)

        item_layout.addWidget(info_container, 1)

        # Time ago
        time_label = QLabel(self.format_time_ago(update_data['timestamp']))
        time_label.setObjectName("updateTime")
        item_layout.addWidget(time_label)

        self.recent_updates_layout.addWidget(item)

    def show_system_status(self):
        """Show useful system information when no updates are available"""
        try:
            # Load basic info first (fast)
            uptime_info = self.get_system_uptime()
            self.create_status_item("⏱️", "System Uptime", uptime_info, "System running smoothly")
            
            boot_time = self.get_last_boot_time()
            self.create_status_item("🚀", "Last Boot", boot_time, "System startup")
            
            # Load heavier operations asynchronously
            QTimer.singleShot(100, self.load_package_info)
            QTimer.singleShot(300, self.load_update_info)
            
        except Exception:
            # Fallback to basic system info
            self.create_status_item("💻", "System Status", "Running", "All systems operational")
            self.create_status_item("📊", "Package Manager", "Ready", "Pacman available")
    
    def load_package_info(self):
        """Load package information asynchronously"""
        try:
            pkg_count = self.get_package_count()
            self.create_status_item("📦", "Installed Packages", f"{pkg_count} packages", "System packages")
        except Exception:
            self.create_status_item("📦", "Installed Packages", "Unknown", "System packages")
    
    def load_update_info(self):
        """Load update information asynchronously"""
        try:
            available_updates = self.check_available_updates()
            self.create_status_item("🔄", "Available Updates", available_updates, "Package manager")
        except Exception:
            self.create_status_item("🔄", "Available Updates", "Check manually", "Package manager")

    def get_cached_system_data(self, key, fetch_func):
        """Get cached system data or fetch if expired"""
        current_time = datetime.datetime.now().timestamp()
        
        # Check if cache is valid
        if (key in self.system_data_cache and 
            current_time - self.cache_timestamp < self.cache_duration):
            return self.system_data_cache[key]
        
        # Fetch new data
        try:
            data = fetch_func()
            self.system_data_cache[key] = data
            self.cache_timestamp = current_time
            return data
        except Exception:
            # Return cached data if available, otherwise default
            return self.system_data_cache.get(key, "Unknown")
    
    def get_system_uptime(self):
        """Get system uptime information with caching"""
        def fetch_uptime():
            boot_time = psutil.boot_time()
            uptime_seconds = datetime.datetime.now().timestamp() - boot_time
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            
            if days > 0:
                return f"{days}d {hours}h"
            elif hours > 0:
                return f"{hours}h {int((uptime_seconds % 3600) // 60)}m"
            else:
                return f"{int(uptime_seconds // 60)}m"
        
        return self.get_cached_system_data('uptime', fetch_uptime)

    def get_package_count(self):
        """Get installed package count with caching"""
        def fetch_package_count():
            result = subprocess.run(
                ['/usr/bin/pacman', '-Q'], 
                capture_output=True, text=True, timeout=3, check=False
            )
            if result.returncode == 0:
                return len(result.stdout.strip().split('\n'))
            return "Unknown"
        
        return self.get_cached_system_data('package_count', fetch_package_count)

    def get_last_boot_time(self):
        """Get last boot time with caching"""
        def fetch_boot_time():
            boot_time = psutil.boot_time()
            boot_datetime = datetime.datetime.fromtimestamp(boot_time)
            now = datetime.datetime.now()
            diff = now - boot_datetime
            
            if diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours}h ago"
            else:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
        
        return self.get_cached_system_data('boot_time', fetch_boot_time)

    def check_available_updates(self):
        """Check for available updates with caching and timeout optimization"""
        def fetch_updates():
            # Use faster timeout for better responsiveness
            result = subprocess.run(
                ['/usr/bin/checkupdates'], 
                capture_output=True, text=True, timeout=5, check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                count = len(result.stdout.strip().split('\n'))
                return f"{count} available"
            else:
                return "Up to date"
        
        return self.get_cached_system_data('available_updates', fetch_updates)

    def create_status_item(self, icon, title, value, description):
        """Create a system status item"""
        item = QFrame()
        item.setObjectName("modernUpdateItem")
        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(16, 12, 16, 12)
        item_layout.setSpacing(14)

        # Icon with background
        icon_container = QFrame()
        icon_container.setObjectName("updateIconContainer")
        icon_container.setFixedSize(40, 40)
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel(icon)
        icon_label.setObjectName("updatePackageIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        item_layout.addWidget(icon_container)

        # Info container
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("updatePackageName")
        info_layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setObjectName("updateVersion")
        info_layout.addWidget(desc_label)

        item_layout.addWidget(info_container, 1)

        # Value
        value_label = QLabel(value)
        value_label.setObjectName("updateTime")
        item_layout.addWidget(value_label)

        self.recent_updates_layout.addWidget(item)

    def create_system_health_section(self):
        """Create enhanced System Health section with modern design"""
        section = QFrame()
        section.setObjectName("systemHealthSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Header with title and status indicator
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title = QLabel("System Health")
        title.setObjectName("systemHealthTitle")
        header_layout.addWidget(title)

        # Status indicator
        status_indicator = QLabel("●")
        status_indicator.setObjectName("systemHealthStatus")
        header_layout.addWidget(status_indicator)
        
        header_layout.addStretch()
        layout.addWidget(header_container)

        # Metrics grid container
        metrics_container = QWidget()
        metrics_layout = QVBoxLayout(metrics_container)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(16)

        # CPU Usage Card
        cpu_card = self.create_metric_card("🖥️", "CPU Usage", "cpu")
        metrics_layout.addWidget(cpu_card)

        # Memory Usage Card
        memory_card = self.create_metric_card("💾", "Memory Usage", "memory")
        metrics_layout.addWidget(memory_card)

        # Disk Usage Card
        disk_card = self.create_metric_card("💿", "Disk Usage", "disk")
        metrics_layout.addWidget(disk_card)

        layout.addWidget(metrics_container)
        
        # Add subtle shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        section.setGraphicsEffect(shadow)

        return section

    def create_metric_card(self, icon, label_text, metric_type):
        """Create a modern metric card with progress visualization"""
        card = QFrame()
        card.setObjectName("metricCard")
        card.setFixedHeight(70)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Header row with icon, label, and value
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Icon with background
        icon_container = QFrame()
        icon_container.setObjectName("metricIconContainer")
        icon_container.setFixedSize(36, 36)
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel(icon)
        icon_label.setObjectName("metricIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        header_layout.addWidget(icon_container)

        # Label
        label = QLabel(label_text)
        label.setObjectName("metricLabel")
        header_layout.addWidget(label, 1)

        # Value label
        value_label = QLabel("Loading...")
        value_label.setObjectName("metricValue")
        header_layout.addWidget(value_label)

        layout.addLayout(header_layout)

        # Progress bar
        progress = QProgressBar()
        progress.setObjectName(f"{metric_type}Progress")
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setFixedHeight(6)
        layout.addWidget(progress)

        # Store references for updates
        if metric_type == "cpu":
            self.cpu_value_label = value_label
            self.cpu_progress = progress
        elif metric_type == "memory":
            self.memory_percentage_label = value_label
            self.memory_progress = progress
        elif metric_type == "disk":
            self.disk_percentage_label = value_label
            self.disk_progress = progress

        return card

    def animate_progress_bar(self, progress_bar, target_value):
        """Animate progress bar to target value with smooth transition"""
        if not progress_bar:
            return
            
        animation = QPropertyAnimation(progress_bar, b"value")
        animation.setDuration(800)  # 800ms animation
        animation.setStartValue(progress_bar.value())
        animation.setEndValue(int(target_value))
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Store animation reference to prevent garbage collection
        self.progress_animations.append(animation)
        animation.finished.connect(lambda: self.progress_animations.remove(animation))
        
        animation.start()

    def update_system_health(self):
        """Update system health metrics with real data"""
        try:
            # Get CPU usage (average over 1 second)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if self.cpu_value_label:
                self.cpu_value_label.setText(f"{cpu_percent:.1f}%")
            if self.cpu_progress:
                self.animate_progress_bar(self.cpu_progress, cpu_percent)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            if self.memory_progress:
                self.animate_progress_bar(self.memory_progress, memory_percent)
            if self.memory_percentage_label:
                self.memory_percentage_label.setText(f"{memory_percent:.1f}%")
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if self.disk_progress:
                self.animate_progress_bar(self.disk_progress, disk_percent)
            if self.disk_percentage_label:
                self.disk_percentage_label.setText(f"{disk_percent:.1f}%")
                
        except Exception:
            # Fallback to static data if psutil fails
            if self.cpu_value_label:
                self.cpu_value_label.setText("N/A")
            if self.cpu_progress:
                self.animate_progress_bar(self.cpu_progress, 0)
            if self.memory_percentage_label:
                self.memory_percentage_label.setText("N/A")
            if self.memory_progress:
                self.animate_progress_bar(self.memory_progress, 0)
            if self.disk_percentage_label:
                self.disk_percentage_label.setText("N/A")
            if self.disk_progress:
                self.animate_progress_bar(self.disk_progress, 0)

    def showEvent(self, event):
        """Handle widget show events"""
        super().showEvent(event)
        # Ensure layout is properly set when widget becomes visible
        if self.width() > 0:
            self.current_width = self.width()
            self.update_layout_for_size()

    def resizeEvent(self, event: QResizeEvent):
        """Handle window resize events"""
        super().resizeEvent(event)
        new_width = event.size().width()
        
        # Only update if width changed significantly (avoid excessive updates)
        if abs(new_width - self.current_width) > 50:
            self.current_width = new_width
            self.update_layout_for_size()

    def update_layout_for_size(self):
        """Update layout based on current window size with performance optimization"""
        if self.layout_switching:
            return  # Prevent recursive calls during layout switching
            
        # Get actual widget width if available, fallback to current_width
        actual_width = max(self.width(), self.current_width)
        
        # Determine if we should use maximized layout (wider than 1200px)
        should_be_maximized = actual_width > 1200
        
        if should_be_maximized != self.is_maximized_layout:
            self.layout_switching = True
            self.is_maximized_layout = should_be_maximized
            
            # Use QTimer.singleShot to defer heavy operations
            if should_be_maximized:
                self.rebuild_layout()
                # Defer data loading to avoid blocking UI
                QTimer.singleShot(100, self.load_maximized_data)
            else:
                self.rebuild_layout()
                self.system_update_timer.stop()
                self.updates_timer.stop()
            
            self.layout_switching = False
        
        # Update margins based on width
        if actual_width > 1400:
            margins = (60, 40, 60, 40)
        elif actual_width > 1000:
            margins = (40, 30, 40, 30)
        else:
            margins = (20, 30, 20, 30)
        
        self.main_layout.setContentsMargins(*margins)
    
    def load_maximized_data(self):
        """Load data for maximized layout with performance optimization"""
        if self.is_maximized_layout:
            # Start timers first for immediate feedback
            self.system_update_timer.start()
            self.updates_timer.start()
            
            # Load system health data (lightweight)
            QTimer.singleShot(50, self.update_system_health)
            
            # Load recent updates data (heavier operation)
            if self.recent_updates_container:
                QTimer.singleShot(200, self.load_recent_updates)

    def rebuild_layout(self):
        """Rebuild the layout when switching between modes"""
        # Clear current layout
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        if self.is_maximized_layout:
            # Maximized layout: hero card + expanded sections
            self.main_layout.addWidget(self.hero_card)
            self.main_layout.addWidget(self.expanded_sections)
            self.expanded_sections.show()
        else:
            # Compact layout: centered hero card
            self.main_layout.addStretch()
            self.main_layout.addWidget(self.hero_card, alignment=Qt.AlignmentFlag.AlignCenter)
            self.main_layout.addStretch()
            self.expanded_sections.hide()
        
        # Update hero card layout for new mode
        self.update_hero_card_layout()
        
        # Recreate highlight cards for new layout
        self.create_highlight_cards()

    def set_search_icon(self):
        """Set the search icon in the input area"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "discover", "search.svg")
            if os.path.exists(icon_path):
                svg_renderer = QSvgRenderer(icon_path)
                if svg_renderer.isValid():
                    pixmap = QPixmap(32, 32)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    with QPainter(pixmap) as painter:
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        svg_renderer.render(painter, QRectF(pixmap.rect()))
                        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                        painter.fillRect(pixmap.rect(), QColor("#666666"))
                    self.search_icon.setPixmap(pixmap)
                else:
                    self.search_icon.setText("🔍")
            else:
                self.search_icon.setText("🔍")
        except Exception:
            self.search_icon.setText("🔍")

    def set_button_icon(self):
        """Set the search button icon"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "discover", "search.svg")
            if os.path.exists(icon_path):
                svg_renderer = QSvgRenderer(icon_path)
                if svg_renderer.isValid():
                    pixmap = QPixmap(24, 24)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    with QPainter(pixmap) as painter:
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        svg_renderer.render(painter, QRectF(pixmap.rect()))
                        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                        painter.fillRect(pixmap.rect(), QColor("white"))
                    self.search_button.setIcon(QIcon(pixmap))
                    self.search_button.setIconSize(QSize(24, 24))
                else:
                    self.search_button.setText("🔍")
            else:
                self.search_button.setText("🔍")
        except Exception:
            self.search_button.setText("🔍")

    def on_text_changed(self):
        """Start auto-search timer when text changes"""
        self.search_timer.start()

    def on_auto_search(self):
        """Perform auto-search when timer times out"""
        query = self.search_input.text().strip()
        if len(query) >= 3:  # Only search if 3+ characters
            self.search_requested.emit(query)

    def on_search_triggered(self):
        """Handle search trigger (enter or button click)"""
        query = self.search_input.text().strip()
        if query:
            self.search_timer.stop()  # Stop any pending auto-search
            self.search_submitted.emit(query)

    def set_compact_mode(self, compact: bool):
        self.compact_mode = compact
        for w in self.highlight_widgets:
            try:
                w["icon"].setVisible(not compact)
                w["desc"].setVisible(not compact)
                w["title"].setVisible(True)
            except Exception:
                pass

    def get_stylesheet(self):
        """Get stylesheet for this component"""
        return """
            LargeSearchBox {
                background-color: transparent;
            }

            QFrame#largeSearchCard {
                background-color: rgba(32, 34, 40, 0.95);
                border-radius: 28px;
                border: 1px solid rgba(0, 191, 174, 0.18);
            }

            QLabel#heroTitle {
                color: #F6F7FB;
                font-size: 28px;
                font-weight: 600;
                letter-spacing: 0.6px;
            }

            QLabel#heroSubtitle {
                color: #AEB4C2;
                font-size: 16px;
            }

            QWidget#largeSearchContainer {
                background-color: rgba(20, 22, 28, 0.9);
                border-radius: 28px;
                border: 1px solid rgba(0, 191, 174, 0.35);
            }

            QWidget#largeSearchContainer:hover {
                border-color: rgba(0, 230, 214, 0.65);
                background-color: rgba(22, 26, 34, 0.95);
            }

            QLabel#searchIconBubble {
                background-color: rgba(0, 191, 174, 0.12);
                border-radius: 20px;
                padding: 4px;
            }

            QLineEdit#largeSearchInput {
                background-color: transparent;
                border: none;
                color: #F0F3F5;
                font-size: 18px;
                font-weight: 400;
                padding: 8px 0px;
                selection-background-color: rgba(0, 191, 174, 0.3);
            }

            QLineEdit#largeSearchInput::placeholder {
                color: #8C94A4;
                font-size: 17px;
            }

            QLineEdit#largeSearchInput:focus {
                outline: none;
            }

            QPushButton#largeSearchButton {
                background-color: #00BFAE;
                border: none;
                border-radius: 24px;
                padding: 0 24px;
                color: #081017;
                font-size: 17px;
                font-weight: 600;
            }

            QPushButton#largeSearchButton:hover {
                background-color: #00D4C1;
            }

            QPushButton#largeSearchButton:pressed {
                background-color: #009688;
            }

            QWidget#highlightsContainer {
                background-color: transparent;
            }

            QFrame#highlightCard {
                background-color: rgba(18, 21, 27, 0.9);
                border-radius: 18px;
                border: 1px solid rgba(0, 191, 174, 0.14);
                min-height: 100px;
            }

            QFrame#highlightCard:hover {
                background-color: rgba(22, 26, 34, 0.95);
                border-color: rgba(0, 191, 174, 0.25);
            }

            QLabel#highlightIcon {
                font-size: 24px;
            }

            QLabel#highlightTitle {
                color: #EAF6F5;
                font-size: 15px;
                font-weight: 600;
                line-height: 1.2em;
            }

            QLabel#highlightDescription {
                color: #9CA6B4;
                font-size: 11px;
                line-height: 1.4em;
            }

            /* Expanded Sections Styles */
            QWidget#expandedSections {
                background-color: transparent;
            }

            QFrame#expandedSection {
                background-color: rgba(28, 30, 36, 0.95);
                border-radius: 20px;
                border: 1px solid rgba(0, 191, 174, 0.12);
            }

            QLabel#sectionTitle {
                color: #F6F7FB;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 8px;
            }

            /* Enhanced Recent Updates Styles */
            QFrame#recentUpdatesSection {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(32, 34, 40, 0.98),
                    stop:0.5 rgba(28, 30, 36, 0.95),
                    stop:1 rgba(24, 26, 32, 0.92));
                border-radius: 24px;
                border: 1px solid rgba(0, 191, 174, 0.15);
            }

            QLabel#recentUpdatesTitle {
                color: #F6F7FB;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }

            QLabel#lastUpdatedLabel {
                color: #00E6D6;
                font-size: 11px;
                font-weight: 600;
                background-color: rgba(0, 230, 214, 0.12);
                padding: 3px 8px;
                border-radius: 10px;
                border: 1px solid rgba(0, 230, 214, 0.2);
            }

            QFrame#modernUpdateItem {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 22, 28, 0.9),
                    stop:1 rgba(16, 18, 24, 0.85));
                border-radius: 16px;
                border: 1px solid rgba(0, 191, 174, 0.08);
            }

            QFrame#modernUpdateItem:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(24, 26, 32, 0.95),
                    stop:1 rgba(20, 22, 28, 0.9));
                border-color: rgba(0, 191, 174, 0.18);
            }

            QFrame#updateIconContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(100, 150, 255, 0.15),
                    stop:1 rgba(0, 191, 174, 0.12));
                border-radius: 20px;
                border: 1px solid rgba(100, 150, 255, 0.2);
            }

            QLabel#updatePackageIcon {
                color: #6496FF;
                font-size: 18px;
                font-weight: 600;
            }

            QLabel#updatePackageName {
                color: #E8F4F3;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }

            QLabel#updateVersion {
                color: #9CA6B4;
                font-size: 12px;
                font-weight: 400;
            }

            QLabel#updateTime {
                color: #00BFAE;
                font-size: 12px;
                font-weight: 700;
                background-color: rgba(0, 191, 174, 0.08);
                padding: 4px 8px;
                border-radius: 8px;
                border: 1px solid rgba(0, 191, 174, 0.15);
                min-width: 50px;
            }

            QLabel#noUpdatesMessage {
                color: #9CA6B4;
                font-size: 14px;
                font-style: italic;
                padding: 20px;
            }

            QLabel#errorMessage {
                color: #FF6B6B;
                font-size: 12px;
                padding: 20px;
            }

            /* Enhanced System Health Styles */
            QFrame#systemHealthSection {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(32, 34, 40, 0.98),
                    stop:0.5 rgba(28, 30, 36, 0.95),
                    stop:1 rgba(24, 26, 32, 0.92));
                border-radius: 24px;
                border: 1px solid rgba(0, 191, 174, 0.15);
            }

            QLabel#systemHealthTitle {
                color: #F6F7FB;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }

            QLabel#systemHealthStatus {
                color: #00E6D6;
                font-size: 12px;
                margin-left: 8px;
            }

            QFrame#metricCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 22, 28, 0.9),
                    stop:1 rgba(16, 18, 24, 0.85));
                border-radius: 16px;
                border: 1px solid rgba(0, 191, 174, 0.08);
            }

            QFrame#metricCard:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(24, 26, 32, 0.95),
                    stop:1 rgba(20, 22, 28, 0.9));
                border-color: rgba(0, 191, 174, 0.18);
            }

            QFrame#metricIconContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 191, 174, 0.15),
                    stop:1 rgba(0, 230, 214, 0.12));
                border-radius: 18px;
                border: 1px solid rgba(0, 191, 174, 0.2);
            }

            QLabel#metricIcon {
                color: #00E6D6;
                font-size: 18px;
                font-weight: 600;
            }

            QLabel#metricLabel {
                color: #E8F4F3;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }

            QLabel#metricValue {
                color: #00BFAE;
                font-size: 14px;
                font-weight: 700;
                background-color: rgba(0, 191, 174, 0.08);
                padding: 4px 8px;
                border-radius: 8px;
                border: 1px solid rgba(0, 191, 174, 0.15);
            }

            /* CPU Progress Bar */
            QProgressBar#cpuProgress {
                background-color: rgba(16, 18, 24, 0.8);
                border-radius: 3px;
                border: none;
            }

            QProgressBar#cpuProgress::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF6B6B, stop:0.3 #FF8E53, stop:0.7 #FF6B35, stop:1 #E74C3C);
                border-radius: 3px;
            }

            /* Memory Progress Bar */
            QProgressBar#memoryProgress {
                background-color: rgba(16, 18, 24, 0.8);
                border-radius: 3px;
                border: none;
            }

            QProgressBar#memoryProgress::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00BFAE, stop:0.3 #00D4C1, stop:0.7 #00E6D6, stop:1 #4ECDC4);
                border-radius: 3px;
            }

            /* Disk Progress Bar */
            QProgressBar#diskProgress {
                background-color: rgba(16, 18, 24, 0.8);
                border-radius: 3px;
                border: none;
            }

            QProgressBar#diskProgress::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9B59B6, stop:0.3 #8E44AD, stop:0.7 #A569BD, stop:1 #BB8FCE);
                border-radius: 3px;
            }
        """
