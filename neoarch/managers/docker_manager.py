"""Docker container management component for NeoArch.

Provides UI and backend for pulling, running, listing, stopping, and
cleaning Docker containers with advanced options for ports, volumes,
environment variables, GPU passthrough, and restart policies.
"""

import os
import subprocess
from threading import Thread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit, QMessageBox,
    QPlainTextEdit, QComboBox, QCheckBox, QMenu, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QObject, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QRectF

from neoarch.resources.paths import ICONS_DIR

__all__ = ["DockerManager"]


class DockerManager(QObject):
    """Docker container management component for NeoArch."""

    def __init__(self, log_signal, show_message_signal, sources_layout, parent=None):
        super().__init__()
        self.log_signal = log_signal
        self.show_message = show_message_signal
        self.sources_layout = sources_layout
        self.parent = parent
        self.docker_section = None
        self.recent_containers_label = None
        self.recent_containers_list = None
        self.create_docker_section()

    def create_docker_section(self):
        """Create and add the Docker section UI to the sources layout."""
        self.docker_section = QWidget()
        docker_layout = QVBoxLayout(self.docker_section)
        docker_layout.setContentsMargins(0, 8, 0, 0)
        docker_layout.setSpacing(10)

        docker_label = QLabel("Docker Containers")
        docker_label.setObjectName("sectionLabel")
        docker_label.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
        docker_layout.addWidget(docker_label)

        install_docker_container = QWidget()
        install_docker_layout = QHBoxLayout(install_docker_container)
        install_docker_layout.setContentsMargins(0, 0, 0, 0)
        install_docker_layout.setSpacing(8)

        docker_icon_label = QLabel()
        docker_icon_path = ICONS_DIR / "discover" / "docker.svg"
        try:
            svg_renderer = QSvgRenderer(str(docker_icon_path))
            if svg_renderer.isValid():
                pixmap = QPixmap(20, 20)
                if pixmap.isNull():
                    docker_icon_label.setText("\U0001f433")
                    docker_icon_label.setStyleSheet("font-size: 14px; color: white;")
                else:
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    svg_renderer.render(painter, QRectF(pixmap.rect()))
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                    painter.fillRect(pixmap.rect(), QColor("white"))
                    painter.end()
                    docker_icon_label.setPixmap(pixmap)
            else:
                docker_icon_label.setText("\U0001f433")
        except OSError:
            docker_icon_label.setText("\U0001f433")

        install_docker_layout.addWidget(docker_icon_label)

        install_docker_btn = QPushButton("Run from Docker")
        install_docker_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.3); border-radius: 6px;
                padding: 6px 10px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.5); }
            QPushButton:pressed { background-color: rgba(0, 191, 174, 0.25); }
        """)
        install_docker_btn.clicked.connect(self.install_from_docker)
        install_docker_layout.addWidget(install_docker_btn)
        docker_layout.addWidget(install_docker_container)

        secondary_buttons_widget = QWidget()
        secondary_layout = QHBoxLayout(secondary_buttons_widget)
        secondary_layout.setContentsMargins(0, 0, 0, 0)
        secondary_layout.setSpacing(4)

        list_btn = QPushButton("\U0001f4cb List")
        list_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15); border-radius: 4px;
                padding: 6px 10px; font-size: 10px; text-align: center;
            }
            QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.35); color: #00BFAE; }
        """)
        list_btn.clicked.connect(self.list_docker_containers)
        secondary_layout.addWidget(list_btn)

        stop_btn = QPushButton("\u23f9\ufe0f Stop")
        stop_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15); border-radius: 4px;
                padding: 6px 10px; font-size: 10px; text-align: center;
            }
            QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.35); color: #FF6B6B; }
        """)
        stop_btn.clicked.connect(self.show_stop_menu)
        secondary_layout.addWidget(stop_btn)

        clean_btn = QPushButton("\U0001f5d1\ufe0f Clean")
        clean_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #F0F0F0;
                border: 1px solid rgba(0, 191, 174, 0.15); border-radius: 4px;
                padding: 6px 10px; font-size: 10px; text-align: center;
            }
            QPushButton:hover { background-color: rgba(0, 191, 174, 0.15); border-color: rgba(0, 191, 174, 0.35); color: #FF6B6B; }
        """)
        clean_btn.clicked.connect(self.clean_docker_containers)
        secondary_layout.addWidget(clean_btn)
        docker_layout.addWidget(secondary_buttons_widget)

        self.recent_containers_label = QLabel("Containers:")
        self.recent_containers_label.setStyleSheet("color: #C9C9C9; font-size: 10px; margin-top: 4px;")
        docker_layout.addWidget(self.recent_containers_label)

        self.recent_containers_list = QListWidget()
        self.recent_containers_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(42, 45, 51, 0.4);
                border: 1px solid rgba(0, 191, 174, 0.15);
                color: #F0F0F0; font-size: 10px; max-height: 85px;
            }
            QListWidget::item:hover { background-color: rgba(0, 191, 174, 0.15); }
            QListWidget::item:selected { background-color: rgba(0, 191, 174, 0.25); }
        """)
        self.recent_containers_list.itemDoubleClicked.connect(self.open_container_logs)
        self.recent_containers_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.recent_containers_list.customContextMenuRequested.connect(self.show_container_menu)
        try:
            self.recent_containers_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        except Exception:
            pass
        self.recent_containers_list.setVisible(False)
        docker_layout.addWidget(self.recent_containers_list)

        self.sources_layout.addWidget(self.docker_section)
        self.load_containers(include_all=True)

    def install_from_docker(self):
        """Open the advanced Docker run dialog."""
        self.show_advanced_run_dialog()

    def show_advanced_run_dialog(self):
        """Show the advanced Docker run dialog with full options."""
        import shlex
        dialog = QDialog()
        dialog.setWindowTitle("Run Container from Docker Image")
        dialog.setModal(True)
        dialog.setStyleSheet("QDialog { background-color: #1E1E1E; color: #F0F0F0; border: 1px solid rgba(0, 191, 174, 0.2); }")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Run Application from Docker Image")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00BFAE;")
        layout.addWidget(title)

        image_input = QLineEdit()
        image_input.setPlaceholderText("nginx:latest or user/app:v1.0")
        image_input.setStyleSheet("QLineEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; padding:8px 12px; font-size:14px; } QLineEdit:focus { border-color:#00BFAE; }")
        layout.addWidget(QLabel("Image"))
        layout.addWidget(image_input)

        name_input = QLineEdit()
        name_input.setPlaceholderText("optional container name")
        name_input.setStyleSheet("QLineEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; padding:6px 10px; font-size:12px; } QLineEdit:focus { border-color:#00BFAE; }")
        layout.addWidget(QLabel("Name"))
        layout.addWidget(name_input)

        ports_edit = QPlainTextEdit()
        ports_edit.setPlaceholderText("8080:80\n127.0.0.1:2222:22/tcp")
        ports_edit.setFixedHeight(70)
        ports_edit.setStyleSheet("QPlainTextEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; }")
        layout.addWidget(QLabel("Ports (one per line: host:container[/proto])"))
        layout.addWidget(ports_edit)

        vols_edit = QPlainTextEdit()
        vols_edit.setPlaceholderText("/host/path:/container/path:ro\n~/data:/var/lib/data:rw")
        vols_edit.setFixedHeight(80)
        vols_edit.setStyleSheet("QPlainTextEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; }")
        layout.addWidget(QLabel("Volumes (one per line: host:container[:ro|rw])"))
        layout.addWidget(vols_edit)

        env_edit = QPlainTextEdit()
        env_edit.setPlaceholderText("KEY=value\nMODE=prod")
        env_edit.setFixedHeight(80)
        env_edit.setStyleSheet("QPlainTextEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; }")
        layout.addWidget(QLabel("Environment (one per line: KEY=VALUE)"))
        layout.addWidget(env_edit)

        opt_row = QHBoxLayout()
        restart_combo = QComboBox()
        restart_combo.addItems(["no", "always", "unless-stopped", "on-failure"])
        detach_chk = QCheckBox("Detach")
        detach_chk.setChecked(True)
        priv_chk = QCheckBox("Privileged")
        gpu_chk = QCheckBox("GPU")
        opt_row.addWidget(QLabel("Restart"))
        opt_row.addWidget(restart_combo)
        opt_row.addStretch()
        opt_row.addWidget(detach_chk)
        opt_row.addWidget(priv_chk)
        opt_row.addWidget(gpu_chk)
        layout.addLayout(opt_row)

        cmd_input = QLineEdit()
        cmd_input.setPlaceholderText("optional command and args")
        cmd_input.setStyleSheet("QLineEdit { background-color: rgba(42,45,51,0.8); color:#F0F0F0; border:2px solid rgba(0,191,174,0.2); border-radius:6px; padding:6px 10px; font-size:12px; } QLineEdit:focus { border-color:#00BFAE; }")
        layout.addWidget(QLabel("Command"))
        layout.addWidget(cmd_input)

        preview = QPlainTextEdit()
        preview.setReadOnly(True)
        preview.setFixedHeight(80)
        preview.setStyleSheet("QPlainTextEdit { background-color: rgba(42,45,51,0.6); color:#CFCFCF; border:1px solid rgba(0,191,174,0.15); border-radius:6px; }")
        layout.addWidget(QLabel("Preview"))
        layout.addWidget(preview)

        def build_preview():
            image = image_input.text().strip()
            name = name_input.text().strip()
            cmd = ["docker", "run"]
            if detach_chk.isChecked():
                cmd.append("-d")
            if name:
                cmd += ["--name", name]
            rp = restart_combo.currentText()
            if rp != "no":
                cmd += ["--restart", rp]
            if priv_chk.isChecked():
                cmd.append("--privileged")
            if gpu_chk.isChecked():
                cmd += ["--gpus", "all"]
            for ln in ports_edit.toPlainText().splitlines():
                t = ln.strip()
                if t:
                    cmd += ["-p", t]
            for ln in vols_edit.toPlainText().splitlines():
                t = ln.strip()
                if t:
                    cmd += ["-v", t]
            for ln in env_edit.toPlainText().splitlines():
                t = ln.strip()
                if t:
                    cmd += ["-e", t]
            if image:
                cmd.append(image)
            extra = cmd_input.text().strip()
            if extra:
                try:
                    cmd += shlex.split(extra)
                except Exception:
                    cmd.append(extra)
            preview.setPlainText(" ".join(shlex.quote(x) for x in cmd))
        for w in [image_input, name_input, ports_edit, vols_edit, env_edit, restart_combo, detach_chk, priv_chk, gpu_chk, cmd_input]:
            try:
                if hasattr(w, 'textChanged'):
                    w.textChanged.connect(build_preview)
                elif hasattr(w, 'currentIndexChanged'):
                    w.currentIndexChanged.connect(build_preview)
                elif hasattr(w, 'stateChanged'):
                    w.stateChanged.connect(build_preview)
            except Exception:
                pass
        build_preview()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        run_btn = QPushButton("Run Container")
        run_btn.setDefault(True)

        def on_run():
            self.proceed_advanced_run(
                image_input.text().strip(), name_input.text().strip(),
                [ln.strip() for ln in ports_edit.toPlainText().splitlines() if ln.strip()],
                [ln.strip() for ln in vols_edit.toPlainText().splitlines() if ln.strip()],
                [ln.strip() for ln in env_edit.toPlainText().splitlines() if ln.strip()],
                restart_combo.currentText().strip(), detach_chk.isChecked(),
                priv_chk.isChecked(), gpu_chk.isChecked(), cmd_input.text().strip(), dialog
            )
        run_btn.clicked.connect(on_run)
        btn_row.addWidget(run_btn)
        layout.addLayout(btn_row)
        dialog.exec()

    def ensure_image_local(self, image):
        """Ensure a Docker image is pulled locally."""
        try:
            r = subprocess.run(["docker", "image", "inspect", image], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return True
        except Exception:
            pass
        self.log_signal.emit(f"Pulling image: {image}")
        try:
            p = subprocess.Popen(["docker", "pull", image], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            while True:
                line = p.stdout.readline() if p.stdout else ""
                if not line and p.poll() is not None:
                    break
                if line:
                    self.log_signal.emit(line.strip())
            _, err = p.communicate()
            if p.returncode != 0:
                if err:
                    self.log_signal.emit(err.strip())
                self.show_message.emit("Docker Pull Failed", f"Failed to pull {image}")
                return False
            self.show_message.emit("Docker", f"Pulled {image}")
            return True
        except Exception as e:
            self.log_signal.emit(str(e))
            self.show_message.emit("Docker Pull Failed", str(e))
            return False

    def proceed_advanced_run(self, image, name, ports, vols, envs, restart_policy, detach, privileged, use_gpu, extra_cmd, dialog):
        """Execute the Docker run command with all specified options."""
        import shlex
        if not image:
            QMessageBox.warning(None, "Invalid Image", "Please enter a valid Docker image name.")
            return
        dialog.accept()
        self.log_signal.emit(f"Starting Docker container from image: {image}")

        def run_thread():
            try:
                if not self.ensure_image_local(image):
                    return
                cmd = ["docker", "run"]
                if detach:
                    cmd.append("-d")
                if name:
                    cmd += ["--name", name]
                if restart_policy and restart_policy != "no":
                    cmd += ["--restart", restart_policy]
                if privileged:
                    cmd.append("--privileged")
                if use_gpu:
                    cmd += ["--gpus", "all"]
                for p in ports:
                    cmd += ["-p", p]
                for v in vols:
                    hv = v
                    try:
                        parts = v.split(":")
                        if len(parts) >= 2:
                            host = os.path.expanduser(parts[0])
                            cont = parts[1]
                            mode = parts[2] if len(parts) > 2 else None
                            hv = host + ":" + cont + (":" + mode if mode else "")
                    except Exception:
                        hv = v
                    cmd += ["-v", hv]
                for e in envs:
                    cmd += ["-e", e]
                cmd.append(image)
                if extra_cmd:
                    try:
                        cmd += shlex.split(extra_cmd)
                    except Exception:
                        cmd.append(extra_cmd)
                self.log_signal.emit("Running command: " + " ".join(shlex.quote(x) for x in cmd))
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    cid = (result.stdout or "").strip()
                    if cid:
                        self.log_signal.emit(f"Container started: {cid}")
                    self.show_message.emit("Container Started", f"Started container from {image}")
                    self.load_containers(include_all=True)
                else:
                    self.log_signal.emit((result.stderr or "Failed").strip())
                    self.show_message.emit("Container Start Failed", (result.stderr or "Failed").strip())
            except Exception as e:
                self.log_signal.emit(f"Error running Docker container: {str(e)}")
                self.show_message.emit("Container Start Failed", f"Error: {str(e)}")
        Thread(target=run_thread, daemon=True).start()

    def list_docker_containers(self):
        """List all Docker containers to the log."""
        try:
            result = subprocess.run(["docker", "ps", "-a", "--format", "table {{.Names}}\\t{{.Image}}\\t{{.Status}}"],
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.log_signal.emit("Docker containers:")
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        self.log_signal.emit(f"  {line}")
            else:
                self.log_signal.emit(f"Failed to list containers: {result.stderr}")
        except Exception as e:
            self.log_signal.emit(f"Error listing containers: {str(e)}")

    def show_stop_menu(self):
        """Show context menu for stopping containers."""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #2A2D33; color: #F0F0F0; border: 1px solid rgba(0,191,174,0.3); }
            QMenu::item:selected { background-color: rgba(0,191,174,0.2); }
        """)
        stop_running = menu.addAction("Stop Running Containers")
        stop_all = menu.addAction("Stop All Containers")
        action = menu.exec(QCursor.pos())
        if action == stop_running:
            self.stop_docker_containers(only_running=True)
        elif action == stop_all:
            self.stop_docker_containers(only_running=False)

    def show_container_menu(self, pos):
        """Show context menu for a container in the list."""
        item = self.recent_containers_list.itemAt(pos)
        if not item:
            return
        cid = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #2A2D33; color: #F0F0F0; border: 1px solid rgba(0,191,174,0.3); }
            QMenu::item:selected { background-color: rgba(0,191,174,0.2); }
        """)
        start_action = menu.addAction("Start")
        stop_action = menu.addAction("Stop")
        restart_action = menu.addAction("Restart")
        logs_action = menu.addAction("View Logs")
        shell_action = menu.addAction("Open Shell")
        remove_action = menu.addAction("Remove")
        action = menu.exec(self.recent_containers_list.mapToGlobal(pos))

        try:
            if action == start_action:
                subprocess.run(["docker", "start", cid], capture_output=True, text=True, timeout=30)
                self.log_signal.emit(f"Started container: {cid}")
                self.load_containers()
            elif action == stop_action:
                subprocess.run(["docker", "stop", cid], capture_output=True, text=True, timeout=30)
                self.log_signal.emit(f"Stopped container: {cid}")
                self.load_containers()
            elif action == restart_action:
                subprocess.run(["docker", "restart", cid], capture_output=True, text=True, timeout=60)
                self.log_signal.emit(f"Restarted container: {cid}")
                self.load_containers()
            elif action == logs_action:
                logs = subprocess.run(["docker", "logs", "--tail", "50", cid], capture_output=True, text=True, timeout=30)
                self.log_signal.emit(f"Logs for {cid}:")
                for line in (logs.stdout or '').strip().split('\n'):
                    if line.strip():
                        self.log_signal.emit(f"  {line}")
            elif action == shell_action:
                self.open_container_shell(cid)
            elif action == remove_action:
                subprocess.run(["docker", "rm", "-f", cid], capture_output=True, text=True, timeout=30)
                self.log_signal.emit(f"Removed container: {cid}")
                self.load_containers()
        except Exception as e:
            self.log_signal.emit(f"Error: {e}")

    def open_container_shell(self, cid):
        """Open a shell in the specified container."""
        try:
            subprocess.Popen(["docker", "exec", "-it", cid, "/bin/bash"])
        except Exception:
            try:
                subprocess.Popen(["docker", "exec", "-it", cid, "/bin/sh"])
            except Exception as e:
                self.log_signal.emit(f"Failed to open shell: {e}")

    def open_container_logs(self, item):
        """Open logs for the container represented by the clicked item."""
        cid = item.data(Qt.ItemDataRole.UserRole)
        if cid:
            self.show_container_logs(cid)

    def show_container_logs(self, cid):
        """Show container logs in a dialog."""
        dialog = QDialog()
        dialog.setWindowTitle(f"Container Logs: {cid}")
        dialog.setMinimumSize(600, 400)
        dialog.setStyleSheet("QDialog { background-color: #1E1E1E; color: #F0F0F0; }")
        layout = QVBoxLayout(dialog)
        log_view = QPlainTextEdit()
        log_view.setReadOnly(True)
        log_view.setStyleSheet("QPlainTextEdit { background-color: #2A2D33; color: #C9C9C9; font-family: monospace; }")
        layout.addWidget(log_view)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        try:
            logs = subprocess.run(["docker", "logs", "--tail", "100", cid], capture_output=True, text=True, timeout=30)
            log_view.setPlainText(logs.stdout or "No logs available")
        except Exception as e:
            log_view.setPlainText(f"Error fetching logs: {e}")
        dialog.exec()

    def load_containers(self, include_all=False):
        """Load Docker containers into the list widget."""
        try:
            fmt = "{{.ID}}\\t{{.Names}}\\t{{.Image}}\\t{{.Status}}"
            cmd = ["docker", "ps"] + (["-a"] if include_all else []) + ["--format", fmt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            containers = []
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        containers.append({
                            'id': parts[0],
                            'name': parts[1],
                            'image': parts[2],
                            'status': parts[3] if len(parts) > 3 else ''
                        })
            if containers and self.recent_containers_list:
                self.recent_containers_list.clear()
                for c in containers:
                    item_text = f"\U0001f433 {c['name']} ({c['image']})"
                    item = QListWidgetItem(item_text)
                    item.setToolTip(f"ID: {c['id']}\nStatus: {c['status']}")
                    item.setData(Qt.ItemDataRole.UserRole, c['id'])
                    self.recent_containers_list.addItem(item)
                if self.recent_containers_label:
                    self.recent_containers_label.setVisible(True)
                self.recent_containers_list.setVisible(True)
            else:
                if self.recent_containers_label:
                    self.recent_containers_label.setVisible(False)
                if self.recent_containers_list:
                    self.recent_containers_list.setVisible(False)
        except Exception as e:
            self.log_signal.emit(f"Error loading containers: {e}")

    def stop_docker_containers(self, only_running=True):
        """Stop Docker containers."""
        try:
            cmd = ["docker", "ps", "-q"] if only_running else ["docker", "ps", "-a", "-q"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                containers = result.stdout.strip().split('\n')
                self.log_signal.emit(f"Stopping {len(containers)} containers...")
                for container_id in containers:
                    stop_result = subprocess.run(["docker", "stop", container_id], capture_output=True, text=True, timeout=30)
                    if stop_result.returncode == 0:
                        self.log_signal.emit(f"Stopped container: {container_id}")
                    else:
                        self.log_signal.emit(f"Failed to stop container {container_id}: {stop_result.stderr}")
                self.show_message.emit("Containers Stopped", f"Stopped {len(containers)} containers")
            else:
                self.log_signal.emit("No running containers to stop")
        except Exception as e:
            self.log_signal.emit(f"Error stopping containers: {str(e)}")

    def clean_docker_containers(self):
        """Clean up Docker resources (stopped containers, unused networks, dangling images)."""
        reply = QMessageBox.question(None, "Clean Docker Containers",
                                     "This will clean up:\n"
                                     "- Stopped containers\n"
                                     "- Unused networks\n"
                                     "- Dangling images\n\n"
                                     "This cannot be undone.\n\n"
                                     "Proceed?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.log_signal.emit("Cleaning Docker containers...")

        def clean_thread():
            steps = [
                ("Removing stopped containers...", ["docker", "container", "prune", "-f"]),
                ("Removing unused networks...", ["docker", "network", "prune", "-f"]),
                ("Removing dangling images...", ["docker", "image", "prune", "-f"]),
            ]
            for msg, cmd in steps:
                try:
                    self.log_signal.emit(msg)
                    subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                except Exception as e:
                    self.log_signal.emit(f"Error: {e}")
            self.log_signal.emit("Docker cleanup complete")
            QTimer.singleShot(0, lambda: self.show_message.emit("Docker Clean Complete", "Docker containers cleaned successfully"))
            self.load_containers(include_all=True)
        Thread(target=clean_thread, daemon=True).start()
