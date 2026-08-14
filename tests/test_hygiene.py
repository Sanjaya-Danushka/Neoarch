import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.hygiene as hygiene


def test_list_orphans_parses_output(monkeypatch):
    fake = subprocess.CompletedProcess(["pacman", "-Qtdq"], 0, stdout="libfoo\nlibbar\n", stderr="")
    monkeypatch.setattr(hygiene, "_run", lambda *a, **k: fake)
    assert hygiene.list_orphans() == ["libfoo", "libbar"]


def test_list_orphans_none(monkeypatch):
    fake = subprocess.CompletedProcess(["pacman", "-Qtdq"], 1, stdout="", stderr="err")
    monkeypatch.setattr(hygiene, "_run", lambda *a, **k: fake)
    assert hygiene.list_orphans() == []


def test_remove_orphans_runs_sudo(monkeypatch):
    calls = []
    monkeypatch.setattr(hygiene, "list_orphans", lambda: ["libfoo"])
    monkeypatch.setattr(hygiene, "_run_sudo", lambda cmd, timeout=600: calls.append(cmd) or
                        subprocess.CompletedProcess(cmd, 0, "", ""))
    assert hygiene.remove_orphans() is True
    assert calls == [["pacman", "-Rns", "--noconfirm", "libfoo"]]


def test_remove_orphans_no_orphans(monkeypatch):
    monkeypatch.setattr(hygiene, "list_orphans", lambda: [])
    monkeypatch.setattr(hygiene, "_run_sudo", lambda cmd, timeout=600: None)
    assert hygiene.remove_orphans() is True


def test_pacnew_info_extracts_package(monkeypatch, tmp_path):
    pacnew = tmp_path / "foo.conf.pacnew"
    pacnew.write_text("x")
    info = hygiene._pacnew_info(str(pacnew))
    assert info["path"] == str(pacnew)
    assert info["original"] == str(tmp_path / "foo.conf")


def test_diff_pacnew_identical(monkeypatch, tmp_path):
    original = tmp_path / "foo.conf"
    original.write_text("same")
    pacnew = tmp_path / "foo.conf.pacnew"
    pacnew.write_text("same")
    assert hygiene.diff_pacnew(str(pacnew)) == "(no differences)"


def test_accept_pacnew_copies_and_removes(monkeypatch, tmp_path):
    original = tmp_path / "foo.conf"
    original.write_text("old")
    pacnew = tmp_path / "foo.conf.pacnew"
    pacnew.write_text("new")

    def fake_sudo(cmd, timeout=600):
        import shutil
        if cmd[0] == "cp":
            if cmd[1] == "-a":
                shutil.copy2(cmd[2], cmd[3])
            else:
                shutil.copy2(cmd[1], cmd[2])
        elif cmd[0] == "rm":
            os.remove(cmd[-1])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(hygiene, "_run_sudo", fake_sudo)
    assert hygiene.accept_pacnew(str(pacnew)) is True
    assert original.read_text() == "new"
    assert not pacnew.exists()
    assert (tmp_path / "foo.conf.pacsave").exists()


def test_accept_pacnew_backup_uses_sudo(monkeypatch, tmp_path):
    """Backup must be created via sudo since /etc is root-owned."""
    original = tmp_path / "foo.conf"
    original.write_text("old")
    pacnew = tmp_path / "foo.conf.pacnew"
    pacnew.write_text("new")
    calls = []

    def fake_sudo(cmd, timeout=600):
        import shutil
        calls.append(cmd)
        if cmd[0] == "cp" and cmd[1] != "-a":
            shutil.copy2(cmd[1], cmd[2])
        elif cmd[0] == "cp":
            shutil.copy2(cmd[2], cmd[3])
        elif cmd[0] == "rm":
            pacnew.unlink()
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(hygiene, "_run_sudo", fake_sudo)
    assert hygiene.accept_pacnew(str(pacnew)) is True
    assert calls[0] == ["cp", "-a", str(original), str(tmp_path / "foo.conf.pacsave")]
    assert calls[1] == ["cp", str(pacnew), str(original)]
    assert calls[2] == ["rm", "-f", str(pacnew)]


def test_delete_pacnew(tmp_path):
    pacnew = tmp_path / "foo.conf.pacnew"
    pacnew.write_text("x")
    assert hygiene.delete_pacnew(str(pacnew)) is True
    assert not pacnew.exists()


