"""Pre-install PKGBUILD security scanner.

Static analysis of AUR PKGBUILD files and their `.install` scriptlets before
installation. Flags risky post-install behavior, binary source files,
privilege-elevation commands, and Unicode homograph spoofing.

Modeled on the checks offered by other package managers, this is a
clean-room implementation and returns findings with severity:

    info     — informational, low risk
    warning  — deserves a closer look
    critical — strongly suspicious; recommend cancelling

The scanner never executes the PKGBUILD.
"""

import os
import re
import shlex
import subprocess
import unicodedata
from typing import Dict, List, Optional

__all__ = [
    "scan_pkgbuild", "scan_install_scriptlet", "findings_for_file",
    "RISKY_TOOLS", "ELEVATION_TOOLS", "DYNAMIC_PATTERNS",
    "MALICIOUS_NPM_PACKAGES",
]

# ──────────────────────────────────────────────────────────────────────────
# Detection tables
# ──────────────────────────────────────────────────────────────────────────

# Tools that commonly download or execute external code during install.
RISKY_TOOLS = (
    "npm", "npx", "yarn", "pnpm", "bun",
    "pip", "pip3", "curl", "wget",
)

# Privilege elevation commands (run package-controlled code as root).
ELEVATION_TOOLS = (
    "sudo", "sudoedit", "doas", "pkexec", "run0", "su",
)

# Dynamic command-construction patterns that cannot be reviewed statically.
DYNAMIC_PATTERNS = (
    (r"\$\(", "command substitution"),
    (r"\beval\b", "eval"),
    (r"\$\{!\w+\}", "bash indirect expansion"),
    (r"openssl\s+.*\|\s*(sh|bash)\b", "decrypt-into-shell"),
    (r"\|\s*(sh|bash)\b", "pipe to shell"),
)

# Patterns that must be matched against the RAW line (de-obfuscation would
# destroy the signal).
RAW_LINE_PATTERNS = (
    (r"(?<!\\)`", "command substitution (backticks)"),
)

# ──────────────────────────────────────────────────────────────────────────
# ArchCanary v0.1.37 rules (patterns 1, 2, 7, 14, 16, 17) ported at the
# semantics level. Comments and heredoc bodies are exempt where a `#` note or
# a here-doc payload would destroy the signal; other rules keep scanning them.
# ──────────────────────────────────────────────────────────────────────────

# Pattern 1: known-malicious package names from the June 2026 AUR
# supply-chain campaign (mirrors ArchCanary's malicious_npm_packages.txt):
# quote-split names like 'j''s'-"d""i""g""e""s""t" defeat plain grep but not a
# de-obfuscated scan (a name must be long enough that quote-splitting still
# reconstructs it, so these short names are matched against the cleaned line).
MALICIOUS_NPM_PACKAGES = (
    "atomic-lockfile",
    "js-digest",
    "lockfile-js",
    "nextfile-js",
)
MALICIOUS_NPM_INSTALL = re.compile(r"(?:bun[ \t]+add|npm[ \t]+install)")

# Pattern 2: `base64` decode straight into a shell. The decode flag (`-d`,
# `--decode`, or a `d` in a short-flag group) must come before a `|` with no
# `;`/`&&`/`|` boundary — so `base64 -d > f && x | sh` (decode redirected to a
# file, then a separate command) never matches — AND somewhere down that same
# pipeline a shell runs (PIPE_TO_SHELL, so `base64 -d | tr a b | bash` counts).
BASE64_DECODE_PIPE = re.compile(
    r"base64([ \t][^\;\&\|]*)?[ \t]"
    r"(-[A-Za-z]*d[A-Za-z]*|--decode)[^\;\&\|]*\|")

# Pattern 7: rev/tr pipe-to-shell obfuscation. `| rev` / `| tr` reversed or
# filtered the pipeline text, so the bytes a reviewer saw are not the bytes
# that run the shell.
REV_TR_PIPE = re.compile(r"\|[ \t]*(?:rev|tr)[ \t]")

# Shared "a shell ends the pipeline" signal used by Patterns 2 and 7. A plain
# `| sh`/`| bash`, or one through a privilege/env wrapper with only glued
# flags or `VAR=val` assignments between (`| sudo bash`, `| env FOO=1 sh`) —
# not a whole command (`| sudo pacman -S bash`).
_SHELL_APP = r"(?:bash|sh|zsh|dash|eval)"
_SHELL_TERM = r"(?:[\s);|&<>`]|$)"
_PIPE_WRAP = r"(?:sudo|doas|pkexec|env|exec)[ \t]+"
_PIPE_WRAP_OPT = r"(?:(?:-[^ \t|;&]*|[A-Za-z_][A-Za-z0-9_]*=[^ \t|;&]*)[ \t]+)*"
PIPE_TO_SHELL = re.compile(
    r"(?:^|[^|&])\|&?[ \t]*(?:"
    r"" + _SHELL_APP + r"(?:" + _SHELL_TERM + r")"
    r"|" + _PIPE_WRAP + _PIPE_WRAP_OPT + _SHELL_APP + r"(?:" + _SHELL_TERM + r")"
    r")")

