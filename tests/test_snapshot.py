"""Regression tests for the Timeshift snapshot service (snapshot.py).

Cover the deadline behaviour for ``timeshift --create``: a full rsync
snapshot can legitimately outlive the old 5-minute deadline while still
being produced, so the service must never surface a failure for a
snapshot that actually exists.
"""

import subprocess

import neoarch.backend.services.snapshot as snapshot


class _Events:
    def emit(self, fn=None):
        if fn is not None:
            fn()


class FakeApp:
    def __init__(self):
        self.events = []
        self.ui_call = _Events()
        self.show_message = _Events()
        self.snapshot_progress = None

        def notify(title, text, level="info", event="install"):
            self.events.append(("notify", title, text, level, event))

        self._notify = notify


def test_report_created_found(monkeypatch):
    monkeypatch.setattr(snapshot, "_find_snapshot", lambda comment: "Wed 16 Sep 2026 09:40:31 PM +0530")
    app = FakeApp()
    ok = snapshot._report_created(app, "NeoArch manual snapshot x")
    assert ok is True
    assert any(e[0] == "notify" and e[3] == "success" for e in app.events)


def test_report_created_missing(monkeypatch):
    monkeypatch.setattr(snapshot, "_find_snapshot", lambda comment: None)
    app = FakeApp()
    assert snapshot._report_created(app, "NeoArch manual snapshot x") is False
    assert not app.events


def test_timeshift_create_deadline_is_lengthy():
    # 5-minute deadline killed mid-rsync and reported "[timeout]" while
    # the snapshot was actually still produced. The deadline is now only
    # a safety net; cancel is the abort path.
    assert snapshot.TIMESHIFT_CREATE_TIMEOUT >= 3 * 3600
    assert snapshot.TIMESHIFT_CLEANUP_TIMEOUT >= 3600


def test_create_timeout_reports_success_when_snapshot_exists(monkeypatch):
    """rc == -1 ("[timeout]") must not fail if the snapshot was made."""

    app = FakeApp()
    app.snapshot_progress = _Events()
    app.cmd_exists = lambda _bin: True

    monkeypatch.setattr(snapshot, "_find_snapshot", lambda comment: "Wed 16 Sep 2026 09:40:31 PM +0530")
    monkeypatch.setattr(
        snapshot,
        "run_auth_cmd",
        lambda *a, **k: snapshot._AuthResult(-1, "", "Group killed by timeout\n[timeout]\n"),
    )

    created = snapshot._report_created(app, "NeoArch manual snapshot x")
    assert created is True
    assert any(e[0] == "notify" and e[3] == "success" for e in app.events)