"""Git repository management component for NeoArch.

Provides UI and backend for cloning, building, updating, and cleaning
Git repositories. Supports Rust (Cargo), autotools, and Makefile-based
projects.
"""

import os
import subprocess
from threading import Thread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit, QMessageBox,
)
from PyQt6.QtCore import Qt, QObject, QTimer

from neoarch.resources.paths import ICONS_DIR
from neoarch.frontend.components.feature_card import FeatureCard

__all__ = ["GitManager"]


class GitManager(QObject):
    """Git repository management component for NeoArch."""

    def __init__(self, log_signal, show_message_signal, sources_layout, parent=None):
        super().__init__()
        self.log_signal = log_signal
        self.show_message = show_message_signal
        self.sources_layout = sources_layout
        self.parent = parent
        self.git_section = None
        self.recent_repos_label = None
        self.recent_repos_list = None
        self.create_git_section()

    def create_git_section(self):
        """Create and add the Git section UI to the sources layout."""
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
        self.git_section.setObjectName("gitSectionWrapper")
        wrapper_layout = QVBoxLayout(self.git_section)
        wrapper_layout.setContentsMargins(0, 6, 0, 0)
        wrapper_layout.setSpacing(4)

        card = FeatureCard()
        git_icon = os.path.join(str(ICONS_DIR), "discover", "git.svg")
        card.build_header(git_icon, "Git Repositories")
        card.build_primary_action("Install from Git", self.install_from_git)
        card.build_action_grid([
            ("Clone", "clone", lambda: self.install_from_git()),
            ("Open", "open", self.open_git_repos_dir),
            ("Update", "update", self.update_all_git_repos),
            ("Clean", "clean", self.clean_git_repos),
        ])
        wrapper_layout.addWidget(card)

        self.recent_repos_label = QLabel("Recent")
        self.recent_repos_label.setObjectName("gitRecentLabel")
        self.recent_repos_label.setStyleSheet("""
            QLabel#gitRecentLabel {
                color: #5C5E66;
                font-size: 9px;
                font-weight: 500;
                padding: 2px 14px 0 14px;
                background: transparent;
                border: none;
            }
        """)
        wrapper_layout.addWidget(self.recent_repos_label)

        self.recent_repos_list = QListWidget()
        self.recent_repos_list.setObjectName("gitRecentList")
        self.recent_repos_list.itemDoubleClicked.connect(self.open_repo_directory)
        self.recent_repos_list.setVisible(False)
        self.recent_repos_list.setStyleSheet("""
            QListWidget#gitRecentList {
                background-color: transparent;
                border: none;
                color: #8B8D97;
                font-size: 10px;
                max-height: 72px;
                padding: 0 14px 4px 14px;
            }
            QListWidget#gitRecentList::item {
                padding: 3px 6px;
                border-radius: 4px;
            }
            QListWidget#gitRecentList::item:hover {
                background-color: rgba(255, 255, 255, 0.04);
                color: #EDEDEF;
            }
            QListWidget#gitRecentList::item:selected {
                background-color: rgba(0, 191, 174, 0.12);
                color: #00BFAE;
            }
        """)
        wrapper_layout.addWidget(self.recent_repos_list)

        try:
            insert_at = 2 if self.sources_layout.count() >= 2 else self.sources_layout.count()
            self.sources_layout.insertWidget(insert_at, self.git_section)
        except Exception:
            self.sources_layout.addWidget(self.git_section)

        self.load_recent_git_repos()

    def install_from_git(self):
        """Show dialog to input a Git repository URL for cloning and building."""
        dialog = QDialog()
        dialog.setWindowTitle("Install from Git")
        dialog.setModal(True)
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet("""
            QDialog {
                background-color: rgba(18, 19, 22, 0.98);
                color: #EDEDEF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Clone & Install from Git")
        title.setStyleSheet("""
            font-size: 15px;
            font-weight: 600;
            color: #EDEDEF;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title)

        desc = QLabel("Enter a Git repository URL to clone, build, and install the application:")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8B8D97; font-size: 12px; background: transparent; border: none;")
        layout.addWidget(desc)

        url_input = QLineEdit()
        url_input.setPlaceholderText("https://github.com/user/repo.git")
        url_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(28, 30, 36, 0.9);
                color: #EDEDEF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 13px;
                selection-background-color: rgba(0, 191, 174, 0.3);
            }
            QLineEdit:focus {
                border-color: rgba(0, 191, 174, 0.5);
                background-color: rgba(28, 30, 36, 0.95);
            }
        """)
        layout.addWidget(url_input)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8B8D97;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 0 20px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.04);
                color: #EDEDEF;
            }
        """)
        buttons_layout.addWidget(cancel_btn)

        install_btn = QPushButton("Clone & Install")
        install_btn.setDefault(True)
        install_btn.setFixedHeight(34)
        install_btn.clicked.connect(lambda: self.proceed_git_install(url_input.text().strip(), dialog))
        install_btn.setStyleSheet("""
            QPushButton {
                background-color: #00BFAE;
                color: #0C0C0E;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #00D4C1;
            }
            QPushButton:pressed {
                background-color: #009688;
            }
        """)
        buttons_layout.addWidget(install_btn)
        layout.addLayout(buttons_layout)
        dialog.exec()

    def proceed_git_install(self, git_url, dialog):
        """Clone a Git repository and attempt to build/install it."""
        if not git_url:
            QMessageBox.warning(None, "Invalid URL", "Please enter a valid Git repository URL.")
            return
        if not (git_url.startswith("http://") or git_url.startswith("https://") or git_url.startswith("git@")):
            QMessageBox.warning(None, "Invalid URL", "Please enter a valid Git repository URL (starting with http://, https://, or git@).")
            return
        dialog.accept()
        repo_name = git_url.split('/')[-1].replace('.git', '')
        self.log_signal.emit(f"Starting installation from Git repository: {git_url}")

        def install_from_git_thread():
            try:
                home_dir = os.path.expanduser("~")
                git_repos_dir = os.path.join(home_dir, "git-repos")
                os.makedirs(git_repos_dir, exist_ok=True)
                clone_path = os.path.join(git_repos_dir, repo_name)

                if os.path.exists(clone_path):
                    self.log_signal.emit(f"Directory {clone_path} already exists. Pulling latest changes...")
                    pull_result = subprocess.run(["git", "-C", clone_path, "pull"], capture_output=True, text=True, timeout=60)
                    if pull_result.returncode != 0:
                        self.log_signal.emit(f"Failed to pull latest changes: {pull_result.stderr}")
                        self.show_message.emit("Git Update Failed", f"Failed to update repository: {pull_result.stderr}")
                        return
                    self.log_signal.emit("Repository updated successfully")
                else:
                    self.log_signal.emit("Cloning repository...")
                    clone_result = subprocess.run(["git", "clone", git_url, clone_path], capture_output=True, text=True, timeout=300)
                    if clone_result.returncode != 0:
                        self.log_signal.emit(f"Failed to clone repository: {clone_result.stderr}")
                        self.show_message.emit("Git Installation Failed", f"Failed to clone repository: {clone_result.stderr}")
                        return
                    self.log_signal.emit("Repository cloned successfully")

                os.chdir(clone_path)

                if os.path.exists(os.path.join(clone_path, "Cargo.toml")):
                    self.log_signal.emit("Detected Rust project, installing with cargo...")
                    install_result = subprocess.run(["cargo", "install", "--path", clone_path], capture_output=True, text=True, timeout=600)
                    if install_result.returncode == 0:
                        self.log_signal.emit("Rust package installed successfully")
                        self.show_message.emit("Installation Complete", f"Successfully installed {repo_name} from Git")
                    else:
                        self.log_signal.emit(f"Failed to install Rust package: {install_result.stderr}")
                        self.show_message.emit("Installation Failed", f"Failed to install Rust package: {install_result.stderr}")
                elif os.path.exists(os.path.join(clone_path, "configure.ac")) or os.path.exists(os.path.join(clone_path, "configure.in")):
                    self.log_signal.emit("Detected autotools project, building...")
                    configure_cmds = []
                    if os.path.exists(os.path.join(clone_path, "autogen.sh")):
                        configure_cmds.append(["./autogen.sh"])
                    if os.path.exists(os.path.join(clone_path, "configure")):
                        configure_cmds.append(["./configure", "--prefix=/usr/local"])
                    if os.path.exists(os.path.join(clone_path, "Makefile")):
                        configure_cmds.append(["make", "-j$(nproc)"])
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
                elif os.path.exists(os.path.join(clone_path, "Makefile")):
                    self.log_signal.emit("Detected Makefile, building and installing...")
                    build_cmds = [["make", "-j$(nproc)"], ["sudo", "make", "install"]]
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
                    self.log_signal.emit(f"Repository cloned to: {clone_path}")
                    self.log_signal.emit("No automatic installation method detected.")
                    self.show_message.emit("Git Clone Complete", f"Repository cloned to {clone_path}. Check console for build instructions.")

                self.load_recent_git_repos()
            except Exception as e:
                self.log_signal.emit(f"Error during Git installation: {str(e)}")
                self.show_message.emit("Installation Failed", f"Error during installation: {str(e)}")

        Thread(target=install_from_git_thread, daemon=True).start()

    def open_git_repos_dir(self):
        """Open the git-repos directory in the file manager."""
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
        """Update all Git repositories in ~/git-repos."""
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
                    result = subprocess.run(["git", "-C", repo_path, "pull"], capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        updated += 1
                        self.log_signal.emit(f"\u2713 Updated {repo}")
                    else:
                        failed += 1
                        self.log_signal.emit(f"\u2717 Failed to update {repo}: {result.stderr.strip()}")
                except Exception as e:
                    failed += 1
                    self.log_signal.emit(f"\u2717 Error updating {repo}: {e}")
            self.log_signal.emit(f"Update complete: {updated} updated, {failed} failed")
            if updated > 0 or failed > 0:
                QTimer.singleShot(0, lambda: self.show_message.emit("Git Update Complete", f"Updated {updated} repos, {failed} failed"))
        Thread(target=update_thread, daemon=True).start()

    def clean_git_repos(self):
        """Clean build artifacts from Git repositories."""
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
                    result = subprocess.run(["git", "-C", repo_path, "clean", "-fdx"], capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        cleaned += 1
                        self.log_signal.emit(f"\u2713 Cleaned {repo}")
                    else:
                        failed += 1
                        self.log_signal.emit(f"\u2717 Failed to clean {repo}: {result.stderr.strip()}")
                except Exception as e:
                    failed += 1
                    self.log_signal.emit(f"\u2717 Error cleaning {repo}: {e}")
            self.log_signal.emit(f"Clean complete: {cleaned} cleaned, {failed} failed")
            if cleaned > 0 or failed > 0:
                QTimer.singleShot(0, lambda: self.show_message.emit("Git Clean Complete", f"Cleaned {cleaned} repos, {failed} failed"))
        Thread(target=clean_thread, daemon=True).start()

    def load_recent_git_repos(self):
        """Load and display recently cloned Git repositories."""
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
                    mtime = os.path.getmtime(repo_path)
                    repos.append((item, mtime, repo_path))
            repos.sort(key=lambda x: x[1], reverse=True)
            recent_repos = repos[:5]
            if recent_repos and self.recent_repos_list:
                self.recent_repos_list.clear()
                for repo_name, _, repo_path in recent_repos:
                    item = QListWidgetItem(f"\U0001f4c1 {repo_name}")
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

    def open_repo_directory(self, item):
        """Open the selected repository directory in the file manager."""
        repo_path = item.data(Qt.ItemDataRole.UserRole)
        if repo_path and os.path.exists(repo_path):
            try:
                subprocess.run(["xdg-open", repo_path], check=True)
                self.log_signal.emit(f"Opened repository: {os.path.basename(repo_path)}")
            except Exception as e:
                self.log_signal.emit(f"Failed to open repository: {e}")