# Pattern 14: sudo/doas/pkexec at a command position. The line's quoted spans
# and a trailing comment are stripped and it's split on `; & | ( {`, so each
# command is judged on its own (a decoy `sudo -u nobody :` can't shield a
# `; sudo cp`). Must have an argument after the tool.
PRIV_ESC = re.compile(r"^(sudo|doas|pkexec)[ \t]+[^ \t]")
# su / sudoedit / run0 are likewise root-switching commands NeoArch flags.
PRIV_SWITCH = re.compile(r"^(su|sudoedit|run0)\b")
# `-u user` / `--user user` de-escalates (the documented legit idiom —
# `sudo -u "$service_user"` in build helpers), so it exempts — but a run of
# any intermediate flags is allowed, and `-u root` / `-u 0` IS the escape and
# re-invokes the finding.
PRIV_RUNAS = re.compile(
    r"^(sudo|doas)(?:[ \t]+(?:--[A-Za-z][A-Za-z-]*(?:=[^ \t]+)?|-[A-Za-z]))*"
    r"[ \t]+(?:-u(?:[ \t]|$)|--user)")
PRIV_RUNAS_ROOT = re.compile(r"(?:-u|--user)[ \t=]*\b(?:root|0)(?![A-Za-z0-9_])")

# Heredoc opener — capture the delimiter keyword so the body can be skipped
# by Pattern 14 (a here-doc payload is document text, not commands). Requires
# whitespace before `<<` (a real redirection), so a `<<` inside a quoted
# string doesn't start a phantom heredoc; `<<<` here-strings don't match.
HEREDOC_OPEN = re.compile(r"[ \t]+<<-?[ \t]*['\"]?([A-Za-z_][A-Za-z0-9_]*)")

# Pattern 17: a `.install` scriptlet creates or escalates a privileged
# account — group/wheel membership, sudoers NOPASSWD, or a hardcoded password
# piped into chpasswd/passwd. Real incident: the 2026-09-14 x11-qemu-validation
# AUR package planted a root-equivalent backdoor exactly this way via
# post_install. A PKGBUILD's package() runs under fakeroot as the calling user
# and can't touch these, and Pattern 14 already flags the sudo that would be
# needed to do it for real.
WHEEL_SUDOERS = re.compile(
    r"(?:useradd|usermod)[ \t].*-[A-Za-z]*[gG][A-Za-z]*[ \t]+[^ \t]*wheel(?![A-Za-z0-9_])"
    r"|gpasswd[ \t]+-a[ \t]+[^ \t]+[ \t]+wheel(?![A-Za-z0-9_])"
    r"|sudoers(?:\.d/[^ \t;&]*)?[^;&]*NOPASSWD"
    r"|NOPASSWD[^;&]*sudoers")
HARDCODED_PASSWD = re.compile(
    r"(?:^|[;&| \t])chpasswd(?:[ \t<]|$)"
    r"|(?:echo|printf)[ \t].*\|[ \t]*(?:"
    r"(?:sudo|doas|pkexec|env|exec)[ \t]+"
    r"(?:(?:-[^ \t|;&]*|[A-Za-z_][A-Za-z0-9_]*=[^ \t|;&]*)[ \t]+)*)?"
    r"(?:chpasswd|passwd)(?:[ \t]|$)")

# ──────────────────────────────────────────────────────────────────────────
# Supply-chain evasion & obfuscation techniques (Layered-defense rules
# ported from the pre-build scanner of `archcanary`; MIT-licensed).
# Each rule is a tuple: (compiled regex, human rule name, severity).
# Commented-out lines are exempted in the scan loop where a rule's signal
# would be destroyed by a routine `#` note.
# ──────────────────────────────────────────────────────────────────────────

# Byte-at-a-time command assembly: `$'\x63\x75\x72\x6c'` spells "curl".
# 3+ chained escapes are required so the ubiquitous `read -d $'\0'` NUL
# idiom never matches.
ANSI_C_QUOTED_BYTES = re.compile(
    r"\$'((?:\\x[0-9a-fA-F]{2}|\\[0-7]{1,3}){3,})'")

