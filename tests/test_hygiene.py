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
            shutil.copy2(cmd[1], cmd[2])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(hygiene, "_run_sudo", fake_sudo)
    assert hygiene.accept_pacnew(str(pacnew)) is True
    assert original.read_text() == "new"
    assert not pacnew.exists()
    assert (tmp_path / "foo.conf.pacsave").exists()


def test_delete_pacnew(tmp_path):
    pacnew = tmp_path / "foo.conf.pacnew"
    pacnew.write_text("x")
    assert hygiene.delete_pacnew(str(pacnew)) is True
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
