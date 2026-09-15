"""Timeshift snapshot management services.

Provides system snapshot creation, restoration, listing, and deletion
via the Timeshift backup utility.
"""

import os
import shutil
import subprocess
import tempfile
import threading
import time
from threading import Thread
from PyQt6.QtWidgets import QMessageBox, QLabel, QComboBox, QVBoxLayout, QDialog, QDialogButtonBox
from neoarch.backend.auth import get_auth_command, get_askpass_env
from neoarch.backend.services.i18n import _

def _is_rooted():
    import os
    return hasattr(os, "geteuid") and os.geteuid() == 0


__all__ = ["create_snapshot", "revert_to_snapshot", "restore_snapshot",
           "delete_snapshots", "pre_update_snapshot",
           "run_auth_cmd", "request_snapshot_cancel", "clear_snapshot_cancel",
           "snapshot_op_active", "acquire_snapshot_op", "release_snapshot_op",
           "kill_stale_snapshot_procs"]


# ── Shared snapshot-operation state (Timeshift + Snapper) ──────────
#
# One busy flag serialises every snapshot operation so a second click
# (or a click right after reopening the app) can never spawn a second
# timeshift/snapper process and deadlock on its lock file. The cancel
# event lets the visible Cancel button terminate a running child. And
# kill_stale_snapshot_procs() clears orphaned processes (from a session
# that was killed mid-snapshot) which are the usual cause of the new
# process silently blocking forever.

_OP_LOCK = threading.Lock()
_OP_BUSY = False
_CANCEL_EVENT = threading.Event()


def snapshot_op_active():
    """Return True when a snapshot operation is currently running."""
    with _OP_LOCK:
        return _OP_BUSY


def acquire_snapshot_op():
    """Serialise snapshot operations. Returns True when acquired."""
    global _OP_BUSY
    with _OP_LOCK:
        if _OP_BUSY:
            return False
        _OP_BUSY = True
        return True


def release_snapshot_op():
    global _OP_BUSY
    with _OP_LOCK:
        _OP_BUSY = False


def request_snapshot_cancel():
    """Ask the running snapshot operation to abort (kills its subprocess)."""
    _CANCEL_EVENT.set()


def clear_snapshot_cancel():
    """Reset the cancel flag for a fresh operation."""
    _CANCEL_EVENT.clear()


def _group_leader_is_alive_timeshift(pgid):
    """True if the process-group leader is a live ``timeshift`` process.

    A manual backup's ``bash script.sh`` + ``rsync`` workers run in a
    separate process group whose leader is the original ``timeshift``
    invocation. When that leader is gone (app killed / cancel SIGKILLed
    it) the group is orphaned and its rsync keeps running for hours.
    """
    try:
        with open(f"/proc/{pgid}/cmdline", "rb") as f:
            cmd = f.read().replace(b"\x00", b" ").decode("utf-8", "replace")
    except Exception:
        return False
    return "timeshift" in cmd


def kill_stale_snapshot_procs():
    """Terminate orphaned timeshift/snapper processes from a dead session.

    When the app is killed mid-snapshot, its ``timeshift``/``snapper``
    children keep running (and keep their lock files). A new operation
    would then block on that stale lock for the full timeout — which the
    UI reads as an app freeze. We only touch processes whose command line
    carries a ``NeoArch`` snapshot comment, so a system-timeshift running
    on its own schedule is left alone.
    """
    import os as _os
    try:
        listing = subprocess.run(
            ["pgrep", "-af", "NeoArch"],
            capture_output=True, text=True, timeout=5, check=False)
    except Exception:
        return
    for line in (listing.stdout or "").splitlines():
        pid, sep, cmd = line.partition(" ")
        if not sep or not pid.isdigit():
            continue
        if ("timeshift" in cmd or "snapper" in cmd) and "NeoArch" in cmd:
            try:
                _os.kill(int(pid), 15)  # SIGTERM
            except Exception:
                pass

    # Orphaned manual-backup workers: the timeshift leader was killed
    # (crash / cancel) but its `bash script.sh` + `rsync` group outlived
    # it and keeps rsync-ing for hours. Kill any group whose leader is no
    # longer a live timeshift process. A scheduled system backup is
    # untouched because its leader (`timeshift --check --scripted`) is
    # alive and matches.
    try:
        listing = subprocess.run(
            ["pgrep", "-af", r"/tmp/timeshift-[^ ]*/script\.sh"],
            capture_output=True, text=True, timeout=5, check=False)
    except Exception:
        return
    seen = set()
    for line in (listing.stdout or "").splitlines():
        pid, sep, cmd = line.partition(" ")
        if not sep or not pid.isdigit():
            continue
        try:
            pgid = _os.getpgid(int(pid))
        except Exception:
            continue
        if pgid in seen:
            continue
        seen.add(pgid)
        if _group_leader_is_alive_timeshift(pgid):
            continue  # scheduled backup still running
        try:
            _os.killpg(pgid, 15)  # SIGTERM the orphaned group
        except Exception:
            pass