# `printf` spelling a command out a byte at a time: the escapes decode to
# letters/digits (hex: 0x30-7a; octal: \6[0-7]..\17[0-2]). Single \x1b-\x1f
# colour/control escapes are excluded by construction.
PRINTF_BYTE = re.compile(
    r"\\x(?:3[0-9]|4[1-9a-fA-F]|5[0-9aA]|6[1-9a-fA-F]|7[0-9aA])"
    r"|\\0?(?:6[0-7]|7[01]|10[1-7]|1[12][0-7]|13[0-2]|14[1-7]|1[56][0-7]|17[0-2])")

# `a=bu; b=n; $a$b` — command reassembled from a variable fragment.
VARIABLE_SPLIT_REASSEMBLY = re.compile(
    r"[a-z_]+=[A-Za-z]+\s*;\s*[a-z_]+=[A-Za-z]+\s*;\s*\$")

# Fetch proxied through Tor/SOCKS (curl -x socks5h://, --socks*, --proxy
# socks), or wrapped by torsocks/proxychains. Used to pull payloads while
# evading URL blocklists.
TOR_FETCH = re.compile(
    r"\b(curl|wget)\b[^\n]*?(-[A-Za-z]*x\s*socks[0-9]?h?://"
    r"|--socks[0-9]?h?\b|--proxy\s+socks)")
TOR_WRAPPER = re.compile(r"(^|[;&|\s])(torsocks|proxychains4?)\s")
ONION_URL = re.compile(r"\.onion([/\"'\s]|$)")

# Downloading straight into a system dir (/usr, /etc, /opt, /boot) instead
# of the makepkg sandbox — bypasses pacman's file tracking.
DOWNLOAD_TO_SYSTEM_PATH = re.compile(
    r"\b(curl|wget)\b[^\n]*?-[A-Za-z]*[oO]\s*/?(usr|etc|opt|boot)/")

# Reference to the AUR's own git SSH remote: self-propagation mechanism.
AUR_SSH_REMOTE = re.compile(r"aur@aur\.archlinux\.org")

# Mutating pacman invoked non-interactively from install-time code.
PACMAN_NONINTERACTIVE = re.compile(r"\bpacman\b[^\n]*?--noconfirm")

# Per-line rules that run inside the main scan loop.
LINE_OBFUSCATION_RULES = (
    (ANSI_C_QUOTED_BYTES, "command obfuscation", "warning",
     "a command is being assembled byte-at-a-time with ANSI-C quoting "
     "($'\\x..' / $'\\0..')"),
    (VARIABLE_SPLIT_REASSEMBLY, "command obfuscation", "warning",
     "a shell command is rebuilt from a variable fragment (a=x;b=y; $a$b)"),
    (TOR_FETCH, "Tor/SOCKS-proxied fetch", "critical",
     "network fetch routed through Tor/SOCKS - used to pull payloads while "
     "evading URL blocklists"),
    (TOR_WRAPPER, "Tor/SOCKS-proxied fetch", "critical",
     "command run through torsocks/proxychains - payload is fetched under a "
     "proxy, evading URL blocklists"),
    (ONION_URL, "Tor/SOCKS-proxied fetch", "warning",
     "reference to a .onion URL in install-time code"),
    (DOWNLOAD_TO_SYSTEM_PATH, "download to system path", "warning",
     "download writes into /usr /etc /opt /boot directly, bypassing pacman's "
     "file tracking"),
    (AUR_SSH_REMOTE, "AUR repository self-reference", "critical",
     "references ssh://aur@aur.archlinux.org - no legit PKGBUILD touches its "
     "own remote; this is the AUR self-propagation pattern"),
    (PACMAN_NONINTERACTIVE, "non-interactive pacman", "warning",
     "pacman mutating operation with --noconfirm from install-time code"),
    # printf byte-spelling is conditional: only when the line already
    # contains `printf`.
    (PRINTF_BYTE, "command obfuscation", "warning",
     "printf is spelling a command out a byte at a time"),
)

# Mutable MR/PR diff endpoints (GitHub/Gitea pulls, GitLab merge requests).
MUTABLE_PATCH_RE = re.compile(
    r"(/-/merge_requests/[0-9]+(?:\.(?:diff|patch)|/diffs)"
    r"|/pulls?/[0-9]+\.(?:diff|patch))")

# Unicode characters that are invisible or control-flow altering.
ZERO_WIDTH = re.compile(
    "[\u200b\u200c\u200d\u2060\ufeff"
    "\u202a\u202b\u202c\u202d\u202e"
    "\u2066\u2067\u2068\u2069\u200e\u200f]"
)

