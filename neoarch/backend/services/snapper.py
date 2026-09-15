"""Snapper (BTRFS) snapshot management services.

Companion to the Timeshift integration: operates on snapper configs
located under /etc/snapper/configs (BTRFS only) and exposes the same
create / list / revert / delete workflow, plus optional system-wide
pacman hooks so every update transaction captures snapshots.

Snapshots are only meaningful on BTRFS; snapper_supported() returns
False otherwise so callers can present a sensible message.
"""

import os
import shutil
import subprocess
from pathlib import Path
from threading import Thread

from PyQt6.QtWidgets import QMessageBox, QLabel, QComboBox, QVBoxLayout, QDialog, QDialogButtonBox

from neoarch.backend.services.backup import (
    get_filesystem_type, _btrfs_root_subvolume)
from neoarch.backend.services.snapshot import (
    run_auth_cmd, acquire_snapshot_op, release_snapshot_op,
    kill_stale_snapshot_procs)
from neoarch.backend.services.i18n import _

__all__ = [
    "snapper_supported", "snapper_available_configs", "default_config",
    "parse_snapshot_list", "create_snapshot", "revert_to_snapshot",
    "restore_snapshot", "delete_snapshots", "pre_update_snapshot",
    "install_pacman_hooks", "remove_pacman_hooks",
]


def _cancelled(app):
    """Emit + report a cancellation outcome in the snapshots channel."""
    _emit_progress(app, "error", _("Operation cancelled."))
    _report(app, _("Snapshot"), _("Operation cancelled."), "error", "errors")


def _busy_rejected(app):
    """Emit + report when a snapshot op is refused (one at a time)."""
    _emit_progress(app, "error",
                   _("Another snapshot operation is already running."))
    _report(app, _("Snapshot"),
            _("Another snapshot operation is already running."),
            "error", "errors")


def _report(app, title, text, level="info", event="install"):
    """Report a snapshot operation result via toast/desktop channels.

    Always marshals onto the GUI thread via ``app.ui_call`` so worker
    threads never touch Qt widgets — Qt6 calls ``qFatal`` (SIGABRT)
    when it detects cross-thread widget access and the UI freezes.
    Falls back to the blocking message dialog in tests / bare apps.
    """
    def _dispatch():
        notify = getattr(app, "_notify", None)
        if callable(notify):
            try:
                notify(title, text, level, event)
                return
            except Exception:
                pass
        try:
            app.show_message.emit(title, text)
        except Exception:
            pass
    ui_call = getattr(app, "ui_call", None)
    if ui_call is not None and hasattr(ui_call, "emit"):
        try:
            ui_call.emit(_dispatch)
            return
        except Exception:
            pass
    _dispatch()


def _emit_progress(app, state, detail):
    """Forward an in-tab progress event when the app exposes the signal."""
    signal = getattr(app, "snapshot_progress", None)
    if signal is not None and hasattr(signal, "emit"):
        try:
            signal.emit(state, detail)
        except Exception:
            pass

SNAPPER_CONFIGS_DIR = Path("/etc/snapper/configs")
HOOKS_DIR = Path("/etc/pacman.d/hooks")
HOOK_PRE = HOOKS_DIR / "neoarch-snapper-pre.hook"
HOOK_POST = HOOKS_DIR / "neoarch-snapper-post.hook"

_HOOK_PRE_CONTENT = """\
[Trigger]
Operation = Upgrade
Operation = Install
Operation = Remove
Type = Path
Target = /

[Action]
Description = NeoArch snapshot before transaction
When = PreTransaction
Exec = /usr/bin/snapper create --config {cfg} --description "NeoArch pre-update snapshot"
"""

_HOOK_POST_CONTENT = """\
[Trigger]
Operation = Upgrade
Operation = Install
Operation = Remove
Type = Path
Target = /

[Action]
Description = NeoArch snapshot after transaction
When = PostTransaction
Exec = /usr/bin/snapper create --config {cfg} --description "NeoArch post-update snapshot"
"""


def _snapper_bin():
    return shutil.which("snapper") or "snapper"