def test_delete_pacnew_root_owned_uses_sudo(monkeypatch, tmp_path):
    """Root-owned /etc files must be removed via sudo, not plain os.remove."""
    pacnew = tmp_path / "foo.conf.pacnew"
    pacnew.write_text("x")
    calls = []

    def fake_sudo(cmd, timeout=600):
        calls.append(cmd)
        if cmd[0] == "rm":
            pacnew.unlink()
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(hygiene, "_run_sudo", fake_sudo)
    assert hygiene.delete_pacnew(str(pacnew)) is True
    assert calls == [["rm", "-f", str(pacnew)]]
    assert not pacnew.exists()


def test_parse_news():
    xml = """<?xml version="1.0"?>
<rss><channel><item>
  <title>Arch News One</title>
  <link>https://archlinux.org/news/one/</link>
  <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
  <description>First summary</description>
</item><item>
  <title>Arch News Two</title>
  <link>https://archlinux.org/news/two/</link>
</item></channel></rss>"""
    items = hygiene._parse_news(xml)
    assert len(items) == 2
    assert items[0]["title"] == "Arch News One"
    assert items[0]["link"] == "https://archlinux.org/news/one/"
    assert "summary" in items[0]


def test_parse_news_invalid():
    assert hygiene._parse_news("not xml") == []


def test_fetch_news_falls_back_to_cache(monkeypatch, tmp_path):
    xml = '<rss><channel><item><title>Cached</title><link>l</link></item></channel></rss>'
    cache = str(tmp_path / "news.xml")
    with open(cache, "w") as f:
        f.write(xml)
    monkeypatch.setattr(hygiene, "NEWS_CACHE", cache)
    monkeypatch.setattr(hygiene, "_fetch_news_xml", lambda: "")
    items = hygiene.fetch_news()
    assert items and items[0]["title"] == "Cached"


# ──────────────────────────────────────────────────────────────────────────
# Cache retention / corrupted archives
# ──────────────────────────────────────────────────────────────────────────

def test_list_corrupted_packages(monkeypatch, tmp_path):
    good = tmp_path / "good-1.0-1-x86_64.pkg.tar.zst"
    bad = tmp_path / "bad-1.0-1-x86_64.pkg.tar.zst"
    good.write_bytes(b"data")
    bad.write_bytes(b"data")
    other = tmp_path / "notes.txt"
    other.write_text("x")

    results = {str(good): 0, str(bad): 1, str(other): 0}
    monkeypatch.setattr(hygiene, "_run",
                        lambda cmd, **k: subprocess.CompletedProcess(
                            cmd, results.get(cmd[-1], 0), stdout="", stderr=""))
    import neoarch.backend.services.downgrade as downgrade
    monkeypatch.setattr(downgrade, "cache_dirs", lambda: [str(tmp_path)])
    assert hygiene.list_corrupted_packages() == [str(bad)]


def test_remove_corrupted_packages(monkeypatch, tmp_path):
    monkeypatch.setattr(hygiene, "list_corrupted_packages",
                        lambda: [str(tmp_path / "bad.pkg.tar.zst")])
    calls = []
    monkeypatch.setattr(hygiene, "_run_sudo", lambda cmd, **k: calls.append(cmd)
                        or subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""))
    assert hygiene.remove_corrupted_packages() is True
    assert calls and calls[0][0] == "rm" and calls[0][1] == "-f"


def test_purge_cache_runs_paccache(monkeypatch):
    calls = []
    monkeypatch.setattr(hygiene, "_run_sudo", lambda cmd, **k: calls.append(cmd)
                        or subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""))
    assert hygiene.purge_cache(2) is True
    assert calls[-1][:4] == ["paccache", "-r", "-k", "2"]
    assert hygiene.purge_cache(-1) is False


def test_purge_flatpak_unused(monkeypatch):
    calls = []
    monkeypatch.setattr(hygiene, "_run_sudo", lambda cmd, **k: calls.append(cmd)
                        or subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""))
    assert hygiene.purge_flatpak_unused() is True
    assert calls[-1][0] == "flatpak" and "--unused" in calls[-1]


# ──────────────────────────────────────────────────────────────────────────
# Three-way pacnew merge
# ──────────────────────────────────────────────────────────────────────────