# Script ranges that can visually spoof Latin ASCII text.
SCRIPT_RANGES = (
    ("cyrillic", (0x0400, 0x04FF)),
    ("greek", (0x0370, 0x03FF)),
    ("armenian", (0x0530, 0x058F)),
    ("hebrew", (0x0590, 0x05FF)),
    ("arabic", (0x0600, 0x06FF)),
    ("devanagari", (0x0900, 0x097F)),
    ("fullwidth", (0xFF00, 0xFFEF)),
)

# Cyrillic/Greek characters that render like ASCII Latin letters.
CONFUSABLES = {
    # Cyrillic look-alikes
    "\u0430": "a",  # а
    "\u0435": "e",  # е
    "\u043e": "o",  # о
    "\u0440": "p",  # р
    "\u0441": "c",  # с
    "\u0445": "x",  # х
    "\u0443": "y",  # у
    "\u0410": "A",  # А
    "\u0415": "E",  # Е
    "\u041e": "O",  # О
    "\u041f": "P",  # П
    "\u0421": "C",  # С
    "\u0425": "X",  # Х
    "\u0423": "Y",  # У
    "\u0412": "B",  # В
    "\u041d": "H",  # Н
    "\u041a": "K",  # К
    "\u041c": "M",  # М
    "\u0422": "T",  # Т
    # Greek look-alikes
    "\u03bf": "o",  # ο omicron
    "\u03b9": "i",  # ι iota
    "\u03b5": "e",  # ε epsilon
    "\u03c0": "n",  # π (visual)
}


def _strip_deobfuscation(text: str) -> str:
    """Remove common obfuscation so hidden tool names are still detected.

    Handles quote injection (``b''u''n``) and backslash escapes (``cur\\l``)
    that are used to defeat naive substring matching.
    """
    cleaned = re.sub(r"['\"`]", "", text)
    cleaned = re.sub(r"\\(?=[\w])", "", cleaned)
    return cleaned


def _lookup_script(char: str) -> Optional[str]:
    cp = ord(char)
    for name, (lo, hi) in SCRIPT_RANGES:
        if lo <= cp <= hi:
            return name
    return None


def _homograph_findings(text: str, context: str) -> List[Dict]:
    """Detect Unicode homograph / mixed-script spoofing in a string."""
    findings: List[Dict] = []
    if not text:
        return findings
    if ZERO_WIDTH.search(text):
        findings.append(_finding(
            "critical",
            "Unicode homograph spoofing",
            "text contains zero-width or bidi control characters that hide "
            "the true contents (IDN homograph attack pattern)",
            context=context,
            matched=repr(text[:80]),
        ))

    scripts = set()
    for ch in text:
        script = _lookup_script(ch)
        if script:
            scripts.add(script)
    if "cyrillic" in scripts or "greek" in scripts:
        # Mixed Latin + Cyrillic/Greek strongly suggests spoofing.
        has_latin = any(("LATIN" in unicodedata.name(ch, "") and ch.isalpha())
                        for ch in text)
        if has_latin or len(text) > 1:
            findings.append(_finding(
                "critical",
                "Unicode homograph spoofing",
                f"mixed-script text ({', '.join(sorted(scripts))} + Latin) "
                "can visually impersonate an ASCII string",
                context=context,
                matched=repr(text[:80]),
            ))

    confusable_hits = [ch for ch in text if ch in CONFUSABLES]
    if confusable_hits and any(("LATIN" in unicodedata.name(ch, "") and ch.isalpha())
                               for ch in text):
        findings.append(_finding(
            "warning",
            "Unicode homograph spoofing",
            f"contains confusable characters: {', '.join(repr(c) for c in confusable_hits)}",
            context=context,
            matched=repr(text[:80]),
        ))
    return findings


def _finding(severity: str, rule: str, detail: str,
             context: str = "", matched: str = "", line: int = 0) -> Dict:
    return {
        "severity": severity,
        "rule": rule,
        "detail": detail,
        "context": context,
        "matched": matched,
        "line": line,
    }


def _url_authority(url: str) -> str:
    """Return the host authority of a URL string (Pattern 16).

    Drops a `name::` rename prefix, the scheme, any `user@`, and everything
    from the first `/ ? #`. What's left is `host[:port]` — the part a
    homoglyph check cares about. Returns "" when there is no scheme.
    """
    u = url.split("::", 1)[-1]
    _scheme, sep, rest = u.partition("://")
    if not sep:
        return ""
    authority = re.split(r"[/?#]", rest, maxsplit=1)[0]
    return authority.rsplit("@", 1)[-1]


