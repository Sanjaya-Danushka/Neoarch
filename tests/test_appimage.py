"""Tests for the managed AppImage store (Phase 3c roadmap)."""

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.appimage as appimage


def _setup(tmp_path, monkeypatch):
    appimage.APPIMAGE_DIR = str(tmp_path / "appimages")
    appimage.ICON_DIR = str(tmp_path / "appimages" / "icons")
    appimage.METADATA_PATH = str(tmp_path / "appimages" / "metadata.json")
    appimage.DESKTOP_DIR = str(tmp_path / "applications")


def _fake_appimage(tmp_path, name="Obsidian-1.5.12-x86_64.AppImage"):
    p = tmp_path / name
    p.write_bytes(b"\x7fELF" + b"\x00" * 100)
    return str(p)


def test_make_id():
    assert appimage._make_id("Obsidian") == "obsidian"
    assert appimage._make_id("  My Cool App!  ") == "my-cool-app"
    assert appimage._make_id("!!!") == "appimage"


def test_parse_version_from_name():
    assert appimage._parse_version_from_name("Obsidian-1.5.12-x86_64.AppImage") == "1.5.12"
    assert appimage._parse_version_from_name("foo_2.1.AppImage") == "2.1"
    assert appimage._parse_version_from_name("no-version.AppImage") is None


def test_clean_tag():
    assert appimage._clean_tag("v1.2.3") == "1.2.3"
    assert appimage._clean_tag("1.2.3") == "1.2.3"
    assert appimage._clean_tag("") == ""


def test_is_newer():
    assert appimage._is_newer("1.6.0", "1.5.12") is True
    assert appimage._is_newer("1.5.12", "1.5.12") is False
    assert appimage._is_newer("1.5.1", "1.5.12") is False
    assert appimage._is_newer("1.5.12.1", "1.5.12") is True


def test_release_api_urls():
    assert appimage._release_api("github", "obsidianmd", "obsidian-releases") == \
        "https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest"
    assert appimage._release_api("codeberg", "a", "b") == \
        "https://codeberg.org/api/v1/repos/a/b/releases/latest"
    assert appimage._release_api("gitlab", "o", "r").startswith("https://gitlab.com/api/v4/projects/")
    assert appimage._release_api("unknown", "a", "b") is None


def test_latest_release_github(monkeypatch):
    payload = {
        "tag_name": "v2.0.0",
        "assets": [
            {"browser_download_url": "https://github.com/x/y/releases/download/v2.0.0/app-2.0.0.AppImage"},
            {"browser_download_url": "https://github.com/x/y/releases/download/v2.0.0/app-2.0.0.tar.gz"},
        ],
    }
    monkeypatch.setattr(urllib_request(), "urlopen", _urlopen(json.dumps(payload)))
    info = appimage._latest_release("github", "x", "y")
    assert info["tag"] == "v2.0.0"
    assert "app-2.0.0.AppImage" in info["url"]


def test_latest_release_empty(monkeypatch):
    monkeypatch.setattr(urllib_request(), "urlopen", _urlopen("{}"))
    assert appimage._latest_release("github", "x", "y") == {"tag": "", "url": ""}


def test_add_from_file(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch)
    appimage._extract_metadata = lambda path, icon_dest_dir="": {
        "name": "Obsidian", "icon_inside": None, "desktop": None}
    entry = appimage.add_from_file(_fake_appimage(tmp_path))
    assert entry["id"] == "obsidian"
    assert entry["name"] == "Obsidian"
    assert entry["version"] == "1.5.12"
    assert os.path.isfile(entry["bin_path"])
    assert os.access(entry["bin_path"], os.X_OK)
    assert os.path.isfile(entry["desktop_path"])
    listed = appimage.list_appimages()
    assert len(listed) == 1


