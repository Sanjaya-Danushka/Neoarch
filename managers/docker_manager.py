# docker_manager.py - Docker container management component for Aurora

import os
import shutil
import subprocess
from threading import Thread
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QListWidget, QListWidgetItem, QDialog, QLineEdit, QMessageBox,
                             QPlainTextEdit, QComboBox, QCheckBox, QMenu, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor, QCursor
from PyQt6.QtSvg import QSvgRenderer


class DockerManager(QObject):
    """Docker container management component for Aurora"""

    def __init__(self, log_signal, show_message_signal, sources_layout, parent=None):
        super().__init__()
        self.log_signal = log_signal
        self.show_message = show_message_signal
        self.sources_layout = sources_layout
        self.parent = parent  # Reference to main window

        # UI elements that will be created
        self.docker_section = None  # Reference to the docker section widget
        self.recent_containers_label = None
        self.recent_containers_list = None

        # Initialize the Docker section UI
        self.create_docker_section()

    def create_docker_section(self):
        """Create and add the Docker section to the sources layout"""
        self.docker_section = QWidget()
        docker_layout = QVBoxLayout(self.docker_section)
        docker_layout.setContentsMargins(0, 8, 0, 0)  # Add top margin for spacing
        docker_layout.setSpacing(10)  # Increase spacing between elements

        # Docker section label
        docker_label = QLabel("Docker Containers")
        docker_label.setObjectName("sectionLabel")
        docker_label.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
        docker_layout.addWidget(docker_label)

        # Main Run from Docker button (separate at top)
        install_docker_container = QWidget()
        install_docker_layout = QHBoxLayout(install_docker_container)
        install_docker_layout.setContentsMargins(0, 0, 0, 0)
        install_docker_layout.setSpacing(8)

        # Docker icon
        docker_icon_label = QLabel()
        docker_icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "discover", "docker.svg")
        try:
            svg_renderer = QSvgRenderer(docker_icon_path)
            if svg_renderer.isValid():
                pixmap = QPixmap(20, 20)
                if pixmap.isNull():
                    docker_icon_label.setText("🐳")
                    docker_icon_label.setStyleSheet("font-size: 14px; color: white;")
                else:
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    from PyQt6.QtCore import QRectF
                    svg_renderer.render(painter, QRectF(pixmap.rect()))
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                    painter.fillRect(pixmap.rect(), QColor("white"))
                    painter.end()
                    docker_icon_label.setPixmap(pixmap)
            else:
                docker_icon_label.setText("🐳")
        except OSError:
            # Handle file loading or parsing errors
            docker_icon_label.setText("🐳")

        install_docker_layout.addWidget(docker_icon_label)

        # Install button
        install_docker_btn = QPushButton("Run from Docker")
        install_docker_btn.setStyleSheet("""
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
        install_docker_btn.clicked.connect(self.install_from_docker)
        install_docker_layout.addWidget(install_docker_btn)

        docker_layout.addWidget(install_docker_container)

        # Secondary buttons widget (at bottom)
        secondary_buttons_widget = QWidget()
        secondary_layout = QHBoxLayout(secondary_buttons_widget)
        secondary_layout.setContentsMargins(0, 0, 0, 0)
        secondary_layout.setSpacing(4)

        # List containers button
        list_containers_btn = QPushButton("📋 List")
        list_containers_btn.setStyleSheet("""
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
        list_containers_btn.clicked.connect(self.list_docker_containers)
        secondary_layout.addWidget(list_containers_btn)

        # Stop containers button
        stop_containers_btn = QPushButton("⏹️ Stop")
        stop_containers_btn.setStyleSheet("""
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
        stop_containers_btn.clicked.connect(self.show_stop_menu)
        secondary_layout.addWidget(stop_containers_btn)

        # Clean containers button
        clean_containers_btn = QPushButton("🗑️ Clean")
        clean_containers_btn.setStyleSheet("""
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
        clean_containers_btn.clicked.connect(self.clean_docker_containers)
        secondary_layout.addWidget(clean_containers_btn)

        docker_layout.addWidget(secondary_buttons_widget)

        # Recent containers list (compact)
        self.recent_containers_label = QLabel("Containers:")
        self.recent_containers_label.setStyleSheet("color: #C9C9C9; font-size: 10px; margin-top: 4px;")
        docker_layout.addWidget(self.recent_containers_label)

        self.recent_containers_list = QListWidget()
        self.recent_containers_list.setStyleSheet("""
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
        self.recent_containers_list.itemDoubleClicked.connect(self.open_container_logs)
        self.recent_containers_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.recent_containers_list.customContextMenuRequested.connect(self.show_container_menu)
        try:
            self.recent_containers_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        except Exception:
            pass
        self.recent_containers_list.setVisible(False)  # Initially hidden
        docker_layout.addWidget(self.recent_containers_list)

        self.sources_layout.addWidget(self.docker_section)

        # Load containers on startup
        self.load_containers(include_all=True)

    def install_from_docker(self):
        self.show_advanced_run_dialog()

    def show_advanced_run_dialog(self):
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
            image = image_input.text().strip()
            name = name_input.text().strip()
            ports = [ln.strip() for ln in ports_edit.toPlainText().splitlines() if ln.strip()]
            vols = [ln.strip() for ln in vols_edit.toPlainText().splitlines() if ln.strip()]
            envs = [ln.strip() for ln in env_edit.toPlainText().splitlines() if ln.strip()]
            rp = restart_combo.currentText().strip()
            detach = detach_chk.isChecked()
            priv = priv_chk.isChecked()
            gpu = gpu_chk.isChecked()
            extra = cmd_input.text().strip()
            self.proceed_advanced_run(image, name, ports, vols, envs, rp, detach, priv, gpu, extra, dialog)
        run_btn.clicked.connect(on_run)
        btn_row.addWidget(run_btn)
        layout.addLayout(btn_row)
        dialog.exec()

    def ensure_image_local(self, image):
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

    def proceed_docker_run(self, image_name, port_mapping, dialog):
        """Handle the actual Docker container running process"""
        if not image_name:
            QMessageBox.warning(None, "Invalid Image", "Please enter a valid Docker image name.")
            return

        dialog.accept()

        self.log_signal.emit(f"Starting Docker container from image: {image_name}")

        def run_docker_thread():
            try:
                # Build the docker run command
                cmd = ["docker", "run", "-d", "--name", f"aurora-{image_name.replace('/', '-').replace(':', '-')}-{os.urandom(4).hex()}"]

                # Add port mapping if specified
                if port_mapping:
                    cmd.extend(["-p", port_mapping])

                cmd.append(image_name)

                self.log_signal.emit(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    container_id = result.stdout.strip()
                    self.log_signal.emit(f"Container started successfully with ID: {container_id}")
                    self.show_message.emit("Container Started", f"Successfully started container from {image_name}")
                    # Refresh containers list
                    self.load_containers(include_all=True)
                else:
                    self.log_signal.emit(f"Failed to start container: {result.stderr}")
                    self.show_message.emit("Container Start Failed", f"Failed to start container: {result.stderr}")

            except Exception as e:
                self.log_signal.emit(f"Error running Docker container: {str(e)}")
                self.show_message.emit("Container Start Failed", f"Error: {str(e)}")

        Thread(target=run_docker_thread, daemon=True).start()

    def list_docker_containers(self):
        """List all Docker containers"""
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

    def stop_docker_containers(self):
        """Stop running Docker containers"""
        try:
            # Get running containers
            result = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=30)
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
                # Refresh containers list
                self.load_containers(include_all=True)
        except Exception as e:
            self.log_signal.emit(f"Error stopping containers: {str(e)}")

    def start_container(self, name):
        try:
            r = subprocess.run(["docker", "start", name], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                self.show_message.emit("Docker", f"Started {name}")
            else:
                self.show_message.emit("Docker", f"Failed to start {name}: {r.stderr}")
        except Exception as e:
            self.show_message.emit("Docker", f"Error starting {name}: {e}")
        self.load_containers(include_all=True)

    def stop_container(self, name):
        try:
            r = subprocess.run(["docker", "stop", name], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                self.show_message.emit("Docker", f"Stopped {name}")
            else:
                self.show_message.emit("Docker", f"Failed to stop {name}: {r.stderr}")
        except Exception as e:
            self.show_message.emit("Docker", f"Error stopping {name}: {e}")
        self.load_containers(include_all=True)

    def restart_container(self, name):
        try:
            r = subprocess.run(["docker", "restart", name], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                self.show_message.emit("Docker", f"Restarted {name}")
            else:
                self.show_message.emit("Docker", f"Failed to restart {name}: {r.stderr}")
        except Exception as e:
            self.show_message.emit("Docker", f"Error restarting {name}: {e}")
        self.load_containers(include_all=True)

    def remove_container(self, name):
        try:
            r = subprocess.run(["docker", "rm", name], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                self.show_message.emit("Docker", f"Removed {name}")
            else:
                self.show_message.emit("Docker", f"Failed to remove {name}: {r.stderr}")
        except Exception as e:
            self.show_message.emit("Docker", f"Error removing {name}: {e}")
        self.load_containers(include_all=True)

    def remove_all_exited(self):
        try:
            r = subprocess.run(["docker", "container", "prune", "-f"], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                self.show_message.emit("Docker", "Removed exited containers")
            else:
                self.show_message.emit("Docker", f"Failed to prune: {r.stderr}")
        except Exception as e:
            self.show_message.emit("Docker", f"Error pruning: {e}")
        self.load_containers(include_all=True)

    def show_stop_menu(self):
        sender = self.sender()
        menu = QMenu()
        selected = [it.data(Qt.ItemDataRole.UserRole) for it in self.recent_containers_list.selectedItems()]
        act_start = menu.addAction("Start Selected")
        act_stop = menu.addAction("Stop Selected")
        act_restart = menu.addAction("Restart Selected")
        act_remove = menu.addAction("Remove Selected")
        act_shell_sel = menu.addAction("Open Shell in Selected")
        menu.addSeparator()
        act_stop_all = menu.addAction("Stop All")
        act_remove_exited = menu.addAction("Remove All Exited")
        # Enable rules
        has_sel = bool(selected)
        act_start.setEnabled(has_sel)
        act_stop.setEnabled(has_sel)
        act_restart.setEnabled(has_sel)
        act_remove.setEnabled(has_sel)
        act_shell_sel.setEnabled(has_sel)
        # Exec menu
        pos = sender.mapToGlobal(QPoint(0, sender.height())) if hasattr(sender, 'mapToGlobal') else QCursor.pos()
        action = menu.exec(pos)
        if action is None:
            return
        if action == act_start:
            for n in selected:
                self.start_container(n)
        elif action == act_stop:
            for n in selected:
                self.stop_container(n)
        elif action == act_restart:
            for n in selected:
                self.restart_container(n)
        elif action == act_remove:
            for n in selected:
                self.remove_container(n)
        elif action == act_stop_all:
            self.stop_docker_containers()
        elif action == act_remove_exited:
            self.remove_all_exited()
        elif action == act_shell_sel:
            for n in selected:
                self.open_shell_in_container(n)

    def show_container_menu(self, pos):
        item = self.recent_containers_list.itemAt(pos)
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu()
        act_logs = menu.addAction("View Logs")
        act_shell = menu.addAction("Open Shell")
        act_start = menu.addAction("Start")
        act_stop = menu.addAction("Stop")
        act_restart = menu.addAction("Restart")
        act_remove = menu.addAction("Remove")
        action = menu.exec(self.recent_containers_list.mapToGlobal(pos))
        if action is None:
            return
        if action == act_logs:
            self.open_container_logs(item)
        elif action == act_shell:
            self.open_shell_in_container(name)
        elif action == act_start:
            self.start_container(name)
        elif action == act_stop:
            self.stop_container(name)
        elif action == act_restart:
            self.restart_container(name)
        elif action == act_remove:
            self.remove_container(name)

    def _find_terminal_emulator(self):
        candidates = [
            "gnome-terminal",
            "konsole",
            "alacritty",
            "kitty",
            "xfce4-terminal",
            "tilix",
            "wezterm",
            "footclient",
            "xterm",
            "lxterminal",
        ]
        for name in candidates:
            if shutil.which(name):
                return name
        return None

    def _build_terminal_args(self, term: str, command: str, title: str | None = None):
        # Run command inside bash -lc to interpret; keep window open after exit
        if term == "gnome-terminal":
            args = [term, "--", "bash", "-lc", command]
            if title:
                args.insert(1, "--title=%s" % title)
            return args
        if term == "konsole":
            args = [term, "-e", "bash", "-lc", command]
            if title:
                args.extend(["--title", title])
            return args
        if term in ("alacritty", "tilix"):
            return [term, "-e", "bash", "-lc", command]
        if term == "kitty":
            return [term, "bash", "-lc", command]
        if term == "wezterm":
            return [term, "start", "--", "bash", "-lc", command]
        if term == "footclient":
            return [term, "bash", "-lc", command]
        if term == "xterm":
            return [term, "-e", "bash", "-lc", command]
        if term == "xfce4-terminal" or term == "lxterminal":
            # These expect a single string for -e
            return [term, "-e", f"bash -lc \"{command}\""]
        # Fallback: try to run in xterm-like
        return [term, "-e", "bash", "-lc", command]

    def open_shell_in_container(self, name: str):
        import shlex
        name_q = shlex.quote(name)
        inner = f"docker exec -it {name_q} bash || docker exec -it {name_q} sh"
        cmd = inner + "; echo; echo 'Shell exited.'; echo 'Press Enter to close...'; read"
        term = self._find_terminal_emulator()
        if not term:
            self.show_message.emit("Docker", "No terminal emulator found. Install gnome-terminal/konsole/xterm/kitty/etc.")
            return
        try:
            args = self._build_terminal_args(term, cmd, title=f"Container: {name}")
            subprocess.Popen(args)
            self.show_message.emit("Docker", f"Opening shell in {name}...")
        except Exception as e:
            self.show_message.emit("Docker", f"Failed to open shell: {e}")

    def remove_docker_section(self):
        """Remove the Docker section from the sources layout"""
        if self.docker_section and self.sources_layout:
            self.sources_layout.removeWidget(self.docker_section)
            self.docker_section.setParent(None)
            self.docker_section.deleteLater()
            self.docker_section = None
            self.log_signal.emit("Docker section removed from sources panel")
            # Clear the reference in parent so it can be recreated
            if self.parent:
                self.parent.docker_manager = None

    def clean_docker_containers(self):
        """Clean up Docker containers and images"""
        try:
            # Ask for confirmation
            reply = QMessageBox.question(
                None, "Clean Docker",
                "This will remove stopped containers and unused images.\n\nAre you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            self.log_signal.emit("Cleaning Docker containers and images...")

            # Remove stopped containers
            clean_result = subprocess.run(["docker", "container", "prune", "-f"], capture_output=True, text=True, timeout=60)
            if clean_result.returncode == 0:
                self.log_signal.emit("Removed stopped containers")
            else:
                self.log_signal.emit(f"Failed to clean containers: {clean_result.stderr}")

            # Remove unused images
            image_result = subprocess.run(["docker", "image", "prune", "-f"], capture_output=True, text=True, timeout=60)
            if image_result.returncode == 0:
                self.log_signal.emit("Removed unused images")
            else:
                self.log_signal.emit(f"Failed to clean images: {image_result.stderr}")

            self.show_message.emit("Docker Clean Complete", "Cleaned containers and images")

        except Exception as e:
            self.log_signal.emit(f"Error cleaning Docker: {str(e)}")

    def load_containers(self, include_all: bool = True):
        """Load and display Docker containers (running or all)"""
        try:
            base = ["docker", "ps"]
            if include_all:
                base.append("-a")
            base += ["--format", "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}"]
            result = subprocess.run(base, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout is not None:
                containers = []
                for line in [l for l in result.stdout.strip().split('\n') if l.strip()]:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        name = parts[0]
                        image = parts[1]
                        status = parts[2]
                        ports = parts[3] if len(parts) > 3 else ""
                        containers.append((name, image, status, ports))

                self.recent_containers_list.clear()
                if containers:
                    for name, image, status, ports in containers:
                        status_info = f" - {status}" if status else ""
                        port_info = f" ({ports})" if ports else ""
                        item = QListWidgetItem(f"🐳 {name} - {image}{status_info}{port_info}")
                        item.setToolTip(f"Container: {name}\nImage: {image}\nStatus: {status}\nPorts: {ports}")
                        item.setData(Qt.ItemDataRole.UserRole, name)
                        self.recent_containers_list.addItem(item)
                    self.recent_containers_label.setVisible(True)
                    self.recent_containers_list.setVisible(True)
                else:
                    self.recent_containers_label.setVisible(False)
                    self.recent_containers_list.setVisible(False)
            else:
                self.recent_containers_label.setVisible(False)
                self.recent_containers_list.setVisible(False)

        except Exception as e:
            self.log_signal.emit(f"Error loading containers: {e}")
            self.recent_containers_label.setVisible(False)
            self.recent_containers_list.setVisible(False)

    def open_container_logs(self, item):
        """Show logs for the selected container"""
        container_name = item.data(Qt.ItemDataRole.UserRole)
        if container_name:
            try:
                result = subprocess.run(["docker", "logs", "--tail", "50", container_name],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.log_signal.emit(f"Logs for container '{container_name}':")
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            self.log_signal.emit(f"  {line}")
                    if result.stderr:
                        for line in result.stderr.split('\n'):
                            if line.strip():
                                self.log_signal.emit(f"  [ERR] {line}")
                else:
                    self.log_signal.emit(f"Failed to get logs for {container_name}: {result.stderr}")
            except Exception as e:
                self.log_signal.emit(f"Error getting container logs: {str(e)}")