def _command_fragments(line: str) -> List[str]:
    """Split a de-obfuscated line into command fragments (Pattern 14).

    Quotes are consumed as spans first (so `echo "sudo x"` can't anchor),
    then a trailing inline comment, then the line is cut on the shell
    separators `; & | ( {` so each command is judged independently. Quotes
    are stripped so `sudo -u "root"` still resolves for the run-as re-check.
    """
    text = re.sub(r'"[^"]*"|\'[^\']*\'', "", line)
    text = re.sub(r"[ \t]#.*$", "", text)
    text = re.sub(r"['\"]", "", text)
    return [frag.strip() for frag in re.split(r"[;&|({]", text) if frag.strip()]


def _iter_scan_lines(text: str):
    """Yield (raw, stripped, in_heredoc, is_comment) for each line, with
    Pattern 14's heredoc-body tracking. A line is "inside a heredoc" if a
    delimiter was open when it started; the line consisting of the delimiter
    word closes it. Here-string (`<<<`) lines never open a heredoc."""
    heredoc_delim: Optional[str] = None
    for raw in text.splitlines():
        line = raw.strip()
        in_heredoc = False
        if heredoc_delim is not None:
            in_heredoc = True
            if line == heredoc_delim:
                heredoc_delim = None
        else:
            m = HEREDOC_OPEN.search(line)
            if m:
                heredoc_delim = m.group(1)
        yield raw, line, in_heredoc, line.startswith("#")


def _elevation_findings_for_line(line: str, stripped: str, obfuscated: bool,
                                 context: str, abs_line: int) -> List[Dict]:
    """Pattern 14 per-line elevation check (command-anchored).

    sudo/doas/pkexec (plus su/sudoedit/run0) only count at a command
    position. A `-u user` / `--user user` run-as is the documented legit
    de-escalation idiom and is exempt — but `-u root` / `-u 0` IS the
    privilege escape and re-flags. Returns at most one finding per line.
    """
    findings: List[Dict] = []
    for frag in _command_fragments(stripped):
        m = PRIV_ESC.match(frag) or PRIV_SWITCH.match(frag)
        if not m:
            continue
        tool = m.group(1)
        if tool in ("sudo", "doas") and PRIV_RUNAS.match(frag) \
                and not PRIV_RUNAS_ROOT.search(frag):
            continue
        if obfuscated:
            findings.append(_finding(
                "critical",
                "obfuscated tool name",
                f"'{tool}' was deliberately obfuscated (e.g. s''udo "
                "or su\\do) — strong malicious indicator",
                context=context, matched=line, line=abs_line,
            ))
        else:
            findings.append(_finding(
                "critical",
                "privilege elevation",
                f"'{tool}' runs package-controlled code as root "
                "outside the package manager",
                context=context, matched=line, line=abs_line,
            ))
        break
    return findings


# ──────────────────────────────────────────────────────────────────────────
# Line-based scanning
# ──────────────────────────────────────────────────────────────────────────

