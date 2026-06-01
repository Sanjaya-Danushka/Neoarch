import subprocess
from threading import Thread
from PyQt6.QtWidgets import QMessageBox, QLabel, QComboBox, QVBoxLayout, QDialog, QDialogButtonBox
from PyQt6.QtCore import QTimer


def create_snapshot(app):
    if not app.cmd_exists("timeshift"):
        QMessageBox.warning(app, "Timeshift Not Found",
                            "Timeshift is not installed. Please install Timeshift to use snapshot functionality.\n\nInstall with: sudo pacman -S timeshift")
        return

    reply = QMessageBox.question(app, "Create Snapshot",
                                 "Create a system snapshot before proceeding with updates?\n\nThis will take some time.",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.Yes)
    if reply != QMessageBox.StandardButton.Yes:
        return

    app.loading_widget.setVisible(True)
    app.loading_widget.set_message("Creating snapshot...")
    app.loading_widget.start_animation()

    def do_create():
        try:
            timestamp = subprocess.run(["date", "+%Y-%m-%d_%H-%M-%S"], capture_output=True, text=True).stdout.strip()
            comment = f"NeoArch manual snapshot {timestamp}"
            result = subprocess.run(["pkexec", "timeshift", "--create", "--comments", comment],
                                    capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                app.show_message.emit("Snapshot", f"Snapshot created successfully: {comment}")
            else:
                app.show_message.emit("Snapshot", f"Failed to create snapshot: {result.stderr}")
        except Exception as e:
            app.show_message.emit("Snapshot", f"Error creating snapshot: {str(e)}")
        finally:
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass

    Thread(target=do_create, daemon=True).start()


def revert_to_snapshot(app):
    if not app.cmd_exists("timeshift"):
        QMessageBox.warning(app, "Timeshift Not Found",
                            "Timeshift is not installed. Please install Timeshift to use snapshot functionality.")
        return

    try:
        result = subprocess.run(["timeshift", "--list"], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            QMessageBox.warning(app, "No Snapshots", "No snapshots found or Timeshift error.")
            return

        snapshots = []
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if line.strip() and not line.startswith('Num') and not line.startswith('---'):
                parts = line.split()
                if len(parts) >= 4:
                    snapshots.append({
                        'num': parts[0],
                        'date': parts[1],
                        'time': parts[2],
                        'comment': ' '.join(parts[3:])
                    })

        if not snapshots:
            QMessageBox.information(app, "No Snapshots", "No snapshots available for restoration.")
            return

        dialog = QDialog(app)
        dialog.setWindowTitle("Select Snapshot to Restore")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select a snapshot to restore the system to:"))

        combo = QComboBox()
        for snap in snapshots:
            combo.addItem(f"{snap['date']} {snap['time']} - {snap['comment']}", snap['num'])
        layout.addWidget(combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_num = combo.currentData()
            if selected_num:
                restore_snapshot(app, selected_num)

    except Exception as e:
        QMessageBox.warning(app, "Error", f"Failed to list snapshots: {str(e)}")


def restore_snapshot(app, snapshot_num):
    reply = QMessageBox.warning(app, "Confirm Restoration",
                                f"This will restore your system to snapshot #{snapshot_num}.\n\n"
                                "The system will reboot after restoration.\n\n"
                                "Are you sure you want to proceed?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        return

    app.loading_widget.setVisible(True)
    app.loading_widget.set_message("Restoring snapshot...")
    app.loading_widget.start_animation()

    def do_restore():
        try:
            result = subprocess.run(["pkexec", "timeshift", "--restore", "--snapshot", snapshot_num],
                                    capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                app.show_message.emit("Snapshot", "Snapshot restoration initiated. System will reboot.")
                QTimer.singleShot(3000, lambda: subprocess.run(["pkexec", "reboot"]))
            else:
                app.show_message.emit("Snapshot", f"Failed to restore snapshot: {result.stderr}")
        except Exception as e:
            app.show_message.emit("Snapshot", f"Error restoring snapshot: {str(e)}")
        finally:
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass

    Thread(target=do_restore, daemon=True).start()


def delete_snapshots(app):
    if not app.cmd_exists("timeshift"):
        QMessageBox.warning(app, "Timeshift Not Found",
                            "Timeshift is not installed.")
        return

    reply = QMessageBox.question(app, "Delete Snapshots",
                                 "This will delete old snapshots to free up disk space.\n\n"
                                 "Keep only the 2 most recent snapshots?\n\n"
                                 "This action cannot be undone.",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        return

    app.loading_widget.setVisible(True)
    app.loading_widget.set_message("Deleting old snapshots...")
    app.loading_widget.start_animation()

    def do_delete():
        try:
            result = subprocess.run(["pkexec", "timeshift", "--delete-all", "--skip", "2"],
                                    capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                app.show_message.emit("Snapshot", "Old snapshots deleted successfully")
            else:
                app.show_message.emit("Snapshot", f"Failed to delete snapshots: {result.stderr}")
        except Exception as e:
            app.show_message.emit("Snapshot", f"Error deleting snapshots: {str(e)}")
        finally:
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass

    Thread(target=do_delete, daemon=True).start()
