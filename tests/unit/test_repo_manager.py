"""Unit tests for pacman repository management (parse + guarded edits)."""

from neoarch.backend.services import repo_manager

_SAMPLE = """# /etc/pacman.conf
[options]
HoldPkg = pacman glibc

[core]
Include = /etc/pacman.d/mirrorlist

[extra]
Include = /etc/pacman.d/mirrorlist

#[multilib]
#Include = /etc/pacman.d/mirrorlist

# neoarch-managed
[chaotic-aur]
Include = /etc/pacman.d/chaotic-mirrorlist
"""


def _lines(text=_SAMPLE):
    return text.splitlines()


def test_parse_detects_enabled_disabled_managed():
    sections = repo_manager.parse_pacman_conf(_SAMPLE)
    by_name = {s["name"]: s for s in sections}
    assert "core" in by_name and "extra" in by_name
    assert by_name["core"]["enabled"] is True
    assert by_name["core"]["include"] == "/etc/pacman.d/mirrorlist"
    assert by_name["multilib"]["enabled"] is False
    assert by_name["chaotic-aur"]["managed"] is True
    assert by_name["core"]["managed"] is False


def test_parse_collects_multiple_servers():
    text = "[myrepo]\nServer = https://a.example\nServer = https://b.example\n"
    sections = repo_manager.parse_pacman_conf(text)
    assert len(sections) == 1
    assert sections[0]["servers"] == ["https://a.example", "https://b.example"]


def test_build_block_marker_header_include_servers():
    block = repo_manager.build_block("myrepo", servers=["https://x.example"],
                                     include="/etc/pacman.d/mylist")
    assert block[0] == "# neoarch-managed"
    assert block[1] == "[myrepo]"
    assert "Include = /etc/pacman.d/mylist" in block
    assert "Server = https://x.example" in block


def _section_positions(out):
    lines = out.splitlines() if isinstance(out, str) else out
    return repo_manager.parse_pacman_conf("\n".join(lines) + "\n")


def test_apply_add_appends_block_and_marker():
    out = repo_manager.apply_add(_lines(), "archlinuxcn",
                                 servers=["https://cn.example/$arch"])
    text = "\n".join(out)
    assert "[archlinuxcn]" in text
    assert "# neoarch-managed" in text
    assert text.rstrip().endswith("Server = https://cn.example/$arch")
    assert text.index("# neoarch-managed") < text.index("[archlinuxcn]")
    # original sections survive untouched
    assert "[core]" in text and "[chaotic-aur]" in text


def test_apply_add_rejects_existing_repo():
    try:
        repo_manager.apply_add(_lines(), "core", include="/etc/x")
    except ValueError as e:
        assert "already exists" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_apply_remove_removes_managed_block_only():
    out = repo_manager.apply_remove(_lines(), "chaotic-aur")
    text = "\n".join(out)
    assert "[chaotic-aur]" not in text
    assert "neoarch-managed" not in text
    assert "[extra]" in text and "[core]" in text


def test_apply_remove_refuses_unmanaged():
    try:
        repo_manager.apply_remove(_lines(), "extra")
    except ValueError as e:
        assert "managed" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_apply_remove_unknown_raises():
    try:
        repo_manager.apply_remove(_lines(), "nope")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def _lines_with_myrepo():
    return (_SAMPLE.splitlines() +
            ["", "# neoarch-managed", "[myrepo]", "Server = https://x.example/$arch"])


def test_apply_enable_comments_and_uncomments_header():
    lines = _lines_with_myrepo()

    out = repo_manager.apply_enable(lines, "myrepo", False)
    candidates = [l for l in out if l.lstrip("#").startswith("[myrepo]")]
    assert candidates, "expected a myrepo header line"
    disabled = candidates[0]
    assert disabled.lstrip().startswith("#")
    assert disabled.lstrip("#").startswith("[myrepo]")

    text = "\n".join(out)
    assert "# neoarch-managed\n[chaotic-aur]" in text  # untouched section

    reenabled = repo_manager.apply_enable(out, "myrepo", True)
    candidates = [l for l in reenabled if l.lstrip("#").startswith("[myrepo]")]
    assert candidates, "expected a myrepo header line"
    active = candidates[0]
    assert not active.lstrip().startswith("#")


def test_apply_enable_noop_when_already_same():
    lines = _lines()[:0] + ["[myrepo]", "Server = https://x"]
    out = repo_manager.apply_enable(lines, "myrepo", True)
    assert out == lines


def test_apply_enable_refuses_system_repos():
    for name in ("core", "extra"):
        try:
            repo_manager.apply_enable(_lines(), name, False)
        except ValueError as e:
            assert "system repository" in str(e)
        else:
            raise AssertionError(f"expected ValueError for {name}")