class _AuthResult:
    """Result of a (possibly cancelled) privileged command run."""

    __slots__ = ("returncode", "stdout", "stderr")

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run_auth_cmd(argv, timeout=300, input=None):
    """Run a privileged command while honouring the cancel request.

    Output is redirected to temporary files instead of pipes so a child
    that survives cancellation can never keep a pipe open against the
    app — teardown always finishes within a bounded time. The cancel
    event is polled every 0.2 s and terminates the whole process group
    (sudo + the tool + its children). Returns an _AuthResult; its
    ``returncode`` is ``None`` when the operation was cancelled, and
    ``-1`` with a ``[timeout]`` suffix on stderr when the deadline ran out.
    """
    clear_snapshot_cancel()
    out_file = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
    err_file = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
    deadline = time.monotonic() + timeout
    try:
        proc = subprocess.Popen(
            get_auth_command() + argv,
            stdout=out_file, stderr=err_file,
            stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
            text=True, env=get_askpass_env(), start_new_session=True)
        if input is not None:
            try:
                proc.stdin.write(input)
                proc.stdin.flush()
                proc.stdin.close()
            except Exception:
                try:
                    proc.stdin.close()
                except Exception:
                    pass
        returncode = None
        while True:
            returncode = proc.poll()
            if returncode is not None:
                break
            if _CANCEL_EVENT.is_set():
                _finish(proc, 15)
                break
            if time.monotonic() > deadline:
                _finish(proc, 9)
                break
            time.sleep(0.2)
        out_file.flush()
        err_file.flush()
        out_file.seek(0)
        err_file.seek(0)
        out = out_file.read()
        err = err_file.read()
    finally:
        try:
            out_file.close()
        except Exception:
            pass
        try:
            err_file.close()
        except Exception:
            pass
    if _CANCEL_EVENT.is_set():
        return _AuthResult(None, out or "", err or "")
    if returncode is None:
        return _AuthResult(-1, out or "", (err or "") + "\n[timeout]")
    return _AuthResult(returncode, out or "", err or "")