def snapper_available_configs():
    """Return configured snapper config names (empty when none)."""
    try:
        if not SNAPPER_CONFIGS_DIR.is_dir():
            return []
        return sorted(
            p.name for p in SNAPPER_CONFIGS_DIR.iterdir()
            if p.is_file() and not p.name.startswith("."))
    except Exception:
        return []


def default_config():
    """Pick the snapper config to operate on."""
    configs = snapper_available_configs()
    if not configs:
        return None
    if "root" in configs:
        return "root"
    return configs[0]


def snapper_supported():
    """True when the root fs is BTRFS, the binary exists and a config is set."""
    if get_filesystem_type() != "btrfs":
        return False
    if not shutil.which("snapper"):
        return False
    if _btrfs_root_subvolume() is None:
        return False
    return default_config() is not None


def parse_snapshot_list(stdout: str):
    """Parse `snapper list` output into snapshot records.

    Records include numeric snapshots only (the 'current' line, num 0,
    is skipped). Description may contain spaces on the snapper side.
    """
    snapshots = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        num = parts[0]
        if not num.isdigit():
            continue
        snapshots.append({
            "num": int(num),
            "type": parts[1],
            "date": parts[3] if len(parts) > 3 else "",
            "description": " ".join(p for p in parts[6:] if p),
        })
    return snapshots


def _list_snapshots(cfg):
    """Return parsed snapshot records for a config ([] on failure)."""
    try:
        result = subprocess.run(
            [_snapper_bin(), "-c", cfg, "list"],
            capture_output=True, text=True, timeout=60, check=False)
        if result.returncode != 0:
            return []
        return [s for s in parse_snapshot_list(result.stdout) if s["num"] > 0]
    except Exception:
        return []


def _loading(app, on, message=None):
    def _apply():
        try:
            if on:
                app.loading_widget.setVisible(True)
                app.loading_widget.set_message(message)
                app.loading_widget.start_animation()
            else:
                app.loading_widget.stop_animation()
                app.loading_widget.setVisible(False)
        except Exception:
            pass
    ui_call = getattr(app, "ui_call", None)
    if ui_call is not None and hasattr(ui_call, "emit"):
        try:
            ui_call.emit(_apply)
            return
        except Exception:
            pass
    _apply()


# ── UI-facing operations (mirror the timeshift service) ─────────────

def create_snapshot(app):
    """Create a new snapper snapshot."""
    cfg = default_config()
    if not cfg or not snapper_supported():
        QMessageBox.warning(
            app, _("Snapper Not Available"),
            _("Snapper needs a BTRFS filesystem, the 'snapper' tool and a"
              " configuration. Create one with: sudo snapper create-config /"))
        return
    reply = QMessageBox.question(
        app, _("Create Snapshot"),
        _("Create a system snapshot before proceeding?\n\n"
          "This will take some time."),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes)
    if reply != QMessageBox.StandardButton.Yes:
        return
    _loading(app, True, _("Creating snapshot..."))

    def do_create():
        if not acquire_snapshot_op():
            _busy_rejected(app)
            return
        try:
            kill_stale_snapshot_procs()
            timestamp = subprocess.run(
                [shutil.which("date") or "date", "+%Y-%m-%d_%H-%M-%S"],
                capture_output=True, text=True, check=False).stdout.strip()
            comment = _("NeoArch manual snapshot {ts}").format(ts=timestamp)
            _emit_progress(app, "busy", _("Creating snapshot..."))
            result = run_auth_cmd(
                [_snapper_bin(), "-c", cfg, "create",
                 "--description", comment, "--type", "single"], timeout=300)
            if result.returncode is None:
                _cancelled(app)
            elif result.returncode == 0:
                _emit_progress(
                    app, "done",
                    _("Snapshot created successfully: {comment}").format(comment=comment))
                _report(
                    app, _("Snapshot"),
                    _("Snapshot created successfully: {comment}").format(comment=comment),
                    "success")
            else:
                app.log(f"Snapper create failed "
                        f"(rc={result.returncode}): {result.stderr}")
                _emit_progress(
                    app, "error",
                    _("Failed to create snapshot: {err}").format(err=result.stderr))
                _report(
                    app, _("Snapshot"),
                    _("Failed to create snapshot: {err}").format(err=result.stderr),
                    "error", "errors")
        except Exception as e:
            _emit_progress(app, "error",
                           _("Error creating snapshot: {err}").format(err=str(e)))
            _report(app, _("Snapshot"),
                    _("Error creating snapshot: {err}").format(err=str(e)),
                    "error", "errors")
        finally:
            release_snapshot_op()
            _loading(app, False)

    Thread(target=do_create, daemon=True).start()