def scan_text(text: str, context: str = "", base_dir: str = "",
              source_files: Optional[List[str]] = None,
              src_line: int = 0, install_scriptlet: bool = False) -> List[Dict]:
    """Scan raw text (a PKGBUILD or install script) for risky patterns.

    Args:
        text: The file contents to scan.
        context: Label for the finding (e.g. "post_install", "build()").
        base_dir: Directory to resolve relative source=() paths against.
        source_files: Explicit list of local source filenames to check.
        src_line: Starting line offset for findings (for .install files).
        install_scriptlet: True when text is a .install scriptlet body
            (enables Pattern 17's privileged-account check, which only makes
            sense where the code runs as root).

    Returns:
        list: Findings, each {severity, rule, detail, context, matched, line}.
    """
    findings: List[Dict] = []

    for line_no, (_raw, line, in_heredoc, is_comment) in enumerate(
            _iter_scan_lines(text), start=1):
        stripped = _strip_deobfuscation(line)
        obfuscated = stripped != line

        for tool in RISKY_TOOLS:
            if re.search(rf"(^|[^-\w]){re.escape(tool)}\b", stripped):
                if obfuscated:
                    findings.append(_finding(
                        "warning",
                        "obfuscated tool name",
                        f"'{tool}' was deliberately obfuscated (e.g. b''u''n "
                        "or cur\\l) — strong malicious indicator",
                        context=context, matched=line, line=line_no + src_line,
                    ))
                elif not is_comment:
                    findings.append(_finding(
                        "warning",
                        "risky post-install tool",
                        f"'{tool}' can download or execute external code "
                        "outside libalpm's control",
                        context=context, matched=line, line=line_no + src_line,
                    ))

        # Pattern 14: command-anchored privilege elevation. Comments and
        # heredoc bodies can't execute, so they're exempt (a `# sudo pacman
        # -U --noconfirm` build reminder is a known FP).
        if not in_heredoc and not is_comment:
            findings.extend(_elevation_findings_for_line(
                line, stripped, obfuscated, context, line_no + src_line))

        # Pattern 1: known-malicious npm/bun package names.
        if MALICIOUS_NPM_INSTALL.search(stripped):
            for pkg in MALICIOUS_NPM_PACKAGES:
                if pkg in stripped:
                    findings.append(_finding(
                        "warning",
                        "malicious package install",
                        f"install of '{pkg}' — a package named in the June "
                        "2026 AUR publisher supply-chain campaign; the post-"
                        "install code is attacker-controlled",
                        context=context, matched=line, line=line_no + src_line,
                    ))
                    break

        if not is_comment:
            # Pattern 2: base64 decode piped into a shell.
            if BASE64_DECODE_PIPE.search(line) and PIPE_TO_SHELL.search(line):
                findings.append(_finding(
                    "warning",
                    "base64 decode into shell",
                    "base64 output is piped into a shell — the bytes decode "
                    "to commands that can't be reviewed ahead of time",
                    context=context, matched=line, line=line_no + src_line,
                ))

            # Pattern 7: rev/tr pipe-to-shell obfuscation.
            if REV_TR_PIPE.search(line) and PIPE_TO_SHELL.search(line):
                findings.append(_finding(
                    "warning",
                    "rev/tr pipe-to-shell obfuscation",
                    "'| rev' / '| tr' reversed or filtered the pipeline text "
                    "feeding a shell — the commands a reviewer sees are not "
                    "the bytes that run",
                    context=context, matched=line, line=line_no + src_line,
                ))

        # Pattern 17: a .install scriptlet (runs as root) creating a
        # privileged account. PKGBUILD package() runs under fakeroot and can't
        # touch wheel/sudoers/passwords, so the check is scriptlet-only.
        if install_scriptlet and not is_comment \
                and (WHEEL_SUDOERS.search(line) or HARDCODED_PASSWD.search(line)):
            findings.append(_finding(
                "warning",
                "privileged account creation",
                "scriptlet changes group/wheel membership, sudoers, or sets "
                "a login password — the 2026-09-14 x11-qemu-validation AUR "
                "incident planted a root-equivalent backdoor exactly this way",
                context=context, matched=line, line=line_no + src_line,
            ))

        if not is_comment:
            for pattern, label in DYNAMIC_PATTERNS:
                if re.search(pattern, stripped):
                    findings.append(_finding(
                        "warning",
                        "dynamic command construction",
                        f"{label} cannot be safely reviewed ahead of time",
                        context=context, matched=line, line=line_no + src_line,
                    ))

            for pattern, label in RAW_LINE_PATTERNS:
                if re.search(pattern, line):
                    findings.append(_finding(
                        "warning",
                        "dynamic command construction",
                        f"{label} cannot be safely reviewed ahead of time",
                        context=context, matched=line, line=line_no + src_line,
                    ))

        if not line.startswith("#"):
            for regex, rule, severity, detail in LINE_OBFUSCATION_RULES:
                if regex is PRINTF_BYTE:
                    if "printf" in line and regex.search(line):
                        findings.append(_finding(
                            severity, rule, detail,
                            context=context, matched=line,
                            line=line_no + src_line,
                        ))
                elif regex.search(line):
                    findings.append(_finding(
                        severity, rule, detail,
                        context=context, matched=line,
                        line=line_no + src_line,
                    ))

    # Homograph checks across the whole document (names, URLs, deps)
    for field_name in ("pkgname", "pkgdesc", "url", "depends"):
        matches = re.findall(rf"^\s*{field_name}\s*=\s*(.+)$", text, re.M)
        for m in matches:
            value = m
            if field_name == "url":
                # Pattern 16: only the host authority of a URL is checked — a
                # non-ASCII byte in a path/query (`/wiki/Программа`) is a
                # legitimate repo/file name and stays unflagged.
                tokens = value.strip().split(None, 1)
                value = _url_authority(tokens[0].strip("\"'")) if tokens else ""
            findings.extend(_homograph_findings(value, context or field_name))

    # Local source files that are binary/ELF cannot be reviewed as text
    for fname in source_files or []:
        if _local_source_is_binary(fname, base_dir):
            findings.append(_finding(
                "critical",
                "local binary source",
                f"source file '{os.path.basename(fname)}' appears to be "
                "binary/ELF content and cannot be reviewed as text",
                context=context, matched=fname,
            ))

    return findings


def _local_source_is_binary(fname: str, base_dir: str) -> bool:
    """Return True if a local (non-URL) source file is binary/ELF."""
    if not fname or "://" in fname:
        return False
    path = os.path.join(base_dir, fname) if base_dir else fname
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "rb") as f:
            head = f.read(1024)
    except Exception:
        return False
    if head.startswith(b"\x7fELF"):
        return True
    return b"\x00" in head


