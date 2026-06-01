# git_manager.py - Git repository management component for Aurora

import os
import subprocess
from threading import Thread
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QListWidget, QListWidgetItem, QDialog, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor
from PyQt6.QtSvg import QSvgRenderer


class GitManager(QObject):
    """Git repository management component for Aurora"""

    def __init__(self, log_signal, show_message_signal, sources_layout, parent=None):
        super().__init__()
        self.log_signal = log_signal
        self.show_message = show_message_signal
        self.sources_layout = sources_layout
        self.parent = parent  # Reference to main window

        # UI elements that will be created
        self.git_section = None  # Reference to the git section widget
        self.recent_repos_label = None
        self.recent_repos_list = None

        # Initialize the Git section UI
        self.create_git_section()

    def create_git_section(self):
        """Create and add the Git section to the sources layout"""
        # Remove previous section if it exists (avoid duplicates after navigation)
        try:
            if self.git_section is not None:
                try:
                    self.git_section.setParent(None)
                except Exception:
                    pass
                self.git_section.deleteLater()
        except Exception:
            pass

        self.git_section = QWidget()
        git_layout = QVBoxLayout(self.git_section)
        git_layout.setContentsMargins(0, 8, 0, 0)  # Add top margin for spacing
        git_layout.setSpacing(10)  # Increase spacing between elements

        # Git section label
        git_label = QLabel("Git Repositories")
        git_label.setObjectName("sectionLabel")
        git_label.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
        git_layout.addWidget(git_label)

        # Main Install from Git button (separate at top)
        install_git_container = QWidget()
        install_git_layout = QHBoxLayout(install_git_container)
        install_git_layout.setContentsMargins(0, 0, 0, 0)
        install_git_layout.setSpacing(8)

        # Git icon
        git_icon_label = QLabel()
        git_icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "discover", "git.svg")
        try:
            svg_renderer = QSvgRenderer(git_icon_path)
            if svg_renderer.isValid():
                pixmap = QPixmap(20, 20)
                if pixmap.isNull():
                    git_icon_label.setText("📦")
                    git_icon_label.setStyleSheet("font-size: 14px; color: white;")
                else:
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    from PyQt6.QtCore import QRectF
                    svg_renderer.render(painter, QRectF(pixmap.rect()))
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                    painter.fillRect(pixmap.rect(), QColor("white"))
                    painter.end()
                    git_icon_label.setPixmap(pixmap)
            else:
                git_icon_label.setText("📦")
        except OSError:
            # Handle file loading or parsing errors
            git_icon_label.setText("📦")

        install_git_layout.addWidget(git_icon_label)

        # Install button
        install_git_btn = QPushButton("Install from Git")
        install_git_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(0, 191, 174, 0.25);
            }
        """)
        install_git_btn.clicked.connect(self.install_from_git)
        install_git_layout.addWidget(install_git_btn)

        git_layout.addWidget(install_git_container)

        # Secondary buttons widget (at bottom)
        secondary_buttons_widget = QWidget()
        secondary_layout = QHBoxLayout(secondary_buttons_widget)
        secondary_layout.setContentsMargins(0, 0, 0, 0)
        secondary_layout.setSpacing(4)

        # Open Repos button
        open_repos_btn = QPushButton("📁 Open")
        open_repos_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15);
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.35);
                color: #00BFAE;
            }
        """)
        open_repos_btn.clicked.connect(self.open_git_repos_dir)
        secondary_layout.addWidget(open_repos_btn)

        # Update All button
        update_repos_btn = QPushButton("🔄 Update")
        update_repos_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15);
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.35);
                color: #00BFAE;
            }
        """)
        update_repos_btn.clicked.connect(self.update_all_git_repos)
        secondary_layout.addWidget(update_repos_btn)

        # Clean button
        clean_repos_btn = QPushButton("🗑️ Clean")
        clean_repos_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15);
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 191, 174, 0.15);
                border-color: rgba(0, 191, 174, 0.35);
                color: #FF6B6B;
            }
        """)
        clean_repos_btn.clicked.connect(self.clean_git_repos)
        secondary_layout.addWidget(clean_repos_btn)

        git_layout.addWidget(secondary_buttons_widget)

        # Recent repos list (compact)
        self.recent_repos_label = QLabel("Recent:")
        self.recent_repos_label.setStyleSheet("color: #C9C9C9; font-size: 10px; margin-top: 4px;")
        git_layout.addWidget(self.recent_repos_label)

        self.recent_repos_list = QListWidget()
        self.recent_repos_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(42, 45, 51, 0.4);
                border: 1px solid rgba(0, 191, 174, 0.15);
                color: #F0F0F0;
                font-size: 10px;
                max-height: 85px;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 191, 174, 0.15);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 191, 174, 0.25);
            }
        """)
        self.recent_repos_list.itemDoubleClicked.connect(self.open_repo_directory)
        self.recent_repos_list.setVisible(False)  # Initially hidden
        git_layout.addWidget(self.recent_repos_list)

        try:
            insert_at = 2 if self.sources_layout.count() >= 2 else self.sources_layout.count()
            self.sources_layout.insertWidget(insert_at, self.git_section)
        except Exception:
            self.sources_layout.addWidget(self.git_section)

        # Load recent repos on startup
        self.load_recent_git_repos()

    def install_from_git(self):
        """Create a dialog to ask for Git URL"""
        dialog = QDialog()
        dialog.setWindowTitle("Install from Git Repository")
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.2);
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Install Application from Git Repository")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00BFAE;")
        layout.addWidget(title)

        # Description
        desc = QLabel("Enter the Git repository URL to clone and install the application:")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # URL input
        url_input = QLineEdit()
        url_input.setPlaceholderText("https://github.com/user/repo.git")
        url_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(42, 45, 51, 0.8);
                color: #F0F0F0;
                border: 2px solid rgba(0, 191, 174, 0.2);
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #00BFAE;
            }
        """)
        layout.addWidget(url_input)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(42, 45, 51, 0.6);
                color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.2);
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: rgba(42, 45, 51, 0.8);
            }
        """)
        buttons_layout.addWidget(cancel_btn)

        install_btn = QPushButton("Clone & Install")
        install_btn.setDefault(True)
        install_btn.clicked.connect(lambda: self.proceed_git_install(url_input.text().strip(), dialog))
        install_btn.setStyleSheet("""
            QPushButton {
                background-color: #00BFAE;
                color: #1E1E1E;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #00C4B0;
            }
        """)
        buttons_layout.addWidget(install_btn)

        layout.addLayout(buttons_layout)

        dialog.exec()

    def proceed_git_install(self, git_url, dialog):
        """Handle the actual Git cloning and installation process"""
        if not git_url:
            QMessageBox.warning(None, "Invalid URL", "Please enter a valid Git repository URL.")
            return

        # Validate URL format
        if not (git_url.startswith("http://") or git_url.startswith("https://") or git_url.startswith("git@")):
            QMessageBox.warning(None, "Invalid URL", "Please enter a valid Git repository URL (starting with http://, https://, or git@).")
            return

        dialog.accept()

        # Extract repo name from URL
        repo_name = git_url.split('/')[-1].replace('.git', '')

        self.log_signal.emit(f"Starting installation from Git repository: {git_url}")

        def install_from_git_thread():
            try:
                # Clone to user's home directory instead of temp
                home_dir = os.path.expanduser("~")
                git_repos_dir = os.path.join(home_dir, "git-repos")
                os.makedirs(git_repos_dir, exist_ok=True)
                clone_path = os.path.join(git_repos_dir, repo_name)

                # Check if directory already exists
                if os.path.exists(clone_path):
                    self.log_signal.emit(f"Directory {clone_path} already exists. Pulling latest changes...")
                    pull_cmd = ["git", "-C", clone_path, "pull"]
                    pull_result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=60)
                    if pull_result.returncode != 0:
                        self.log_signal.emit(f"Failed to pull latest changes: {pull_result.stderr}")
                        self.show_message.emit("Git Update Failed", f"Failed to update repository: {pull_result.stderr}")
                        return
                    self.log_signal.emit("Repository updated successfully")
                else:
                    # Clone the repository
                    self.log_signal.emit("Cloning repository...")
                    clone_cmd = ["git", "clone", git_url, clone_path]
                    clone_result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=300)

                    if clone_result.returncode != 0:
                        self.log_signal.emit(f"Failed to clone repository: {clone_result.stderr}")
                        self.show_message.emit("Git Installation Failed", f"Failed to clone repository: {clone_result.stderr}")
                        return

                    self.log_signal.emit("Repository cloned successfully")

                # Change to clone directory
                os.chdir(clone_path)

                # Check for Rust project
                if os.path.exists(os.path.join(clone_path, "Cargo.toml")):
                    self.log_signal.emit("Detected Rust project, installing with cargo...")
                    install_cmd = ["cargo", "install", "--path", clone_path]
                    install_result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=600)

                    if install_result.returncode == 0:
                        self.log_signal.emit("Rust package installed successfully")
                        self.show_message.emit("Installation Complete", f"Successfully installed {repo_name} from Git")
                    else:
                        self.log_signal.emit(f"Failed to install Rust package: {install_result.stderr}")
                        self.show_message.emit("Installation Failed", f"Failed to install Rust package: {install_result.stderr}")

                # Check for other common build systems (like autotools)
                elif os.path.exists(os.path.join(clone_path, "configure.ac")) or os.path.exists(os.path.join(clone_path, "configure.in")):
                    self.log_signal.emit("Detected autotools project, building...")
                    configure_cmds = []

                    # Check for autogen.sh
                    if os.path.exists(os.path.join(clone_path, "autogen.sh")):
                        self.log_signal.emit("Running autogen.sh...")
                        configure_cmds.append(["./autogen.sh"])

                    # Run configure
                    if os.path.exists(os.path.join(clone_path, "configure")):
                        self.log_signal.emit("Running configure...")
                        configure_cmds.append(["./configure", "--prefix=/usr/local"])

                    # Run make
                    if os.path.exists(os.path.join(clone_path, "Makefile")):
                        self.log_signal.emit("Running make...")
                        configure_cmds.append(["make", "-j$(nproc)"])
                        self.log_signal.emit("Running make install...")
                        configure_cmds.append(["sudo", "make", "install"])

                    success = True
                    for cmd in configure_cmds:
                        result = subprocess.run(cmd, cwd=clone_path, capture_output=True, text=True, timeout=600)
                        if result.returncode != 0:
                            self.log_signal.emit(f"Command failed: {' '.join(cmd)}")
                            self.log_signal.emit(f"Error: {result.stderr}")
                            success = False
                            break

                    if success:
                        self.log_signal.emit("Autotools build completed successfully")
                        self.show_message.emit("Installation Complete", f"Successfully built and installed {repo_name}")

                    else:
                        self.show_message.emit("Build Failed", "Check console output for build errors")

                # Check for Makefile (generic)
                elif os.path.exists(os.path.join(clone_path, "Makefile")):
                    self.log_signal.emit("Detected Makefile, building and installing...")

                    # Try common build patterns
                    build_cmds = [
                        ["make", "-j$(nproc)"],  # Build
                        ["sudo", "make", "install"]  # Install
                    ]

                    success = True
                    for cmd in build_cmds:
                        self.log_signal.emit(f"Running: {' '.join(cmd)}")
                        result = subprocess.run(cmd, cwd=clone_path, capture_output=True, text=True, timeout=600)
                        if result.returncode != 0:
                            self.log_signal.emit(f"Command failed: {' '.join(cmd)}")
                            self.log_signal.emit(f"Error: {result.stderr}")
                            success = False
                            break

                    if success:
                        self.log_signal.emit("Build and installation completed successfully")
                        self.show_message.emit("Installation Complete", f"Successfully built and installed {repo_name}")
                    else:
                        self.show_message.emit("Build Failed", "Check console output for build errors")

                else:
                    # No automatic installation detected
                    self.log_signal.emit(f"Repository cloned to: {clone_path}")
                    self.log_signal.emit("No automatic installation method detected.")
                    self.log_signal.emit("To manually build and install:")
                    self.log_signal.emit(f"  cd {clone_path}")
                    self.log_signal.emit("  ls -la  # Check for build files")
                    self.log_signal.emit("  # Common build commands:")
                    self.log_signal.emit("  # ./configure && make && sudo make install")
                    self.log_signal.emit("  # OR")
                    self.log_signal.emit("  # make && sudo make install")
                    self.log_signal.emit("  # OR")
                    self.log_signal.emit("  # cargo install --path .")

                    self.show_message.emit("Git Clone Complete", f"Repository cloned to {clone_path}. Check console for build instructions.")

                # Refresh recent repos list after successful clone
                self.load_recent_git_repos()

            except Exception as e:
                self.log_signal.emit(f"Error during Git installation: {str(e)}")
                self.show_message.emit("Installation Failed", f"Error during installation: {str(e)}")

        Thread(target=install_from_git_thread, daemon=True).start()

    def open_git_repos_dir(self):
        """Open the git-repos directory in file manager"""
        git_repos_dir = os.path.expanduser("~/git-repos")
        try:
            if os.path.exists(git_repos_dir):
                subprocess.run(["xdg-open", git_repos_dir], check=True)
                self.log_signal.emit("Opened git-repos directory")
            else:
                self.log_signal.emit("git-repos directory doesn't exist yet")
                QMessageBox.information(None, "No Repos Yet", "You haven't cloned any Git repositories yet.\nUse 'Install from Git' to get started!")
        except Exception as e:
            self.log_signal.emit(f"Failed to open directory: {e}")

    def update_all_git_repos(self):
        """Update all Git repositories in ~/git-repos"""
        git_repos_dir = os.path.expanduser("~/git-repos")
        if not os.path.exists(git_repos_dir):
            self.log_signal.emit("No git-repos directory found")
            return

        repos = [d for d in os.listdir(git_repos_dir)
                if os.path.isdir(os.path.join(git_repos_dir, d)) and
                os.path.exists(os.path.join(git_repos_dir, d, ".git"))]

        if not repos:
            self.log_signal.emit("No Git repositories found")
            return

        self.log_signal.emit(f"Updating {len(repos)} Git repositories...")

        def update_thread():
            updated = 0
            failed = 0
            for repo in repos:
                repo_path = os.path.join(git_repos_dir, repo)
                try:
                    self.log_signal.emit(f"Updating {repo}...")
                    result = subprocess.run(["git", "-C", repo_path, "pull"],
                                          capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        updated += 1
                        self.log_signal.emit(f"✓ Updated {repo}")
                    else:
                        failed += 1
                        self.log_signal.emit(f"✗ Failed to update {repo}: {result.stderr.strip()}")
                except Exception as e:
                    failed += 1
                    self.log_signal.emit(f"✗ Error updating {repo}: {e}")

            self.log_signal.emit(f"Update complete: {updated} updated, {failed} failed")
            # Emit signal from main thread instead of worker thread
            if updated > 0 or failed > 0:
                # Use QTimer to emit from main thread
                QTimer.singleShot(0, lambda: self.show_message.emit("Git Update Complete", f"Updated {updated} repos, {failed} failed"))

        Thread(target=update_thread, daemon=True).start()

    def clean_git_repos(self):
        """Clean up Git repositories (remove build artifacts, etc.)"""
        git_repos_dir = os.path.expanduser("~/git-repos")
        if not os.path.exists(git_repos_dir):
            self.log_signal.emit("No git-repos directory found")
            return

        repos = [d for d in os.listdir(git_repos_dir)
                if os.path.isdir(os.path.join(git_repos_dir, d)) and
                os.path.exists(os.path.join(git_repos_dir, d, ".git"))]

        if not repos:
            self.log_signal.emit("No Git repositories found")
            return

        # Ask for confirmation
        reply = QMessageBox.question(
            None, "Clean Git Repositories",
            f"This will clean build artifacts from {len(repos)} repositories.\n\n"
            "This will run 'git clean -fdx' and remove untracked and ignored files.\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.log_signal.emit(f"Cleaning {len(repos)} Git repositories...")

        def clean_thread():
            cleaned = 0
            failed = 0
            for repo in repos:
                repo_path = os.path.join(git_repos_dir, repo)
                try:
                    self.log_signal.emit(f"Cleaning {repo}...")
                    result = subprocess.run(["git", "-C", repo_path, "clean", "-fdx"],
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        cleaned += 1
                        self.log_signal.emit(f"✓ Cleaned {repo}")
                    else:
                        failed += 1
                        self.log_signal.emit(f"✗ Failed to clean {repo}: {result.stderr.strip()}")
                except Exception as e:
                    failed += 1
                    self.log_signal.emit(f"✗ Error cleaning {repo}: {e}")

            self.log_signal.emit(f"Clean complete: {cleaned} cleaned, {failed} failed")
            if cleaned > 0 or failed > 0:
                # Use QTimer to emit from main thread
                QTimer.singleShot(0, lambda: self.show_message.emit("Git Clean Complete", f"Cleaned {cleaned} repos, {failed} failed"))

        Thread(target=clean_thread, daemon=True).start()

    def load_recent_git_repos(self):
        """Load and display recently cloned Git repositories"""
        git_repos_dir = os.path.expanduser("~/git-repos")
        if not os.path.exists(git_repos_dir):
            if self.recent_repos_label:
                self.recent_repos_label.setVisible(False)
            if self.recent_repos_list:
                self.recent_repos_list.setVisible(False)
            return

        repos = []
        try:
            for item in os.listdir(git_repos_dir):
                repo_path = os.path.join(git_repos_dir, item)
                if os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, ".git")):
                    # Get last modified time
                    mtime = os.path.getmtime(repo_path)
                    repos.append((item, mtime, repo_path))

            # Sort by modification time (most recent first)
            repos.sort(key=lambda x: x[1], reverse=True)

            # Show only recent 5
            recent_repos = repos[:5]

            if recent_repos and self.recent_repos_list:
                self.recent_repos_list.clear()
                for repo_name, _, repo_path in recent_repos:
                    item = QListWidgetItem(f"📁 {repo_name}")
                    item.setToolTip(f"Double-click to open: {repo_path}")
                    item.setData(Qt.ItemDataRole.UserRole, repo_path)
                    self.recent_repos_list.addItem(item)

                if self.recent_repos_label:
                    self.recent_repos_label.setVisible(True)
                self.recent_repos_list.setVisible(True)
            else:
                if self.recent_repos_label:
                    self.recent_repos_label.setVisible(False)
                if self.recent_repos_list:
                    self.recent_repos_list.setVisible(False)

        except Exception as e:
            self.log_signal.emit(f"Error loading recent repos: {e}")
            if self.recent_repos_label:
                self.recent_repos_label.setVisible(False)
            if self.recent_repos_list:
                self.recent_repos_list.setVisible(False)

    def open_repo_directory(self, item):
        """Open the selected repository directory"""
        repo_path = item.data(Qt.ItemDataRole.UserRole)
        if repo_path and os.path.exists(repo_path):
            try:
                subprocess.run(["xdg-open", repo_path], check=True)
                self.log_signal.emit(f"Opened repository: {os.path.basename(repo_path)}")
            except Exception as e:
                self.log_signal.emit(f"Failed to open repository: {e}")