def _killpg(proc, sig):
    """Signal the whole process group (sudo + tool + its children).

    The group is owned by this user (``sudo`` runs setuid but its group
    contains the elevated ``timeshift``/``rsync`` workers), so a plain
    ``os.killpg`` from an unprivileged caller gets EPERM and nothing dies
    — the elevated workers keep running for hours afterwards. When the
    direct signal fails, re-send via ``sudo`` so the groups actually go
    away. Never signals anything outside the resolved group.
    """
    pgid = proc.pid
    try:
        os.killpg(pgid, sig)
        return
    except ProcessLookupError:
        return
    except Exception:
        pass
    if sig == 15:
        sig_name = "TERM"
    else:
        sig_name = str(sig)
    try:
        subprocess.run(
            get_auth_command() + ["kill", "-s", sig_name, "--", f"-{pgid}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=get_askpass_env(), timeout=10, check=False)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _finish(proc, sig):
    """Signal the group and reap the leader within a bounded time."""
    _killpg(proc, sig)
    try:
        proc.wait(timeout=5)
    except Exception:
        _killpg(proc, 9)
        try:
            proc.wait(timeout=5)
        except Exception:
            pass


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


def _system_timeshift_busy():
    """True when the system's scheduled hourly timeshift holds the lock."""
    try:
        r = subprocess.run(
            ["pgrep", "-af", r"timeshift --check --scripted"],
            capture_output=True, text=True, timeout=5, check=False)
    except Exception:
        return False
    return bool((r.stdout or "").strip())


class _TimeshiftBusy(Exception):
    """Raised when timeshift's lock is held (scheduled/manual backup)."""


_BUSY_MSG = _(
    "Timeshift is busy with another backup in progress "
    "(scheduled or manual). Try again after it finishes.")


def _report_busy(app):
    _emit_progress(app, "error", _BUSY_MSG)
    _report(app, _("Snapshot"), _BUSY_MSG, "error", "errors")


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


def _find_snapshot(comment):
    """Return the snapshot date whose --list entry matches comment, or None."""
    try:
        listing = subprocess.run(
            [shutil.which("timeshift") or "timeshift", "--list"],
            capture_output=True, text=True, timeout=30, check=False)
    except Exception:
        return None
    if listing.returncode != 0:
        return None
    text = (listing.stdout or "") + "\n" + (listing.stderr or "")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if comment in line:
            for prev in lines[max(0, i - 3): i]:
                fields = prev.split()
                if len(fields) >= 2 and fields[0].isdigit():
                    return f"{fields[1]} {fields[2]}"
    return None


def create_snapshot(app):
    """Create a new Timeshift system snapshot."""
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
        if not acquire_snapshot_op():
            _busy_rejected(app)
            return
        try:
            kill_stale_snapshot_procs()
            timestamp = subprocess.run([shutil.which("date") or "date", "+%Y-%m-%d_%H-%M-%S"], capture_output=True, text=True, check=False).stdout.strip()
            comment = f"NeoArch manual snapshot {timestamp}"
            _emit_progress(app, "busy", _("Creating snapshot..."))
            if _system_timeshift_busy():
                raise _TimeshiftBusy()
            result = run_auth_cmd(
                ["timeshift", "--create", "--comments", comment], timeout=300)
            if result.returncode is None:
                _cancelled(app)
            elif result.returncode == 0:
                # timeshift --create can report success without actually
                # producing a snapshot (bad config / silent failure), so
                # verify through --list before claiming success.
                created = _find_snapshot(comment)
                if created:
                    _emit_progress(
                        app, "done",
                        _("Snapshot created successfully: {date}")
                        .format(date=created))
                    _report(app, _("Snapshot"),
                            _("Snapshot created successfully: {date}")
                            .format(date=created), "success")
                else:
                    detail = (result.stdout or result.stderr or "").strip()
                    _emit_progress(
                        app, "error",
                        _("The snapshot did not appear in Timeshift's list."
                          "\nCommand output: {out}").format(
                              out=detail[-500:] or _("(empty)")))
                    _report(
                        app, _("Snapshot"),
                        _("The snapshot did not appear in Timeshift's list."
                          "\nCommand output: {out}").format(
                              out=detail[-500:] or _("(empty)")),
                        "error", "errors")
            else:
                app.log(f"Snapshot create failed "
                        f"(rc={result.returncode}): {result.stderr}")
                if "Another instance" in result.stderr:
                    _report_busy(app)
                else:
                    _emit_progress(app, "error",
                                   _("Failed to create snapshot: {err}").format(err=result.stderr))
                    _report(app, _("Snapshot"),
                            _("Failed to create snapshot: {err}").format(err=result.stderr),
                            "error", "errors")
        except _TimeshiftBusy:
            _report_busy(app)
        except Exception as e:
            _emit_progress(app, "error",
                           _("Error creating snapshot: {err}").format(err=str(e)))
            _report(app, _("Snapshot"),
                    _("Error creating snapshot: {err}").format(err=str(e)),
                    "error", "errors")
        finally:
            release_snapshot_op()
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass
    Thread(target=do_create, daemon=True).start()


def revert_to_snapshot(app):
    """Show dialog to select and restore a Timeshift snapshot."""
    if not app.cmd_exists("timeshift"):
        QMessageBox.warning(app, "Timeshift Not Found",
                            "Timeshift is not installed.")
        return
    if not acquire_snapshot_op():
        _busy_rejected(app)
        return
    _emit_progress(app, "busy", _("Loading snapshots..."))

    def do_list():
        try:
            kill_stale_snapshot_procs()
            result = subprocess.run(
                [shutil.which("timeshift") or "timeshift", "--list"],
                capture_output=True, text=True, timeout=30, check=False)
            if result.returncode != 0:
                raise RuntimeError(
                    (result.stderr or result.stdout or "").strip()
                    or _("Timeshift list failed"))
            snapshots = []
            for line in result.stdout.strip().split('\n'):
                if line.strip() and not line.startswith('Num') \
                        and not line.startswith('---'):
                    parts = line.split()
                    if len(parts) >= 4:
                        snapshots.append({
                            'num': parts[0],
                            'date': parts[1],
                            'time': parts[2],
                            'comment': ' '.join(parts[3:])
                        })
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
        if not snapshots:
            app.ui_call.emit(lambda: QMessageBox.information(
                app, "No Snapshots", "No snapshots available for restoration."))
            return
        listed = list(snapshots)
        app.ui_call.emit(lambda: _prompt_timeshift_restore(app, listed))

    Thread(target=do_list, daemon=True).start()


def _prompt_timeshift_restore(app, snapshots):
    """Show the (modal) restore picker run on the UI thread."""
    if not snapshots:
        QMessageBox.information(app, "No Snapshots",
                                "No snapshots available for restoration.")
        return
    dialog = QDialog(app)
    dialog.setWindowTitle("Select Snapshot to Restore")
    dialog.setModal(True)
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel("Select a snapshot to restore the system to:"))
    combo = QComboBox()
    for snap in snapshots:
        combo.addItem(f"{snap['date']} {snap['time']} - {snap['comment']}",
                      snap['num'])
    layout.addWidget(combo)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                               QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        selected_num = combo.currentData()
        if selected_num:
            restore_snapshot(app, selected_num)


def restore_snapshot(app, snapshot_num):
    """Restore the system to a specific Timeshift snapshot."""
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
        if not acquire_snapshot_op():
            _busy_rejected(app)
            return
        try:
            kill_stale_snapshot_procs()
            _emit_progress(app, "busy", _("Restoring snapshot..."))
            if _system_timeshift_busy():
                raise _TimeshiftBusy()
            result = run_auth_cmd(
                ["timeshift", "--restore", "--snapshot", snapshot_num],
                timeout=600)
            if result.returncode is None:
                _cancelled(app)
            elif result.returncode == 0:
                _emit_progress(app, "done",
                               _("Snapshot restoration initiated. System will reboot."))
                _report(app, _("Snapshot"),
                        _("Snapshot restoration initiated. System will reboot."),
                        "success")
                time.sleep(3)
                subprocess.run(
                    ["reboot"] if _is_rooted() else get_auth_command() + ["reboot"],
                    env=get_askpass_env(), check=False)
            else:
                if "Another instance" in result.stderr:
                    _report_busy(app)
                else:
                    _emit_progress(app, "error",
                                   _("Failed to restore snapshot: {err}").format(err=result.stderr))
                    _report(app, _("Snapshot"),
                            _("Failed to restore snapshot: {err}").format(err=result.stderr),
                            "error", "errors")
        except _TimeshiftBusy:
            _report_busy(app)
        except Exception as e:
            _emit_progress(app, "error",
                           _("Error restoring snapshot: {err}").format(err=str(e)))
            _report(app, _("Snapshot"),
                    _("Error restoring snapshot: {err}").format(err=str(e)),
                    "error", "errors")
        finally:
            release_snapshot_op()
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass
    Thread(target=do_restore, daemon=True).start()


def pre_update_snapshot(app):
    """Clean up old snapshots (keep 2) and create a pre-update snapshot."""
    if not app.cmd_exists("timeshift"):
        app.log("Auto-update: timeshift not installed, skipping snapshot")
        return
    if not acquire_snapshot_op():
        app.log("Auto-update: snapshot already running, skipping")
        _emit_progress(app, "error",
                       _("Another snapshot operation is already running."))
        return
    try:
        kill_stale_snapshot_procs()
        result = subprocess.run([shutil.which("timeshift") or "timeshift", "--list"],
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            snapshot_count = sum(1 for line in lines
                                 if line.strip() and not line.startswith('Num')
                                 and not line.startswith('---'))
            if snapshot_count > 2:
                delete_result = run_auth_cmd(
                    ["timeshift", "--delete-all", "--skip", "2"], timeout=300)
                if delete_result.returncode is None:
                    app.log("Auto-update: cleanup cancelled")
                elif delete_result.returncode == 0:
                    app.log("Auto-update: Cleaned up old snapshots (kept latest 2)")
                else:
                    app.log(f"Auto-update: Failed to clean up snapshots: {delete_result.stderr}")
    except Exception as e:
        app.log(f"Auto-update: Error checking snapshots: {e}")
    timestamp = subprocess.run([shutil.which("date") or "date", "+%Y-%m-%d_%H-%M-%S"],
                               capture_output=True, text=True).stdout.strip()
    comment = f"NeoArch pre-update snapshot {timestamp}"
    _emit_progress(app, "busy", _("Creating pre-update snapshot..."))
    try:
        if _system_timeshift_busy():
            raise _TimeshiftBusy()
        result = run_auth_cmd(
            ["timeshift", "--create", "--comments", comment], timeout=300)
        if result.returncode is None:
            app.log("Auto-update: Pre-update snapshot cancelled")
            _emit_progress(app, "error", _("Operation cancelled."))
        elif result.returncode == 0:
            app.log(f"Auto-update: Pre-update snapshot created: {comment}")
            _emit_progress(app, "done",
                           _("Pre-update snapshot created: {comment}").format(comment=comment))
            _report(app, _("Snapshot"),
                    _("Pre-update snapshot created: {comment}").format(comment=comment),
                    "success")
        else:
            app.log(f"Auto-update: Failed to create pre-update snapshot: {result.stderr}")
            if "Another instance" in result.stderr:
                _emit_progress(app, "error", _BUSY_MSG)
            else:
                _emit_progress(app, "error",
                               _("Failed to create pre-update snapshot: {err}")
                               .format(err=result.stderr))
    except _TimeshiftBusy:
        app.log("Auto-update: timeshift busy, skipping pre-update snapshot")
        _emit_progress(app, "error", _BUSY_MSG)
    except Exception as e:
        app.log(f"Auto-update: Pre-update snapshot creation failed: {e}")
        _emit_progress(app, "error",
                       _("Error creating pre-update snapshot: {err}")
                       .format(err=str(e)))
    finally:
        release_snapshot_op()


def delete_snapshots(app):
    """Delete old Timeshift snapshots, keeping only the 2 most recent."""
    if not app.cmd_exists("timeshift"):
        QMessageBox.warning(app, "Timeshift Not Found", "Timeshift is not installed.")
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
        if not acquire_snapshot_op():
            _busy_rejected(app)
            return
        try:
            kill_stale_snapshot_procs()
            _emit_progress(app, "busy", _("Deleting old snapshots..."))
            if _system_timeshift_busy():
                raise _TimeshiftBusy()
            result = run_auth_cmd(
                ["timeshift", "--delete-all", "--skip", "2"], timeout=300)
            if result.returncode is None:
                _cancelled(app)
            elif result.returncode == 0:
                _emit_progress(app, "done",
                               _("Old snapshots deleted successfully"))
                _report(app, _("Snapshot"),
                        _("Old snapshots deleted successfully"), "success")
            else:
                if "Another instance" in result.stderr:
                    _report_busy(app)
                else:
                    _emit_progress(app, "error",
                                   _("Failed to delete snapshots: {err}").format(err=result.stderr))
                    _report(app, _("Snapshot"),
                            _("Failed to delete snapshots: {err}").format(err=result.stderr),
                            "error", "errors")
        except _TimeshiftBusy:
            _report_busy(app)
        except Exception as e:
            _emit_progress(app, "error",
                           _("Error deleting snapshots: {err}").format(err=str(e)))
            _report(app, _("Snapshot"),
                    _("Error deleting snapshots: {err}").format(err=str(e)),
                    "error", "errors")
        finally:
            release_snapshot_op()
            try:
                app.ui_call.emit(lambda: app.loading_widget.stop_animation())
                app.ui_call.emit(lambda: app.loading_widget.setVisible(False))
            except Exception:
                pass
    Thread(target=do_delete, daemon=True).start()