def revert_to_snapshot(app):
    """Show a dialog to select and restore a snapper snapshot."""
    cfg = default_config()
    if not cfg:
        QMessageBox.warning(app, _("Snapper Not Available"),
                            _("No snapper configuration found."))
        return
    if not acquire_snapshot_op():
        _busy_rejected(app)
        return
    _emit_progress(app, "busy", _("Loading snapshots..."))

    def do_list():
        try:
            kill_stale_snapshot_procs()
            snaps = _list_snapshots(cfg)
        except Exception as e:
            release_snapshot_op()
            _emit_progress(app, "error",
                           _("Failed to list snapshots: {err}").format(err=str(e)))
            _report(app, _("Snapshot"),
                    _("Failed to list snapshots: {err}").format(err=str(e)),
                    "error", "errors")
            return
        release_snapshot_op()
        _emit_progress(app, "done", "")
        if not snaps:
            app.ui_call.emit(lambda: QMessageBox.information(
                app, _("No Snapshots"), _("No snapshots available for restoration.")))
            return
        listed = list(snaps)
        app.ui_call.emit(lambda: _prompt_snapper_restore(app, listed))

    Thread(target=do_list, daemon=True).start()


def _prompt_snapper_restore(app, snapshots):
    """Show the (modal) restore picker for snapper on the UI thread."""
    if not snapshots:
        QMessageBox.information(app, _("No Snapshots"),
                                _("No snapshots available for restoration."))
        return
    dialog = QDialog(app)
    dialog.setWindowTitle(_("Select Snapshot to Restore"))
    dialog.setModal(True)
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel(_("Select a snapshot to restore the system to:")))
    combo = QComboBox()
    for snap in snapshots:
        label = snap["date"]
        if snap["description"]:
            label += f" - {snap['description']}"
        combo.addItem(label, snap["num"])
    layout.addWidget(combo)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        selected_num = combo.currentData()
        if selected_num:
            restore_snapshot(app, selected_num)