def test_list_repos_reads_configured_path(tmp_path, monkeypatch):
    conf = tmp_path / "pacman.conf"
    conf.write_text(_SAMPLE, encoding="utf-8")
    monkeypatch.setattr(repo_manager, "PACMAN_CONF", str(conf))
    repos = {r["name"]: r for r in repo_manager.list_repos()}
    assert repos["core"]["system"] is True
    assert repos["chaotic-aur"]["managed"] is True
    assert repos["multilib"]["enabled"] is False
    assert repos["chaotic-aur"]["include"] == "/etc/pacman.d/chaotic-mirrorlist"


def test_add_repo_rejects_bad_input_without_writing():
    ok, msg = repo_manager.add_repo("bad name!..", servers=["https://x"])
    assert ok is False and msg
    ok, msg = repo_manager.add_repo("mylist")
    assert ok is False and "Include" in msg
    ok, msg = repo_manager.add_repo("mylist", include="relative/path")
    assert ok is False and "under /etc/" in msg
    ok, msg = repo_manager.add_repo("mylist", servers=["file:///tmp/x"])
    assert ok is False and "http" in msg
    ok, msg = repo_manager.add_repo("mylist", servers=["https://x\n\ny"])
    assert ok is False


def test_add_repo_refuses_system_name():
    ok, msg = repo_manager.add_repo("Core", servers=["https://x"])
    assert ok is False and "system repository" in msg


# ── distro-aware Chaotic AUR preflight ───────────────────────────────


def _os_release(data):
    return "\n".join(f"{k}={v}" for k, v in data.items()) + "\n"


def test_read_os_release_parses(tmp_path):
    f = tmp_path / "os-release"
    f.write_text(_os_release({"ID": "manjaro", "ID_LIKE": "arch"}),
                 encoding="utf-8")
    data = repo_manager.read_os_release(str(f))
    assert data["ID"] == "manjaro"
    assert data["ID_LIKE"] == "arch"


def test_read_os_release_missing_is_empty():
    assert repo_manager.read_os_release("/nonexistent/os-release") == {}


def test_read_os_release_handles_quotes_and_comments(tmp_path):
    f = tmp_path / "os-release"
    f.write_text('PRETTY_NAME="Manjaro Linux"\n# comment line\nID=manjaro\n',
                 encoding="utf-8")
    data = repo_manager.read_os_release(str(f))
    assert data["PRETTY_NAME"] == "Manjaro Linux"
    assert data["ID"] == "manjaro"


def test_chaotic_preflight_empty_on_arch(tmp_path, monkeypatch):
    f = tmp_path / "os-release"
    f.write_text(_os_release({"ID": "arch"}), encoding="utf-8")
    monkeypatch.setattr(repo_manager, "_OS_RELEASE_PATH", str(f))
    assert repo_manager.chaotic_preflight() == ""


def test_chaotic_preflight_empty_on_arch_derivative(tmp_path, monkeypatch):
    f = tmp_path / "os-release"
    f.write_text(_os_release({"ID": "endeavouros", "ID_LIKE": "arch"}),
                 encoding="utf-8")
    monkeypatch.setattr(repo_manager, "_OS_RELEASE_PATH", str(f))
    assert repo_manager.chaotic_preflight() == ""


def test_chaotic_preflight_warns_on_manjaro_stable(tmp_path, monkeypatch):
    f = tmp_path / "os-release"
    f.write_text(_os_release({"ID": "manjaro"}), encoding="utf-8")
    mirrors = tmp_path / "pacman-mirrors.conf"
    mirrors.write_text("Branch = stable\n", encoding="utf-8")
    monkeypatch.setattr(repo_manager, "_OS_RELEASE_PATH", str(f))
    monkeypatch.setattr(repo_manager, "_PACMAN_MIRRORS_CONF", str(mirrors))
    msg = repo_manager.chaotic_preflight()
    assert msg and "stable" in msg and "unstable" in msg


def test_chaotic_preflight_empty_on_manjaro_unstable(tmp_path, monkeypatch):
    f = tmp_path / "os-release"
    f.write_text(_os_release({"ID": "manjaro"}), encoding="utf-8")
    mirrors = tmp_path / "pacman-mirrors.conf"
    mirrors.write_text("Branch = unstable\n", encoding="utf-8")
    monkeypatch.setattr(repo_manager, "_OS_RELEASE_PATH", str(f))
    monkeypatch.setattr(repo_manager, "_PACMAN_MIRRORS_CONF", str(mirrors))
    assert repo_manager.chaotic_preflight() == ""