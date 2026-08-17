"""Git repository management for NeoArch.

Provides backend logic for cloning, building, updating, and cleaning Git
repositories. Supports Rust (Cargo), CMake, Meson, Go, Make, npm, and
PKGBUILD-based projects.  The UI is provided by the GitTab full-page
component.
"""

import os
import time
import subprocess
from threading import Thread
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QDialog, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QObject, QTimer, QMetaObject, Qt

__all__ = ["GitManager"]


def _dir_size(path):
    """Return total size in bytes of *path* (non-recursive is fine for top-level)."""
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _dir_size(entry.path)
            except OSError:
                pass
    except OSError:
        pass
    return total


def _fmt_size(nbytes):
    """Human-readable file size."""
    if nbytes < 1024:
        return f"{nbytes} B"
    for unit in ("KB", "MB", "GB"):
        nbytes /= 1024
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}" if unit == "GB" else f"{nbytes:.0f} {unit}"
    return f"{nbytes:.1f} TB"


def _detect_build_system(path):
    """Return (build_system, language) tuple for a repository path."""
    if os.path.isfile(os.path.join(path, "PKGBUILD")):
        return ("PKGBUILD", "Shell")
    if os.path.isfile(os.path.join(path, "Cargo.toml")):
        return ("Cargo", "Rust")
    if os.path.isfile(os.path.join(path, "CMakeLists.txt")):
        return ("CMake", "C/C++")
    if os.path.isfile(os.path.join(path, "meson.build")):
        return ("Meson", "C/C++")
    if os.path.isfile(os.path.join(path, "go.mod")):
        return ("Go", "Go")
    if os.path.isfile(os.path.join(path, "package.json")):
        return ("npm", "JavaScript")
    if os.path.isfile(os.path.join(path, "Makefile")):
        return ("Make", "")
    if os.path.isfile(os.path.join(path, "configure.ac")) or os.path.isfile(os.path.join(path, "configure.in")):
        return ("Autotools", "C/C++")
    return ("", "")