def restore_snapshot(app, snapshot_num):
    """Roll the system back to a specific snapper snapshot."""
    cfg = default_config() or "root"
    reply = QMessageBox.warning(
        app, _("Confirm Restoration"),
        _("This will roll back the system to snapper snapshot #{num}.\n\n"
          "Snapper switches the default subvolume; a reboot is required.\n\n"
          "Are you sure you want to proceed?").format(num=snapshot_num),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        return
    _loading(app, True, _("Restoring snapshot..."))

    def do_restore():
        if not acquire_snapshot_op():
            _busy_rejected(app)
            return
        try:
            kill_stale_snapshot_procs()
            _emit_progress(app, "busy", _("Restoring snapshot..."))
            result = run_auth_cmd(
                [_snapper_bin(), "-c", cfg, "rollback", str(snapshot_num)],
                timeout=600)
            if result.returncode is None:
                _cancelled(app)
            elif result.returncode == 0:
                _emit_progress(
                    app, "done",
                    _("Rollback initiated for snapshot #{num}. Reboot to"
                      " complete.").format(num=snapshot_num))
                _report(
                    app, _("Snapshot"),
                    _("Rollback initiated for snapshot #{num}. Reboot to"
                      " complete.").format(num=snapshot_num))
            else:
                _emit_progress(
                    app, "error",
                    _("Failed to restore snapshot: {err}").format(err=result.stderr))
                _report(
                    app, _("Snapshot"),
                    _("Failed to restore snapshot: {err}").format(err=result.stderr),
                    "error", "errors")
        except Exception as e:
            _emit_progress(app, "error",
                           _("Error restoring snapshot: {err}").format(err=str(e)))
            _report(app, _("Snapshot"),
                    _("Error restoring snapshot: {err}").format(err=str(e)),
                    "error", "errors")
        finally:
            release_snapshot_op()
            _loading(app, False)

    Thread(target=do_restore, daemon=True).start()


def delete_snapshots(app):
    """Delete old snapper snapshots, keeping the 2 most recent."""
    cfg = default_config()
    if not cfg:
        QMessageBox.warning(app, _("Snapper Not Available"),
                            _("No snapper configuration found."))
        return
    reply = QMessageBox.question(
        app, _("Delete Snapshots"),
        _("This will delete old snapshots to free up disk space.\n\n"
          "Keep only the 2 most recent snapshots?\n\n"
          "This action cannot be undone."),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        return
    _loading(app, True, _("Deleting old snapshots..."))

    def do_delete():
        if not acquire_snapshot_op():
            _busy_rejected(app)
            return
        try:
            kill_stale_snapshot_procs()
            snaps = _list_snapshots(cfg)
            old = [s["num"] for s in snaps[:-2]]
            if not old:
                _emit_progress(app, "done",
                               _("Nothing to delete — 2 or fewer snapshots."))
                _report(app, _("Snapshot"),
                        _("Nothing to delete — 2 or fewer snapshots."))
                return
            _emit_progress(app, "busy", _("Deleting old snapshots..."))
            result = run_auth_cmd(
                [_snapper_bin(), "-c", cfg, "delete"] + [str(n) for n in old],
                timeout=300)
            if result.returncode is None:
                _cancelled(app)
            elif result.returncode == 0:
                _emit_progress(app, "done",
                               _("Old snapshots deleted successfully"))
                _report(app, _("Snapshot"),
                        _("Old snapshots deleted successfully"), "success")
            else:
                _emit_progress(
                    app, "error",
                    _("Failed to delete snapshots: {err}").format(err=result.stderr))
                _report(
                    app, _("Snapshot"),
                    _("Failed to delete snapshots: {err}").format(err=result.stderr),
                    "error", "errors")
        except Exception as e:
            _emit_progress(app, "error",
                           _("Error deleting snapshots: {err}").format(err=str(e)))
            _report(app, _("Snapshot"),
                    _("Error deleting snapshots: {err}").format(err=str(e)),
                    "error", "errors")
        finally:
            release_snapshot_op()
            _loading(app, False)

    Thread(target=do_delete, daemon=True).start()


# ── Automatic update integration ─────────────────────────────────────

def pre_update_snapshot(app):
    """Clean up old snapshots (keep 2) and create a pre-update snapshot."""
    cfg = default_config()
    if not cfg:
        app.log("Auto-update: snapper not configured, skipping snapshot")
        return
    if not acquire_snapshot_op():
        app.log("Auto-update: snapshot already running, skipping")
        _emit_progress(app, "error",
                       _("Another snapshot operation is already running."))
        return
    try:
        kill_stale_snapshot_procs()
        snaps = _list_snapshots(cfg)
        old = [s["num"] for s in snaps[:-2]]
        if old:
            result = run_auth_cmd(
                [_snapper_bin(), "-c", cfg, "delete"] + [str(n) for n in old],
                timeout=300)
            if result.returncode is None:
                app.log("Auto-update: cleanup cancelled")
            elif result.returncode == 0:
                app.log("Auto-update: Cleaned up old snapper snapshots "
                        "(kept latest 2)")
            else:
                app.log(f"Auto-update: Failed to clean up snapper snapshots: "
                        f"{result.stderr}")
    except Exception as e:
        app.log(f"Auto-update: Error checking snapper snapshots: {e}")

    timestamp = subprocess.run(
        [shutil.which("date") or "date", "+%Y-%m-%d_%H-%M-%S"],
        capture_output=True, text=True, check=False).stdout.strip()
    comment = f"NeoArch pre-update snapshot {timestamp}"
    _emit_progress(app, "busy", _("Creating pre-update snapshot..."))
    try:
        result = run_auth_cmd(
            [_snapper_bin(), "-c", cfg, "create",
             "--description", comment, "--type", "single"], timeout=300)
        if result.returncode is None:
            app.log("Auto-update: Pre-update snapshot cancelled")
            _emit_progress(app, "error", _("Operation cancelled."))
        elif result.returncode == 0:
            app.log(f"Auto-update: Pre-update snapshot created: {comment}")
            _emit_progress(
                app, "done",
                _("Pre-update snapshot created: {comment}").format(comment=comment))
            _report(
                app, _("Snapshot"),
                _("Pre-update snapshot created: {comment}").format(comment=comment),
                "success")
        else:
            app.log(f"Auto-update: Failed to create pre-update snapshot: "
                    f"{result.stderr}")
            _emit_progress(app, "error",
                           _("Failed to create pre-update snapshot: {err}")
                           .format(err=result.stderr))
    except Exception as e:
        app.log(f"Auto-update: Pre-update snapshot creation failed: {e}")
        _emit_progress(app, "error",
                       _("Error creating pre-update snapshot: {err}")
                       .format(err=str(e)))
    finally:
        release_snapshot_op()


# ── System-wide pacman hooks ─────────────────────────────────────────

def install_pacman_hooks(app):
    """Install pacman Alpm hooks for update-time snapper snapshots."""
    if not snapper_supported():
        QMessageBox.warning(
            app, _("Snapper Not Available"),
            _("Snapper needs a BTRFS filesystem and a configuration."))
        return
    cfg = default_config() or "root"

    def _do():
        if not acquire_snapshot_op():
            _busy_rejected(app)
            return
        try:
            kill_stale_snapshot_procs()
            _emit_progress(app, "busy", _("Installing update-time hooks..."))
            mkdir = run_auth_cmd(["mkdir", "-p", str(HOOKS_DIR)], timeout=30)
            if mkdir.returncode is None:
                _cancelled(app)
                return
            for path, content in ((HOOK_PRE, _HOOK_PRE_CONTENT),
                                  (HOOK_POST, _HOOK_POST_CONTENT)):
                r = run_auth_cmd(["tee", str(path)], timeout=30,
                                 input=content.format(cfg=cfg))
                if r.returncode is None:
                    _cancelled(app)
                    return
                if r.returncode != 0:
                    _emit_progress(
                        app, "error",
                        _("Failed to install pacman hook: {path}"
                          " - {err}").format(path=path, err=r.stderr))
                    _report(
                        app, _("Snapshot"),
                        _("Failed to install pacman hook: {path}"
                          " - {err}").format(path=path, err=r.stderr),
                        "error", "errors")
                    return
            _emit_progress(
                app, "done",
                _("Pacman hooks installed — every system update will now"
                  " capture Snapper snapshots."))
            _report(
                app, _("Snapshot"),
                _("Pacman hooks installed — every system update will now"
                  " capture Snapper snapshots."), "success")
        except Exception as e:
            _emit_progress(app, "error",
                           _("Error installing pacman hooks: {err}").format(err=str(e)))
            _report(app, _("Snapshot"),
                    _("Error installing pacman hooks: {err}").format(err=str(e)),
                    "error", "errors")
        finally:
            release_snapshot_op()

    Thread(target=_do, daemon=True).start()


def remove_pacman_hooks(app):
    """Remove the NeoArch pacman Alpm hooks."""
    def _do():
        if not acquire_snapshot_op():
            _busy_rejected(app)
            return
        try:
            kill_stale_snapshot_procs()
            _emit_progress(app, "busy", _("Removing update-time hooks..."))
            result = run_auth_cmd(
                ["rm", "-f", str(HOOK_PRE), str(HOOK_POST)], timeout=60)
            if result.returncode is None:
                _cancelled(app)
            elif result.returncode == 0:
                _emit_progress(app, "done", _("Pacman hooks removed."))
                _report(app, _("Snapshot"),
                        _("Pacman hooks removed."), "success")
            else:
                _emit_progress(
                    app, "error",
                    _("Failed to remove pacman hooks: {err}").format(err=result.stderr))
                _report(
                    app, _("Snapshot"),
                    _("Failed to remove pacman hooks: {err}").format(err=result.stderr),
                    "error", "errors")
        except Exception as e:
            _emit_progress(app, "error",
                           _("Error removing pacman hooks: {err}").format(err=str(e)))
            _report(app, _("Snapshot"),
                    _("Error removing pacman hooks: {err}").format(err=str(e)),
                    "error", "errors")
        finally:
            release_snapshot_op()

    Thread(target=_do, daemon=True).start()