def test_merge_pacnew_clean_accept(monkeypatch, tmp_path):
    original = tmp_path / "conf"
    pacnew = tmp_path / "conf.pacnew"
    original.write_text("A = old\nB = shared\n")
    pacnew.write_text("A = new\nB = shared\n")

    monkeypatch.setattr(hygiene, "_extract_base", lambda *a, **k: "A = old\nB = shared\n")
    import shutil

    def fake_sudo(cmd, **k):
        if cmd and cmd[0] == "cp":
            shutil.copy(cmd[-2], cmd[-1])
        elif cmd and cmd[0] == "rm":
            os.remove(cmd[-1])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(hygiene, "_run_sudo", fake_sudo)
    result = hygiene.merge_pacnew(str(pacnew), accept=True)
    assert result["conflicts"] is False
    assert original.read_text() == "A = new\nB = shared\n"
    assert not pacnew.exists()


def test_merge_pacnew_with_conflicts(monkeypatch, tmp_path):
    original = tmp_path / "conf"
    pacnew = tmp_path / "conf.pacnew"
    original.write_text("A = user\nB = mine\n")
    pacnew.write_text("A = user\nB = theirs\n")
    monkeypatch.setattr(hygiene, "_extract_base", lambda *a, **k: "A = user\nB = base\n")

    result = hygiene.merge_pacnew(str(pacnew))
    assert result["conflicts"] is True
    merged_path = result["merged"]
    assert merged_path.endswith(".merged")
    content = open(merged_path).read()
    assert "<<<<<<<" in content
    assert pacnew.exists()
    os.remove(merged_path)


def test_merge_pacnew_missing_pacnew(monkeypatch, tmp_path):
    result = hygiene.merge_pacnew(str(tmp_path / "none.pacnew"))
    assert result["conflicts"] is True


def test_extract_base_uses_cached_archive(monkeypatch, tmp_path):
    archive = tmp_path / "confpkg-1.0-1-x86_64.pkg.tar.zst"
    archive.write_bytes(b"x")
    import neoarch.backend.services.downgrade as downgrade
    monkeypatch.setattr(downgrade, "cache_dirs", lambda: [str(tmp_path)])
    monkeypatch.setattr(downgrade, "_parse_pkgfile",
                        lambda p: {"name": "confpkg", "version": "1.0-1"})
    monkeypatch.setattr(hygiene, "_run", lambda cmd, **k: subprocess.CompletedProcess(
        cmd, 0, stdout="A = old\n", stderr=""))
    base = hygiene._extract_base("/etc/conf", "/etc/conf.pacnew", "confpkg")
    assert base == "A = old\n"


# ──────────────────────────────────────────────────────────────────────────
# News read-tracking
# ──────────────────────────────────────────────────────────────────────────

def test_news_seen_roundtrip(monkeypatch, tmp_path):
    seen_path = tmp_path / "news_seen.json"
    monkeypatch.setattr(hygiene, "NEWS_SEEN_CACHE", str(seen_path))
    entry = {"id": "https://archlinux.org/news/foo", "title": "Foo"}
    assert hygiene.news_seen(entry) is False
    assert hygiene.mark_news_seen(entry) is True
    assert hygiene.news_seen(entry) is True


def test_news_seen_status(monkeypatch, tmp_path):
    seen_path = tmp_path / "news_seen.json"
    monkeypatch.setattr(hygiene, "NEWS_SEEN_CACHE", str(seen_path))
    hygiene.mark_news_seen({"link": "https://archlinux.org/news/a"})
    entries = [
        {"link": "https://archlinux.org/news/a"},
        {"link": "https://archlinux.org/news/b"},
    ]
    marked = hygiene.news_seen_status(entries)
    assert marked[0]["seen"] is True
    assert marked[1]["seen"] is False


def test_mark_news_seen_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(hygiene, "NEWS_SEEN_CACHE", str(tmp_path / "seen.json"))
    assert hygiene.mark_news_seen({"title": ""}) is False
    assert hygiene.news_seen({"title": ""}) is False


def test_news_unseen_count(monkeypatch, tmp_path):
    seen_path = tmp_path / "news_seen.json"
    monkeypatch.setattr(hygiene, "NEWS_SEEN_CACHE", str(seen_path))
    hygiene.mark_news_seen({"link": "https://archlinux.org/news/a"})
    monkeypatch.setattr(
        hygiene, "fetch_news",
        lambda limit=50: [
            {"id": "https://archlinux.org/news/a", "title": "A"},
            {"id": "https://archlinux.org/news/b", "title": "B"},
        ])
    assert hygiene.news_unseen_count() == 1


def test_parse_news_has_id():
    items = hygiene._parse_news(
        "<rss><channel><item><title>T</title><link>http://x/1</link>"
        "</item></channel></rss>")
    assert items[0]["id"] == "http://x/1"