# ──────────────────────────────────────────────────────────────────────────
# File-level entry points
# ──────────────────────────────────────────────────────────────────────────

def _parse_pkgbuild_sources(text: str) -> List[str]:
    """Parse source=() arrays from a PKGBUILD (best effort)."""
    items: List[str] = []
    for m in re.finditer(r"\bsource\s*\(?\+?\s*=\s*\(", text):
        depth = 1
        i = m.end()
        while i < len(text) and depth:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
            i += 1
        inner = text[m.end():i - 1]
        try:
            items.extend(shlex.split(inner))
        except ValueError:
            continue
    return items


def _parse_install_scriptlets(text: str) -> Dict[str, str]:
    """Extract .install scriptlet bodies (post_install, pre_install, etc.)."""
    scriptlets: Dict[str, str] = {}
    matches = re.finditer(
        r"^\s*(post_install|pre_install|pre_upgrade|post_upgrade|"
        r"pre_remove|post_remove)\s*\(\s*\)\s*\{", text, re.M)
    for m in matches:
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        scriptlets[m.group(1)] = text[start:i - 1]
    return scriptlets


def _duplicate_source_decl(header: str) -> List[Dict]:
    """Flag a source=() key assigned twice by a bare `=` (the later one
    silently discards the earlier). A deliberate duplicate is either dead
    build-variant logic or a staged-but-not-armed payload (real incident:
    storageexplorer-bin pretended source=() above its real one). `+=`
    appends and never discards, so it alone never matches — but a prior
    `+=` still counts as already-assigned for catching a later bare `=`."""
    findings: List[Dict] = []
    seen = {}
    for raw in header.splitlines():
        m = re.match(r"^\s*(source(?:_[A-Za-z0-9_]+)?)(\+?)=\(", raw)
        if not m:
            continue
        key, operator = m.group(1), m.group(2)
        if not operator and key in seen:
            findings.append(_finding(
                "warning",
                "duplicate source declaration",
                f"{key}=() is declared more than once; makepkg honors only the "
                "last assignment, so the earlier one is dead code (a known "
                "staging trick)",
                matched=raw.strip(),
            ))
        seen[key] = True
    return findings


def _parse_pkgbuild_checksums(text: str) -> List[str]:
    """Parse sha256sums=() arrays (best effort), mirroring source parsing."""
    items: List[str] = []
    for m in re.finditer(r"\bsha2?56sums?\s*\(?\+?\s*=\s*\(", text):
        depth = 1
        i = m.end()
        while i < len(text) and depth:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
            i += 1
        inner = text[m.end():i - 1]
        try:
            items.extend(shlex.split(inner))
        except ValueError:
            continue
    return items


def _mutable_patch_source(text: str) -> List[Dict]:
    """Flag a source=() entry pointing at a mutable MR/PR diff URL that no
    sha256sums=() entry pins. A /commit/<sha>.patch is immutable and fine; a
    /pull/<n>.diff changes on every push, so it can be swapped after review.
    Checksums pair positionally with source=() entries."""
    findings: List[Dict] = []
    sources = _parse_pkgbuild_sources(text)
    checksums = _parse_pkgbuild_checksums(text)
    for idx, src in enumerate(sources):
        if not MUTABLE_PATCH_RE.search(src):
            continue
        pin = checksums[idx] if idx < len(checksums) and checksums[idx] else ""
        if pin and pin.upper() != "SKIP":
            continue
        findings.append(_finding(
            "warning",
            "mutable patch source",
            f"source '{src}' is a mutable MR/PR diff/patch endpoint and is "
            "not pinned by a sha256sum — it can change to different content "
            "after review",
            matched=src,
        ))
    return findings


def scan_install_scriptlet(scriptlet_text: str, name: str) -> List[Dict]:
    """Scan a single extracted scriptlet body."""
    return scan_text(scriptlet_text, context=name, src_line=0,
                     install_scriptlet=True)


def _pkgbuild_unicode_hosts(text: str) -> List[Dict]:
    """Pattern 16: look-alike / hidden characters in the HOST authority of a
    top-level `url=` scalar or a `source=`/`source_$CARCH=()` URL entry.
    Only the host is checked; a non-ASCII byte in a URL path is a legitimate
    repo/file name and local (non-URL) source filenames are skipped."""
    findings: List[Dict] = []
    for m in re.finditer(r"(?m)^url[ \t]*=[ \t]*([^\s#]+)", text):
        host = _url_authority(m.group(1).strip("\"'"))
        if host:
            findings.extend(_homograph_findings(host, "url"))
    for src in _parse_pkgbuild_sources(text):
        if "://" not in src:
            continue
        host = _url_authority(src)
        if host:
            findings.extend(_homograph_findings(host, "source"))
    return findings


