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
import unicodedata
from typing import Dict, List, Optional

__all__ = [
    "scan_pkgbuild", "scan_install_scriptlet", "findings_for_file",
    "RISKY_TOOLS", "ELEVATION_TOOLS", "DYNAMIC_PATTERNS",
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
    (r"base64\s+(-d|--decode|--d)", "decode-into-shell"),
    (r"openssl\s+.*\|\s*(sh|bash)\b", "decrypt-into-shell"),
    (r"\|\s*(sh|bash)\b", "pipe to shell"),
)

# Patterns that must be matched against the RAW line (de-obfuscation would
# destroy the signal).
RAW_LINE_PATTERNS = (
    (r"(?<!\\)`", "command substitution (backticks)"),
)

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


# ──────────────────────────────────────────────────────────────────────────
# Line-based scanning
# ──────────────────────────────────────────────────────────────────────────

def scan_text(text: str, context: str = "", base_dir: str = "",
              source_files: Optional[List[str]] = None,
              src_line: int = 0) -> List[Dict]:
    """Scan raw text (a PKGBUILD or install script) for risky patterns.

    Args:
        text: The file contents to scan.
        context: Label for the finding (e.g. "post_install", "build()").
        base_dir: Directory to resolve relative source=() paths against.
        source_files: Explicit list of local source filenames to check.
        src_line: Starting line offset for findings (for .install files).

    Returns:
        list: Findings, each {severity, rule, detail, context, matched, line}.
    """
    findings: List[Dict] = []
    deobf = _strip_deobfuscation(text)

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
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
                else:
                    findings.append(_finding(
                        "warning",
                        "risky post-install tool",
                        f"'{tool}' can download or execute external code "
                        "outside libalpm's control",
                        context=context, matched=line, line=line_no + src_line,
                    ))

        for tool in ELEVATION_TOOLS:
            if re.search(rf"(^|[^-\w]){re.escape(tool)}\b", stripped):
                if obfuscated:
                    findings.append(_finding(
                        "critical",
                        "obfuscated tool name",
                        f"'{tool}' was deliberately obfuscated (e.g. s''udo "
                        "or su\\do) — strong malicious indicator",
                        context=context, matched=line, line=line_no + src_line,
                    ))
                else:
                    findings.append(_finding(
                        "critical",
                        "privilege elevation",
                        f"'{tool}' runs package-controlled code as root "
                        "outside the package manager",
                        context=context, matched=line, line=line_no + src_line,
                    ))

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
            findings.extend(_homograph_findings(m, context or field_name))

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
    return scan_text(scriptlet_text, context=name, src_line=0)


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
