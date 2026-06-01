"""
SourceItem Component - Individual source selection widget
"""

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QGraphicsDropShadowEffect
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtSvg import QSvgRenderer


class SourceItem(QWidget):
    """Component for individual source selection with icon and checkbox"""

    def __init__(self, source_name, icon_path, parent=None):
        super().__init__(parent)
        self.source_name = source_name
        self.icon_path = icon_path
        self.checked = True
        self.init_ui()

    def init_ui(self):
        """Initialize the source item UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Icon container with better styling
        self.icon_container = QWidget()
        self.icon_container.setFixedSize(40, 40)
        self.icon_container.setObjectName("sourceIconContainer")

        icon_layout = QVBoxLayout(self.icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_icon(self.icon_path)
        icon_layout.addWidget(self.icon_label)

        # Checkbox with better styling
        self.checkbox = QCheckBox(self.source_name)
        self.checkbox.setChecked(self.checked)
        self.checkbox.setObjectName("sourceCheckbox")

        layout.addWidget(self.icon_container)
        layout.addWidget(self.checkbox, 1)

        # Connect signals
        self.checkbox.stateChanged.connect(self.on_state_changed)

        # Accent and interactivity
        self.accent_hex = self.get_accent_color(self.source_name)
        self.accent_color = QColor(self.accent_hex)
        self.apply_accent_styles()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(f"Search {self.source_name}")

        # Subtle shadow for icon
        try:
            shadow = QGraphicsDropShadowEffect(self.icon_container)
            shadow.setBlurRadius(12)
            shadow.setOffset(0, 2)
            c = QColor(self.accent_color)
            c.setAlpha(80)
            shadow.setColor(c)
            self.icon_container.setGraphicsEffect(shadow)
        except ImportError:
            # Handle missing graphics effect support gracefully
            pass

        # Apply styling
        self.setStyleSheet(self.get_stylesheet())
        self.update_visual_state()

    def set_icon(self, icon_path):
        """Set the icon for this source item"""
        # Use reliable styled text icons that match your SVG colors
        icon_styles = {
            "pacman": {
                "text": "●",  # Solid circle for Pac-Man
                "color": "#0073e1",  # Your exact blue color
                "size": "16px",
                "bg_color": "rgba(0, 115, 225, 0.15)"
            },
            "aur": {
                "text": "▲",  # Triangle for AUR
                "color": "#ff9955",  # Your exact orange color
                "size": "14px",
                "bg_color": "rgba(255, 153, 85, 0.15)"
            },
            "flatpak": {
                "text": "📦",  # Package box
                "color": "#4CAF50",  # Green color matching the SVG
                "size": "14px",
                "bg_color": "rgba(76, 175, 80, 0.15)"
            },
            "npm": {
                "text": "◆",  # Diamond shape
                "color": "#cb3837",  # npm red
                "size": "14px",
                "bg_color": "rgba(203, 56, 55, 0.15)"
            },
            "local": {
                "text": "🏠",  # House for local
                "color": "#00BFAE",
                "size": "14px",
                "bg_color": "rgba(0, 191, 174, 0.15)"
            }
        }
        
        source_key = self.source_name.lower()
        if source_key in icon_styles:
            style = icon_styles[source_key]
            self.icon_label.setText(style["text"])
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {style["size"]};
                    color: {style["color"]};
                    font-weight: bold;
                    background-color: {style["bg_color"]};
                    border-radius: 12px;
                    padding: 4px;
                    border: 1px solid {style["color"]};
                    text-align: center;
                }}
            """)
        else:
            self._set_fallback_icon()
        
        # Now that we know SVG works, let's try loading it properly
        if self._try_load_svg_properly(icon_path):
            return
    
    def _try_load_svg(self, icon_path):
        """Try to load and render the actual SVG file"""
        try:
            if not os.path.exists(icon_path):
                print(f"SVG file not found: {icon_path}")
                return False
                
            # Read SVG content and clean it up more thoroughly
            with open(icon_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Remove problematic Inkscape elements that cause rendering issues
            import re
            
            # Remove Inkscape-specific namespaces and elements
            svg_content = re.sub(r'xmlns:inkscape="[^"]*"', '', svg_content)
            svg_content = re.sub(r'xmlns:sodipodi="[^"]*"', '', svg_content)
            svg_content = re.sub(r'<sodipodi:namedview[^>]*>.*?</sodipodi:namedview>', '', svg_content, flags=re.DOTALL)
            svg_content = re.sub(r'<defs[^>]*>\s*</defs>', '', svg_content)
            svg_content = re.sub(r'inkscape:[^=]*="[^"]*"', '', svg_content)
            svg_content = re.sub(r'sodipodi:[^=]*="[^"]*"', '', svg_content)
            
            # Create SVG renderer from cleaned content
            svg_renderer = QSvgRenderer()
            if not svg_renderer.load(svg_content.encode('utf-8')):
                print(f"Failed to load cleaned SVG: {self.source_name}")
                return False
                
            if svg_renderer.isValid():
                # Create pixmap with white background first to test
                size = 32
                pixmap = QPixmap(size, size)
                pixmap.fill(QColor(255, 255, 255, 0))  # Fully transparent

                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
                
                # Set composition mode to ensure proper alpha blending
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

                # Render SVG to pixmap with proper bounds
                svg_renderer.render(painter, QRectF(0, 0, size, size))
                painter.end()

                # Scale to final size
                final_pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, 
                                           Qt.TransformationMode.SmoothTransformation)
                
                if not final_pixmap.isNull():
                    self.icon_label.setPixmap(final_pixmap)
                    # Set label background to transparent to avoid black box
                    self.icon_label.setStyleSheet("""
                        QLabel {
                            background-color: transparent;
                            border: none;
                        }
                    """)
                    return True
                    
            return False
            
        except Exception as e:
            return False
    
    
    def _try_load_svg_properly(self, icon_path):
        """Load SVG with proper display handling"""
        try:
            if not os.path.exists(icon_path):
                return False
                
            # Simple, direct SVG loading
            svg_renderer = QSvgRenderer(icon_path)
            if not svg_renderer.isValid():
                return False
                
            # Create pixmap
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            svg_renderer.render(painter)
            painter.end()
            
            # Scale to final size
            final_pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, 
                                       Qt.TransformationMode.SmoothTransformation)
            
            if not final_pixmap.isNull():
                # Clear any text content first
                self.icon_label.setText("")
                
                # Set the pixmap
                self.icon_label.setPixmap(final_pixmap)
                
                # Override any background styling that might cause black box
                self.icon_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        border: none;
                        padding: 0px;
                        margin: 0px;
                    }
                """)
                
                return True
                
            return False
            
        except Exception as e:
            return False
    
    def _set_fallback_icon(self):
        """Set fallback emoji icon when SVG loading fails"""
        emoji_map = {
            "pacman": "📦",
            "aur": "🧡", 
            "flatpak": "📱",
            "npm": "💚",
            "node": "💚",
        }
        fallback_emoji = emoji_map.get(self.source_name.lower(), "📦")
        self.icon_label.setText(fallback_emoji)
        self.icon_label.setStyleSheet("font-size: 16px; color: white;")
    
    def _try_svg_fallback(self, icon_path):
        """Try to load SVG as a fallback if text icons don't work"""
        try:
            if not os.path.exists(icon_path):
                return
                
            # Create a simple colored rectangle as a test
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            
            # Set color based on source type
            color_map = {
                "pacman": QColor("#0073e1"),
                "aur": QColor("#ff9955"),
                "flatpak": QColor("#4A90E2"),
                "npm": QColor("#68A063")
            }
            
            color = color_map.get(self.source_name.lower(), QColor("#ffffff"))
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Draw a simple shape based on source
            if self.source_name.lower() == "pacman":
                painter.drawEllipse(2, 2, 20, 20)
                painter.setBrush(QColor("#000000"))
                painter.drawPie(2, 2, 20, 20, 0, 90 * 16)  # Pac-man mouth
            elif self.source_name.lower() == "aur":
                # Draw triangle
                from PyQt6.QtGui import QPolygon
                from PyQt6.QtCore import QPoint
                triangle = QPolygon([QPoint(12, 2), QPoint(22, 20), QPoint(2, 20)])
                painter.drawPolygon(triangle)
            elif self.source_name.lower() == "npm":
                painter.drawRoundedRect(2, 2, 20, 20, 4, 4)
            else:
                painter.drawRoundedRect(2, 2, 20, 20, 2, 2)
            
            painter.end()
            
            # Only use this if it's not null and we want to override text
            # For now, keep the text icons as primary
            # self.icon_label.setPixmap(pixmap)
            
        except Exception as e:
            print(f"SVG fallback failed for {self.source_name}: {e}")
            pass

    def on_state_changed(self, state):
        """Handle checkbox state changes"""
        self.checked = state == Qt.CheckState.Checked
        self.update_visual_state()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                pos = event.position().toPoint()
            except AttributeError:
                pos = event.pos()
            # Toggle only when clicking outside the checkbox to avoid double toggles
            if not self.checkbox.geometry().contains(pos):
                self.checkbox.toggle()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Avoid double toggle when the checkbox itself has focus
            if not self.checkbox.hasFocus():
                self.checkbox.toggle()
                return
        super().keyPressEvent(event)

    def get_accent_color(self, name):
        n = name.lower()
        mapping = {
            "pacman": "#4FC3F7",
            "aur": "#FF8A65",
            "flatpak": "#26A69A",
            "npm": "#E53935",
        }
        return mapping.get(n, "#00BFAE")

    def apply_accent_styles(self):
        r, g, b = self.accent_color.red(), self.accent_color.green(), self.accent_color.blue()
        self.checkbox.setStyleSheet(
            f"""
            QCheckBox#sourceCheckbox {{
                color: #F0F0F0;
                font-size: 13px;
                font-weight: 600;
                spacing: 8px;
            }}
            QCheckBox#sourceCheckbox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid rgba({r}, {g}, {b}, 0.4);
                background-color: rgba(42, 45, 51, 0.8);
            }}
            QCheckBox#sourceCheckbox::indicator:checked {{
                background-color: {self.accent_hex};
                border: 2px solid {self.accent_hex};
            }}
            QCheckBox#sourceCheckbox::indicator:hover {{
                border-color: rgba({r}, {g}, {b}, 0.8);
            }}
            """
        )

    def update_visual_state(self):
        """Update visual appearance based on checked state"""
        if self.checked:
            r, g, b = self.accent_color.red(), self.accent_color.green(), self.accent_color.blue()
            self.icon_container.setStyleSheet(
                f"""
                QWidget#sourceIconContainer {{
                    background-color: rgba({r}, {g}, {b}, 0.14);
                    border: 1px solid rgba({r}, {g}, {b}, 0.4);
                    border-radius: 12px;
                }}
                """
            )
        else:
            self.icon_container.setStyleSheet("""
                QWidget#sourceIconContainer {
                    background-color: rgba(42, 45, 51, 0.3);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                }
            """)

    def get_stylesheet(self):
        """Get stylesheet for this component"""
        return """
            SourceItem {
                background-color: transparent;
                border-radius: 12px;
                margin: 2px 0px;
            }

            SourceItem:hover {
                background-color: rgba(0, 191, 174, 0.05);
                border-radius: 12px;
            }

            QCheckBox#sourceCheckbox {
                color: #F0F0F0;
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }

            QCheckBox#sourceCheckbox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid rgba(0, 191, 174, 0.4);
                background-color: rgba(42, 45, 51, 0.8);
            }

            QCheckBox#sourceCheckbox::indicator:checked {
                background-color: #00BFAE;
                border: 2px solid #00BFAE;
            }

            QCheckBox#sourceCheckbox::indicator:unchecked {
                background-color: rgba(42, 45, 51, 0.8);
            }

            QCheckBox#sourceCheckbox::indicator:hover {
                border-color: rgba(0, 191, 174, 0.8);
            }

            QWidget#sourceIconContainer {
                background-color: rgba(0, 191, 174, 0.1);
                border: 1px solid rgba(0, 191, 174, 0.3);
                border-radius: 12px;
            }
        """

    def is_checked(self):
        """Return whether this source is checked"""
        return self.checked

    def set_checked(self, checked):
        """Set the checked state"""
        self.checked = checked
        self.checkbox.setChecked(checked)
        self.update_visual_state()
