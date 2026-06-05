"""Docker container management component for NeoArch.

Provides UI and backend for pulling, running, listing, stopping, and
cleaning Docker containers with advanced options for ports, volumes,
environment variables, GPU passthrough, and restart policies.
"""

import os
import shutil
import subprocess
from threading import Thread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit, QMessageBox,
    QPlainTextEdit, QComboBox, QCheckBox, QMenu, QAbstractItemView,
    QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QObject, QTimer, QPoint
from PyQt6.QtGui import QCursor

from neoarch.resources.paths import ICONS_DIR
from neoarch.frontend.components.feature_card import FeatureCard

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
        self._container_count = 0
        self.create_docker_section()

    def create_docker_section(self):
        """Create and add the Docker section UI to the sources layout."""
        self.docker_section = QWidget()
        self.docker_section.setObjectName("dockerSectionWrapper")
        wrapper_layout = QVBoxLayout(self.docker_section)
        wrapper_layout.setContentsMargins(0, 6, 0, 0)
        wrapper_layout.setSpacing(4)

        self._card = FeatureCard()
        docker_icon = os.path.join(str(ICONS_DIR), "discover", "docker.svg")
        self._update_badge()
        self._card.build_header(docker_icon, "Docker Containers", self._container_count or None)
        self._card.build_primary_action("Run Container", self.install_from_docker)
        self._card.build_action_grid([
            ("Images", "list", self.list_docker_images),
            ("Stop", "stop", self.show_stop_menu),
            ("Shell", "shell", self.show_shell_menu),
            ("Clean", "clean", self.clean_docker_containers),
        ])
        wrapper_layout.addWidget(self._card)

        self.recent_containers_label = QLabel("Containers")
        self.recent_containers_label.setObjectName("dockerRecentLabel")
        self.recent_containers_label.setStyleSheet("""
            QLabel#dockerRecentLabel {
                color: #5C5E66;
                font-size: 9px;
                font-weight: 500;
                padding: 2px 14px 0 14px;
                background: transparent;
                border: none;
            }
        """)
        wrapper_layout.addWidget(self.recent_containers_label)

        self.recent_containers_list = QListWidget()
        self.recent_containers_list.setObjectName("dockerRecentList")
        self.recent_containers_list.itemDoubleClicked.connect(self.open_container_logs)
        self.recent_containers_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.recent_containers_list.customContextMenuRequested.connect(self.show_container_menu)
        try:
            self.recent_containers_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        except Exception:
            pass
        self.recent_containers_list.setVisible(False)
        self.recent_containers_list.setStyleSheet("""
            QListWidget#dockerRecentList {
                background-color: transparent;
                border: none;
                color: #8B8D97;
                font-size: 10px;
                max-height: 72px;
                padding: 0 14px 4px 14px;
            }
            QListWidget#dockerRecentList::item {
                padding: 3px 6px;
                border-radius: 4px;
            }
            QListWidget#dockerRecentList::item:hover {
                background-color: rgba(255, 255, 255, 0.04);
                color: #EDEDEF;
            }
            QListWidget#dockerRecentList::item:selected {
                background-color: rgba(0, 191, 174, 0.12);
                color: #00BFAE;
            }
        """)
        wrapper_layout.addWidget(self.recent_containers_list)

        self.sources_layout.addWidget(self.docker_section)
        self.load_containers(include_all=True)

    def _update_badge(self):
        """Count active containers for the header badge."""
        try:
            result = subprocess.run(
                ["docker", "ps", "-q"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                self._container_count = len(result.stdout.strip().split('\n'))
            else:
                self._container_count = 0
        except Exception:
            self._container_count = 0

    def show_shell_menu(self):
        """Show a menu to select a container and open a shell."""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #2A2D33; color: #F0F0F0; border: 1px solid rgba(0,191,174,0.3); }
            QMenu::item:selected { background-color: rgba(0,191,174,0.2); }
        """)
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                names = result.stdout.strip().split('\n')
                for name in names:
                    action = menu.addAction(name)
                    action.triggered.connect(lambda checked=False, n=name: self.open_container_shell(n))
            else:
                menu.addAction("No running containers").setEnabled(False)
        except Exception:
            menu.addAction("No running containers").setEnabled(False)
        menu.exec(QCursor.pos())

    def install_from_docker(self):
        """Open the advanced Docker run dialog."""
        self.show_advanced_run_dialog()

    def show_advanced_run_dialog(self, prefill_image=None):
        """Show the advanced Docker run dialog with full options."""
        import shlex
        dialog = QDialog()
        dialog.setWindowTitle("Run Container from Docker Image")
        dialog.setModal(True)
        dialog.setMinimumWidth(480)
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
        layout.setSpacing(12)

        title = QLabel("Run Container from Docker Image")
        title.setStyleSheet("""
            font-size: 15px;
            font-weight: 600;
            color: #EDEDEF;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title)

        image_input = QLineEdit()
        image_input.setPlaceholderText("nginx:latest or user/app:v1.0")
        if prefill_image:
            image_input.setText(prefill_image)
        image_input.setStyleSheet("""
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
            }
        """)
        def _input_style():
            return """
                QLineEdit {
                    background-color: rgba(28, 30, 36, 0.9);
                    color: #EDEDEF;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 12px;
                    selection-background-color: rgba(0, 191, 174, 0.3);
                }
                QLineEdit:focus {
                    border-color: rgba(0, 191, 174, 0.4);
                }
            """

        def _plain_style():
            return """
                QPlainTextEdit {
                    background-color: rgba(28, 30, 36, 0.9);
                    color: #EDEDEF;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 6px 8px;
                    font-size: 12px;
                    selection-background-color: rgba(0, 191, 174, 0.3);
                }
                QPlainTextEdit:focus {
                    border-color: rgba(0, 191, 174, 0.4);
                }
            """

        def _field_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #8B8D97; font-size: 11px; font-weight: 500; background: transparent; border: none; margin-top: 4px;")
            return lbl

        layout.addWidget(_field_label("Image"))
        layout.addWidget(image_input)

        name_input = QLineEdit()
        name_input.setPlaceholderText("optional container name")
        name_input.setStyleSheet(_input_style())
        layout.addWidget(_field_label("Name"))
        layout.addWidget(name_input)

        ports_edit = QPlainTextEdit()
        ports_edit.setPlaceholderText("8080:80\n127.0.0.1:2222:22/tcp")
        ports_edit.setFixedHeight(60)
        ports_edit.setStyleSheet(_plain_style())
        layout.addWidget(_field_label("Ports (host:container[/proto])"))
        layout.addWidget(ports_edit)

        vols_edit = QPlainTextEdit()
        vols_edit.setPlaceholderText("/host/path:/container/path:ro\n~/data:/var/lib/data:rw")
        vols_edit.setFixedHeight(60)
        vols_edit.setStyleSheet(_plain_style())
        layout.addWidget(_field_label("Volumes (host:container[:ro|rw])"))
        layout.addWidget(vols_edit)

        env_edit = QPlainTextEdit()
        env_edit.setPlaceholderText("KEY=value\nMODE=prod")
        env_edit.setFixedHeight(60)
        env_edit.setStyleSheet(_plain_style())
        layout.addWidget(_field_label("Environment (KEY=VALUE)"))
        layout.addWidget(env_edit)

        opt_row = QHBoxLayout()
        opt_row.setSpacing(8)
        restart_combo = QComboBox()
        restart_combo.addItems(["no", "always", "unless-stopped", "on-failure"])
        restart_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(28, 30, 36, 0.9);
                color: #EDEDEF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 11px;
                min-width: 100px;
            }
            QComboBox:focus {
                border-color: rgba(0, 191, 174, 0.4);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(22, 23, 26, 0.98);
                color: #EDEDEF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                selection-background-color: rgba(0, 191, 174, 0.15);
                outline: none;
            }
        """)
        detach_chk = QCheckBox("Detach")
        detach_chk.setChecked(True)
        detach_chk.setStyleSheet("""
            QCheckBox {
                color: #C9C9CD;
                font-size: 11px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1.5px solid #5C5E66;
                background-color: rgba(28, 30, 36, 0.9);
            }
            QCheckBox::indicator:checked {
                background-color: #00BFAE;
                border-color: #00BFAE;
            }
            QCheckBox::indicator:hover {
                border-color: #00BFAE;
            }
        """)
        priv_chk = QCheckBox("Privileged")
        priv_chk.setStyleSheet(detach_chk.styleSheet())
        gpu_chk = QCheckBox("GPU")
        gpu_chk.setStyleSheet(detach_chk.styleSheet())
        opt_row.addWidget(_field_label("Restart"))
        opt_row.addWidget(restart_combo)
        opt_row.addStretch()
        opt_row.addWidget(detach_chk)
        opt_row.addWidget(priv_chk)
        opt_row.addWidget(gpu_chk)
        layout.addLayout(opt_row)

        cmd_input = QLineEdit()
        cmd_input.setPlaceholderText("optional command and args")
        cmd_input.setStyleSheet(_input_style())
        layout.addWidget(_field_label("Command"))
        layout.addWidget(cmd_input)

        preview = QPlainTextEdit()
        preview.setReadOnly(True)
        preview.setFixedHeight(64)
        preview.setStyleSheet("""
            QPlainTextEdit {
                background-color: rgba(14, 14, 16, 0.8);
                color: #5C5E66;
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 8px;
                padding: 6px 8px;
                font-size: 11px;
                font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
            }
        """)
        layout.addWidget(_field_label("Preview"))
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
        btn_row.addWidget(cancel_btn)
        run_btn = QPushButton("Run Container")
        run_btn.setDefault(True)
        run_btn.setFixedHeight(34)

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
        run_btn.setStyleSheet("""
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

    def list_docker_images(self):
        """Show Docker images as styled cards with contextual Run/Stop button."""
        dialog = QDialog()
        dialog.setWindowTitle("Docker Images")
        dialog.setMinimumSize(440, 320)
        dialog.setStyleSheet("""
            QDialog {
                background-color: rgba(18, 19, 22, 0.98);
                color: #EDEDEF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 10, 10, 6)
        title = QLabel("Docker Images")
        title.setStyleSheet("color: #EDEDEF; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        hl.addWidget(title)
        hl.addStretch()
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.02);
                width: 5px; border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.08);
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent; border: none;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(12, 2, 12, 12)
        scroll_layout.setSpacing(3)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        try:
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.ID}}"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    parts = line.split('\t')
                    if len(parts) >= 3 and parts[0] and parts[0] != "<none>":
                        card = self._create_image_card(parts[0], parts[1],
                            parts[2] if len(parts) > 2 else "",
                            parts[3] if len(parts) > 3 else "")
                        scroll_layout.addWidget(card)
            else:
                empty = QLabel("No Docker images found")
                empty.setStyleSheet("color: #5C5E66; font-size: 12px; background: transparent; border: none; padding: 24px;")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                scroll_layout.addWidget(empty)
        except Exception as e:
            err = QLabel(f"Error: {e}")
            err.setStyleSheet("color: #E06C75; font-size: 12px; background: transparent; border: none; padding: 24px;")
            scroll_layout.addWidget(err)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        dialog.exec()

    def _create_image_card(self, repo, tag, size, image_id):
        """Styled card for one image with a single contextual Run/Stop button."""
        image_ref = f"{repo}:{tag}"

        has_running = False
        try:
            r = subprocess.run(
                ["docker", "ps", "-q", "--filter", f"ancestor={image_ref}"],
                capture_output=True, text=True, timeout=10,
            )
            has_running = r.returncode == 0 and r.stdout.strip() != ""
        except Exception:
            pass

        card = QWidget()
        card.setObjectName("dockerImageCard")
        card.setFixedHeight(36)

        cl = QHBoxLayout(card)
        cl.setContentsMargins(10, 0, 6, 0)
        cl.setSpacing(8)

        name_lbl = QLabel(f"{repo}:{tag}")
        name_lbl.setStyleSheet("color: #EDEDEF; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        cl.addWidget(name_lbl)

        meta_lbl = QLabel(size)
        meta_lbl.setStyleSheet("color: #5C5E66; font-size: 10px; background: transparent; border: none;")
        cl.addWidget(meta_lbl)
        cl.addStretch()

        if has_running:
            btn = QPushButton("Stop")
            btn.setFixedSize(48, 22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=image_ref: self._stop_containers_for_image(i))
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(224, 108, 117, 0.12);
                    color: #E06C75;
                    border: 1px solid rgba(224, 108, 117, 0.2);
                    border-radius: 5px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(224, 108, 117, 0.2);
                }
            """)
        else:
            btn = QPushButton("Run")
            btn.setFixedSize(48, 22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=image_ref: self.show_advanced_run_dialog(prefill_image=i))
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 191, 174, 0.1);
                    color: #00BFAE;
                    border: 1px solid rgba(0, 191, 174, 0.2);
                    border-radius: 5px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(0, 191, 174, 0.18);
                }
            """)
        cl.addWidget(btn)

        card.setStyleSheet("""
            QWidget#dockerImageCard {
                background-color: rgba(22, 23, 26, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 8px;
            }
            QWidget#dockerImageCard:hover {
                background-color: rgba(22, 23, 26, 0.7);
                border-color: rgba(255, 255, 255, 0.08);
            }
        """)
        return card

    def _stop_containers_for_image(self, image):
        """Stop all containers using the given image."""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"ancestor={image}", "--format", "{{.ID}}"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                containers = result.stdout.strip().split('\n')
                self.log_signal.emit(f"Stopping {len(containers)} container(s) from {image}...")
                for cid in containers:
                    subprocess.run(["docker", "stop", cid], capture_output=True, text=True, timeout=30)
                    self.log_signal.emit(f"Stopped container: {cid}")
                self.show_message.emit("Containers Stopped", f"Stopped {len(containers)} container(s)")
                self.load_containers(include_all=True)
            else:
                self.show_message.emit("No Containers", f"No containers found for image {image}")
        except Exception as e:
            self.log_signal.emit(f"Error stopping containers: {e}")

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
        terminals = ["kitty", "alacritty", "gnome-terminal", "konsole", "xterm"]
        term = None
        for t in terminals:
            if shutil.which(t):
                term = t
                break
        for shell in ["/bin/bash", "/bin/sh"]:
            try:
                if term == "gnome-terminal":
                    subprocess.Popen([term, "--", "bash", "-c",
                                      f"docker exec -it {cid} {shell}"])
                elif term:
                    subprocess.Popen([term, "-e", "docker", "exec", "-it", cid, shell])
                else:
                    subprocess.Popen(["docker", "exec", "-it", cid, shell])
                return
            except Exception:
                continue
        self.log_signal.emit("Failed to open shell: no shell or terminal available")

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
        self._update_badge()
        if hasattr(self, '_card') and self._card is not None:
            self._card.set_badge(self._container_count or None)

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