def _parse_build_package_bodies(text: str) -> List[tuple]:
    """Extract `build()`, `package()` and their arch-variant function bodies
    for the Pattern 14 sub-scan. `scan_pkgbuild` otherwise cuts at the first
    function definition, so these bodies aren't reached via the header scan."""
    bodies: List[tuple] = []
    for m in re.finditer(
            r"(?m)^[ \t]*(build|[a-z_]*package)(_[A-Za-z0-9_]+)?"
            r"[ \t]*\([ \t]*\)[ \t]*\{", text):
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        bodies.append((m.group(1) + (m.group(2) or ""), text[start:i - 1]))
    return bodies


def _scan_function_elevation(text: str) -> List[Dict]:
    """Pattern 14 sub-scan of build()/package() bodies.

    build()/package() run as the calling user (package() under fakeroot), so
    sudo/doas/pkexec here writes outside $pkgdir onto the live system,
    bypassing pacman's file tracking — but a `-u` non-root run-as is the
    documented legit idiom and stays exempt.
    """
    findings: List[Dict] = []
    for name, body in _parse_build_package_bodies(text):
        for line_no, (_raw, line, in_heredoc, is_comment) in enumerate(
                _iter_scan_lines(body), start=1):
            if in_heredoc or is_comment:
                continue
            stripped = _strip_deobfuscation(line)
            findings.extend(_elevation_findings_for_line(
                line, stripped, stripped != line, name, line_no))
    return findings


def _git_tracked_elf_findings(base_dir: str) -> List[Dict]:
    """Pattern 8: an undocumented ELF binary committed to the package's own
    git tree. A source-based PKGBUILD has no reason to ship a compiled binary
    in its AUR repo — -bin packages fetch theirs into src/ via source=() at
    build time. Only files tracked in the package's own git repo are flagged:
    a raw-binary source=() downloads into this same top-level dir as a normal
    build step, and a dir with no git repo at all is treated as untracked
    (err toward not flagging rather than FP on every raw-binary -bin pkg)."""
    findings: List[Dict] = []
    if not base_dir or not os.path.isdir(base_dir):
        return findings
    try:
        entries = list(os.scandir(base_dir))
    except OSError:
        return findings
    for entry in entries:
        path = os.path.join(base_dir, entry.name)
        try:
            with open(path, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    continue
        except OSError:
            continue
        try:
            rc = subprocess.run(
                ["git", "-C", base_dir, "ls-files", "--error-unmatch", "--",
                 entry.name],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            ).returncode
        except OSError:
            continue
        if rc != 0:
            continue
        findings.append(_finding(
            "warning",
            "undocumented ELF binary",
            f"'{entry.name}' is an ELF binary tracked in the package's own "
            "git tree — source-based PKGBUILDs don't ship compiled binaries "
            "in their repo; inspect before building (file / strings)",
        ))
    return findings


def _split_header(text: str) -> str:
    """Return the PKGBUILD variable-assignment header, cut at the first
    function definition so build()/package() bodies aren't double-scanned."""
    m = re.search(r"(?m)^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\(\s*\)\s*\{", text)
    return text[:m.start()] if m else text


def scan_pkgbuild(text: str, base_dir: str = "") -> List[Dict]:
    """Scan a full PKGBUILD, including its .install scriptlets.

    Args:
        text: PKGBUILD contents.
        base_dir: Directory containing local source files.

    Returns:
        list: Findings across the PKGBUILD header and scriptlets.
    """
    header = _split_header(text)
    findings = scan_text(header, context="PKGBUILD", base_dir=base_dir,
                         source_files=_parse_pkgbuild_sources(header))
    findings.extend(_duplicate_source_decl(header))
    findings.extend(_mutable_patch_source(header))
    findings.extend(_pkgbuild_unicode_hosts(header))
    findings.extend(_scan_function_elevation(text))
    findings.extend(_git_tracked_elf_findings(base_dir))
    for name, body in _parse_install_scriptlets(text).items():
        findings.extend(scan_install_scriptlet(body, name))
    return findings


def findings_for_file(path: str) -> List[Dict]:
    """Scan a PKGBUILD (or .install file) on disk. Returns [] on error."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return []
    base_dir = os.path.dirname(path)
    if os.path.basename(path).endswith(".install"):
        return scan_install_scriptlet(text, os.path.basename(path))
    return scan_pkgbuild(text, base_dir)