def test_add_from_file_with_icon(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    icon = tmp_path / "obsidian.png"
    icon.write_bytes(b"png")
    appimage._extract_metadata = lambda path, icon_dest_dir="": {
        "name": "Obsidian", "icon_inside": str(icon), "desktop": None}
    entry = appimage.add_from_file(_fake_appimage(tmp_path))
    assert os.path.isfile(entry["icon_path"])
    assert "Icon=" in open(entry["desktop_path"]).read()


def test_extract_metadata_copies_icon_out_of_workdir(tmp_path, monkeypatch):
    """Regression: an icon found inside the extraction scratch dir must be
    copied out before the scratch dir is deleted, or the returned path dies."""
    import importlib
    importlib.reload(appimage)
    _setup(tmp_path, monkeypatch)
    root = tmp_path / "extract" / "squashfs-root"
    icons_dir = root / "usr" / "share" / "icons" / "hicolor" / "128x128" / "apps"
    icons_dir.mkdir(parents=True)
    (icons_dir / "aptakube.png").write_bytes(b"pngdata")
    (root / "aptakube.desktop").write_text(
        "[Desktop Entry]\nName=Aptakube\nIcon=aptakube\n", encoding="utf-8")

    def fake_extract(path):
        workdir = tmp_path / "extract"
        monkeypatch.setattr(appimage.tempfile, "mkdtemp", lambda *a, **k: str(workdir))
        monkeypatch.setattr(appimage.subprocess, "run",
                            lambda *a, **k: subprocess.CompletedProcess(args=(), returncode=0))
        return appimage._extract_metadata(path, icon_dest_dir=str(tmp_path / "icons"))

    fake = tmp_path / "fake.AppImage"
    fake.write_bytes(b"\x7fELF" + b"\x00" * 10)
    meta = fake_extract(str(fake))
    assert meta["icon_inside"], "icon should have been found and copied out"
    assert os.path.isfile(meta["icon_inside"])
    assert meta["icon_inside"].startswith(str(tmp_path / "icons"))


def test_desktop_entry_text():
    text = appimage._desktop_entry_text("obsidian", "Obsidian", "/bin/obsidian", "/ico.png")
    assert "[Desktop Entry]" in text
    assert "Name=Obsidian" in text
    assert "Exec=/bin/obsidian" in text
    assert "Icon=/ico.png" in text
    assert "X-NeoArch-AppImage=true" in text


def test_remove_appimage(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    appimage._extract_metadata = lambda path, icon_dest_dir="": {"name": None, "icon_inside": None, "desktop": None}
    entry = appimage.add_from_file(_fake_appimage(tmp_path))
    assert appimage.remove_appimage("obsidian") is True
    assert not os.path.exists(entry["bin_path"])
    assert not os.path.exists(entry["desktop_path"])
    assert appimage.list_appimages() == []
    assert appimage.remove_appimage("obsidian") is False


def test_add_from_url(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    appimage._extract_metadata = lambda path, icon_dest_dir="": {"name": None, "icon_inside": None, "desktop": None}
    appimage._download = lambda url, dest: (_write_fake(dest), True)[1]
    entry = appimage.add_from_url("MyApp", "https://example.com/MyApp-3.0.AppImage")
    assert entry["id"] == "myapp"
    assert entry["source_type"] == "url"
    assert entry["source"] == "https://example.com/MyApp-3.0.AppImage"
    assert entry["version"] == "3.0"
    assert os.path.isfile(entry["bin_path"])


def test_add_from_url_rejects_non_appimage():
    try:
        appimage.add_from_url("x", "https://example.com/file.tar.gz")
        assert False, "should raise"
    except ValueError:
        pass


def test_add_from_repo(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    appimage._extract_metadata = lambda path, icon_dest_dir="": {"name": None, "icon_inside": None, "desktop": None}
    appimage._latest_release = lambda host, owner, repo: {
        "tag": "v4.2.1", "url": "https://example.com/App-4.2.1.AppImage"}
    appimage._download = lambda url, dest: (_write_fake(dest), True)[1]
    entry = appimage.add_from_repo("MyApp", "owner", "repo", "github")
    assert entry["source_type"] == "repo"
    assert entry["host"] == "github"
    assert entry["owner"] == "owner"
    assert entry["repo"] == "repo"
    assert entry["version"] == "4.2.1"


def test_add_from_repo_no_asset(tmp_path, monkeypatch):
    appimage._latest_release = lambda *a: {"tag": "v1", "url": ""}
    try:
        appimage.add_from_repo("MyApp", "o", "r")
        assert False, "should raise"
    except RuntimeError:
        pass


def test_check_update_repo(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    appimage._extract_metadata = lambda path, icon_dest_dir="": {"name": None, "icon_inside": None, "desktop": None}
    appimage._download = lambda url, dest: (_write_fake(dest), True)[1]
    appimage._latest_release = lambda host, owner, repo: {
        "tag": "v9.0.0", "url": "https://example.com/App-9.0.0.AppImage"}
    entry = appimage.add_from_file(_fake_appimage(tmp_path, "App-1.0.AppImage"), name="App")
    appimage._update_entry("app", {"source_type": "repo", "host": "github",
                                   "owner": "o", "repo": "r"})
    updated = appimage.check_update("app")
    assert updated["latest_version"] == "9.0.0"
    assert "9.0.0" in updated["latest_url"]
    assert updated["last_check"] is not None


def test_check_update_static(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    appimage._extract_metadata = lambda path, icon_dest_dir="": {"name": None, "icon_inside": None, "desktop": None}
    appimage._download = lambda url, dest: (_write_fake(dest), True)[1]
    entry = appimage.add_from_url("App", "https://example.com/App-2.5.AppImage")
    updated = appimage.check_update("app")
    assert updated["latest_version"] == "2.5"


def test_install_update(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    appimage._extract_metadata = lambda path, icon_dest_dir="": {"name": None, "icon_inside": None, "desktop": None}
    appimage._download = lambda url, dest: (_write_fake(dest), True)[1]
    appimage._latest_release = lambda *a: {"tag": "v2.0", "url": "https://x/App-2.0.AppImage"}
    entry = appimage.add_from_file(_fake_appimage(tmp_path, "App-1.0.AppImage"), name="App")
    appimage._update_entry("app", {"source_type": "repo", "host": "github",
                                   "owner": "o", "repo": "r"})
    assert appimage.install_update("app") is True
    refreshed = next(e for e in appimage.list_appimages() if e["id"] == "app")
    assert refreshed["version"] == "2.0"
    assert refreshed["latest_version"] is None


def test_install_update_no_newer(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    appimage._extract_metadata = lambda path, icon_dest_dir="": {"name": None, "icon_inside": None, "desktop": None}
    appimage._latest_release = lambda *a: {"tag": "v1.0", "url": "https://x/App-1.0.AppImage"}
    appimage.add_from_file(_fake_appimage(tmp_path, "App-2.0.AppImage"), name="App")
    assert appimage.install_update("app") is False


def test_sync_from_disk_removes_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    appimage._extract_metadata = lambda path, icon_dest_dir="": {"name": None, "icon_inside": None, "desktop": None}
    entry = appimage.add_from_file(_fake_appimage(tmp_path, "App-1.0.AppImage"), name="App")
    os.remove(entry["bin_path"])
    remaining = appimage.sync_from_disk()
    assert remaining == []


# ── helpers ──────────────────────────────────────────────────────────────

def urllib_request():
    import urllib.request
    return urllib.request


def _urlopen(body):
    class _Resp:
        def __init__(self, body):
            self.body = body

        def read(self):
            return self.body.encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return lambda req, **k: _Resp(body)


def _write_fake(dest):
    with open(dest, "wb") as f:
        f.write(b"\x7fELF" + b"\x00" * 64)