class GitManager(QObject):
    """Git repository management component for NeoArch."""

    repos_changed = pyqtSignal()
    build_completed = pyqtSignal(str, bool, str)  # repo_name, success, message

    def __init__(self, log_signal, show_message_signal, parent=None):
        super().__init__(parent)
        self.log_signal = log_signal
        self.show_message = show_message_signal
        self.parent = parent
        self._build_history = []

    def _emit_repos_changed(self):
        """Thread-safe repos_changed emission via QueuedConnection."""
        QMetaObject.invokeMethod(
            self, "_do_repos_changed", Qt.ConnectionType.QueuedConnection)

    @pyqtSlot()
    def _do_repos_changed(self):
        self.repos_changed.emit()

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

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
        title.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #EDEDEF;"
            "background: transparent; border: none;")
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
            QPushButton:hover { background-color: #00D4C1; }
            QPushButton:pressed { background-color: #009688; }
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
            QMessageBox.warning(
                None, "Invalid URL",
                "Please enter a valid Git repository URL (starting with http://, https://, or git@).")
            return
        dialog.accept()
        repo_name = git_url.split('/')[-1].replace('.git', '')
        self.log_signal.emit(f"Starting installation from Git repository: {git_url}")

        def _task():
            ok = False
            msg = ""
            build_sys = ""
            try:
                home_dir = os.path.expanduser("~")
                git_repos_dir = os.path.join(home_dir, "git-repos")
                os.makedirs(git_repos_dir, exist_ok=True)
                clone_path = os.path.join(git_repos_dir, repo_name)

                if os.path.exists(clone_path):
                    self.log_signal.emit(f"Directory {clone_path} already exists. Pulling latest...")
                    r = subprocess.run(
                        ["git", "-C", clone_path, "pull"],
                        capture_output=True, text=True, timeout=60)
                    if r.returncode != 0:
                        self.log_signal.emit(f"Failed to pull: {r.stderr}")
                        self.show_message.emit("Git Update Failed", r.stderr)
                        msg = f"Failed to pull: {r.stderr}"
                    else:
                        msg = "Updated successfully"
                        ok = True
                else:
                    self.log_signal.emit("Cloning repository...")
                    r = subprocess.run(
                        ["git", "clone", git_url, clone_path],
                        capture_output=True, text=True, timeout=300)
                    if r.returncode != 0:
                        self.log_signal.emit(f"Failed to clone: {r.stderr}")
                        self.show_message.emit("Git Installation Failed", r.stderr)
                        msg = f"Failed to clone: {r.stderr}"
                    else:
                        build_sys, _ = _detect_build_system(clone_path)
                        if build_sys == "Cargo":
                            self.log_signal.emit("Detected Rust project, installing with cargo...")
                            r = subprocess.run(
                                ["cargo", "install", "--path", clone_path],
                                capture_output=True, text=True, timeout=600)
                            ok = r.returncode == 0
                            msg = "Rust package installed successfully" if ok else f"Failed: {r.stderr}"
                        elif build_sys == "Autotools":
                            self.log_signal.emit("Detected autotools project, building...")
                            cmds = []
                            if os.path.exists(os.path.join(clone_path, "autogen.sh")):
                                cmds.append(["./autogen.sh"])
                            if os.path.exists(os.path.join(clone_path, "configure")):
                                cmds.append(["./configure", "--prefix=/usr/local"])
                            cmds += [["make", "-j$(nproc)"], ["sudo", "make", "install"]]
                            ok = True
                            for cmd in cmds:
                                r = subprocess.run(cmd, cwd=clone_path, capture_output=True, text=True, timeout=600)
                                if r.returncode != 0:
                                    ok = False
                                    msg = f"Failed: {r.stderr}"
                                    break
                            else:
                                msg = "Build completed successfully"
                        elif build_sys == "Make":
                            self.log_signal.emit("Detected Makefile, building...")
                            ok = True
                            for cmd in [["make", "-j$(nproc)"], ["sudo", "make", "install"]]:
                                r = subprocess.run(cmd, cwd=clone_path, capture_output=True, text=True, timeout=600)
                                if r.returncode != 0:
                                    ok = False
                                    msg = f"Failed: {r.stderr}"
                                    break
                            else:
                                msg = "Build completed successfully"
                        else:
                            msg = f"Cloned to {clone_path}. No auto-build detected."
                            ok = True

                self.log_signal.emit(msg)
                if ok:
                    self.show_message.emit("Installation Complete", f"Successfully installed {repo_name}")
                else:
                    self.show_message.emit("Build Failed", msg)
            except Exception as e:
                self.log_signal.emit(f"Error during Git installation: {e}")
                self.show_message.emit("Installation Failed", str(e))
            entry = {
                "name": repo_name, "success": ok,
                "message": msg,
                "time": time.time(),
                "build_system": build_sys,
            }
            self._build_history.insert(0, entry)
            if len(self._build_history) > 50:
                self._build_history = self._build_history[:50]
            self._emit_repos_changed()

        Thread(target=_task, daemon=True).start()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_repos(self):
        """Return enriched repo info dicts for ~/git-repos (most recent first)."""
        git_repos_dir = os.path.expanduser("~/git-repos")
        repos = []
        if not os.path.isdir(git_repos_dir):
            return repos
        try:
            for item in os.listdir(git_repos_dir):
                repo_path = os.path.join(git_repos_dir, item)
                if not (os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, ".git"))):
                    continue
                info = {"name": item, "path": repo_path}
                try:
                    info["mtime"] = os.path.getmtime(repo_path)
                except Exception:
                    info["mtime"] = 0

                # Remote URL
                try:
                    r = subprocess.run(
                        ["git", "-C", repo_path, "remote", "get-url", "origin"],
                        capture_output=True, text=True, timeout=5)
                    info["url"] = r.stdout.strip() if r.returncode == 0 else ""
                except Exception:
                    info["url"] = ""

                # Branch
                try:
                    r = subprocess.run(
                        ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
                        capture_output=True, text=True, timeout=5)
                    info["branch"] = r.stdout.strip() if r.returncode == 0 else ""
                except Exception:
                    info["branch"] = ""

                # Status: modified files count
                try:
                    r = subprocess.run(
                        ["git", "-C", repo_path, "status", "--porcelain"],
                        capture_output=True, text=True, timeout=5)
                    modified = len([l for l in r.stdout.strip().split("\n") if l.strip()]) if r.returncode == 0 else 0
                    info["modified_count"] = modified
                except Exception:
                    info["modified_count"] = 0

                # Commits behind remote
                try:
                    r = subprocess.run(
                        ["git", "-C", repo_path, "rev-list", "--count",
                         f"HEAD..@{{u}}"],
                        capture_output=True, text=True, timeout=5)
                    info["behind"] = int(r.stdout.strip()) if r.returncode == 0 else 0
                except Exception:
                    info["behind"] = 0

                # Last commit time
                try:
                    r = subprocess.run(
                        ["git", "-C", repo_path, "log", "-1", "--format=%ct"],
                        capture_output=True, text=True, timeout=5)
                    info["last_commit"] = int(r.stdout.strip()) if r.returncode == 0 else 0
                except Exception:
                    info["last_commit"] = 0

                # Build system + language
                info["build_system"], info["language"] = _detect_build_system(repo_path)

                # PKGBUILD detection
                info["has_pkgbuild"] = os.path.isfile(os.path.join(repo_path, "PKGBUILD"))

                # Disk usage
                info["disk_usage"] = _dir_size(repo_path)

                repos.append(info)
        except Exception as e:
            self.log_signal.emit(f"Error listing repos: {e}")
        repos.sort(key=lambda r: r.get("mtime", 0), reverse=True)
        return repos

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def open_git_repos_dir(self):
        """Open the git-repos directory in the file manager."""
        git_repos_dir = os.path.expanduser("~/git-repos")
        try:
            if os.path.exists(git_repos_dir):
                subprocess.run(["xdg-open", git_repos_dir], check=True)
                self.log_signal.emit("Opened git-repos directory")
            else:
                QMessageBox.information(
                    None, "No Repos Yet",
                    "You haven't cloned any Git repositories yet.\n"
                    "Use '+ Clone Repository' to get started!")
        except Exception as e:
            self.log_signal.emit(f"Failed to open directory: {e}")

    def open_repo(self, repo_path):
        """Open a single repository directory in the file manager."""
        if os.path.exists(repo_path):
            try:
                subprocess.run(["xdg-open", repo_path], check=True)
            except Exception as e:
                self.log_signal.emit(f"Failed to open repository: {e}")

    def update_repo(self, repo_path):
        """Update (git pull) a single repository."""
        name = os.path.basename(repo_path.rstrip("/"))

        def _task():
            try:
                self.log_signal.emit(f"Updating {name}...")
                r = subprocess.run(
                    ["git", "-C", repo_path, "pull"],
                    capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    self.show_message.emit("Git Update Complete", f"Updated {name}")
                else:
                    self.show_message.emit("Git Update Failed", r.stderr.strip())
            except Exception as e:
                self.log_signal.emit(f"Error updating {name}: {e}")
            self._emit_repos_changed()

        Thread(target=_task, daemon=True).start()

    def remove_repo(self, repo_path):
        """Permanently delete a repository directory."""
        import shutil
        try:
            shutil.rmtree(repo_path)
            self.log_signal.emit(f"Removed repository: {os.path.basename(repo_path)}")
        except Exception as e:
            self.log_signal.emit(f"Failed to remove repository: {e}")
        self.repos_changed.emit()

    def update_all_git_repos(self):
        """Update all Git repositories in ~/git-repos."""
        git_repos_dir = os.path.expanduser("~/git-repos")
        if not os.path.exists(git_repos_dir):
            return
        repos = [d for d in os.listdir(git_repos_dir)
                 if os.path.isdir(os.path.join(git_repos_dir, d)) and
                 os.path.exists(os.path.join(git_repos_dir, d, ".git"))]
        if not repos:
            return

        def _task():
            updated = failed = 0
            for repo in repos:
                r = subprocess.run(
                    ["git", "-C", os.path.join(git_repos_dir, repo), "pull"],
                    capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    updated += 1
                else:
                    failed += 1
            QTimer.singleShot(0, lambda: self.show_message.emit(
                "Git Update Complete", f"Updated {updated} repos, {failed} failed"))
            self._emit_repos_changed()

        Thread(target=_task, daemon=True).start()

    def clean_git_repos(self):
        """Clean build artifacts from Git repositories."""
        git_repos_dir = os.path.expanduser("~/git-repos")
        if not os.path.exists(git_repos_dir):
            return
        repos = [d for d in os.listdir(git_repos_dir)
                 if os.path.isdir(os.path.join(git_repos_dir, d)) and
                 os.path.exists(os.path.join(git_repos_dir, d, ".git"))]
        if not repos:
            return
        reply = QMessageBox.question(
            None, "Clean Git Repositories",
            f"This will run 'git clean -fdx' on {len(repos)} repositories.\n"
            "Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        def _task():
            cleaned = failed = 0
            for repo in repos:
                r = subprocess.run(
                    ["git", "-C", os.path.join(git_repos_dir, repo), "clean", "-fdx"],
                    capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    cleaned += 1
                else:
                    failed += 1
            QTimer.singleShot(0, lambda: self.show_message.emit(
                "Git Clean Complete", f"Cleaned {cleaned} repos, {failed} failed"))
            self._emit_repos_changed()

        Thread(target=_task, daemon=True).start()

    def build_repo(self, repo_path):
        """Build a repository using its detected build system."""
        name = os.path.basename(repo_path.rstrip("/"))
        build_sys, _ = _detect_build_system(repo_path)

        def _task():
            success = False
            msg = ""
            try:
                self.log_signal.emit(f"Building {name} ({build_sys or 'unknown'})...")
                if build_sys == "Cargo":
                    r = subprocess.run(
                        ["cargo", "build", "--release"],
                        cwd=repo_path, capture_output=True, text=True, timeout=600)
                    success = r.returncode == 0
                    msg = "Build successful" if success else r.stderr[-500:]
                elif build_sys == "CMake":
                    build_dir = os.path.join(repo_path, "build")
                    os.makedirs(build_dir, exist_ok=True)
                    for cmd in [
                        ["cmake", ".."],
                        ["cmake", "--build", ".", "-j$(nproc)"],
                    ]:
                        r = subprocess.run(
                            cmd, cwd=build_dir, capture_output=True, text=True, timeout=600)
                        if r.returncode != 0:
                            msg = r.stderr[-500:]
                            break
                    else:
                        success = True
                        msg = "Build successful"
                elif build_sys == "Meson":
                    build_dir = os.path.join(repo_path, "builddir")
                    for cmd in [
                        ["meson", "setup", build_dir, "--prefix=/usr/local"],
                        ["ninja", "-C", build_dir],
                    ]:
                        r = subprocess.run(
                            cmd, cwd=repo_path, capture_output=True, text=True, timeout=600)
                        if r.returncode != 0:
                            msg = r.stderr[-500:]
                            break
                    else:
                        success = True
                        msg = "Build successful"
                elif build_sys == "Go":
                    r = subprocess.run(
                        ["go", "build", "./..."],
                        cwd=repo_path, capture_output=True, text=True, timeout=600)
                    success = r.returncode == 0
                    msg = "Build successful" if success else r.stderr[-500:]
                elif build_sys == "npm":
                    r = subprocess.run(
                        ["npm", "run", "build"],
                        cwd=repo_path, capture_output=True, text=True, timeout=600)
                    success = r.returncode == 0
                    msg = "Build successful" if success else r.stderr[-500:]
                elif build_sys == "Make":
                    r = subprocess.run(
                        ["make", "-j$(nproc)"],
                        cwd=repo_path, capture_output=True, text=True, timeout=600)
                    success = r.returncode == 0
                    msg = "Build successful" if success else r.stderr[-500:]
                else:
                    msg = "No supported build system detected"
            except Exception as e:
                msg = str(e)

            entry = {
                "name": name, "success": success,
                "message": msg, "time": time.time(),
                "build_system": build_sys,
            }
            self._build_history.insert(0, entry)
            if len(self._build_history) > 50:
                self._build_history = self._build_history[:50]
            self.log_signal.emit(f"{'✓' if success else '✕'} {name}: {msg}")
            QTimer.singleShot(0, lambda: self.build_completed.emit(name, success, msg))
            self._emit_repos_changed()

        Thread(target=_task, daemon=True).start()

    def get_build_history(self):
        """Return recent build history entries."""
        return list(self._build_history)

    def get_stats(self, repos=None):
        """Return overview statistics dict. Pass pre-fetched repos to avoid double scan."""
        if repos is None:
            repos = self.get_repos()
        total = len(repos)
        updates = sum(1 for r in repos if r.get("behind", 0) > 0)
        total_disk = sum(r.get("disk_usage", 0) for r in repos)
        builds_today = sum(
            1 for b in self._build_history
            if b.get("time", 0) > time.time() - 86400 and b.get("success"))
        return {
            "total": total,
            "updates": updates,
            "builds_today": builds_today,
            "disk_usage": total_disk,
            "disk_usage_fmt": _fmt_size(total_disk),
        }
