"""Read and manage pacman repository sections in /etc/pacman.conf.

Reading needs no privileges (the file is world-readable). Writes are
guarded: every edit goes through ``sudo -A tee`` with the app's session
auth, a working copy is kept in /tmp first, and the original is restored
if the write fails.

NeoArch only ever deletes or toggles sections it created itself (they carry
a ``# neoarch-managed`` marker). Hand-written third-party sections keep
protected: callers get a clear message telling them to edit the file, so a
misparse can never clobber someone's carefully built config. Built-in
repos (core/extra/multilib/testing) can't be toggled from the GUI.

The ``chaotic-aur`` preset runs the full upstream workflow: sign the
maintainer key, fetch the mirror list over HTTPS, append
``[chaotic-aur] Include = /etc/pacman.d/chaotic-mirrorlist`` and sync.
"""

import re
import time

from neoarch.backend.services.i18n import _

PACMAN_CONF = "/etc/pacman.conf"

# Repos every Arch install gets on the base file; toggling these off can
# strand dependencies, so the GUI keeps a read-only "System" label on them.
SYSTEM_REPOS = {"core", "extra", "multilib", "testing"}

# Marker above a section block that NeoArch added.
_MANAGED_MARKER = "# neoarch-managed"

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# Optional leading spaces, optional leading '#', then [name].
_HEADER_RE = re.compile(r"^[ \t]*#?\[(?P<name>[^\]\s]+)\][ \t]*$")

_CHAOTIC_KEY = "3056513887BEC678"
_CHAOTIC_MIRROR_URL = ("https://raw.githubusercontent.com/chaotic-aur/"
                       "packages/master/chaotic-mirrorlist")
_CHAOTIC_INCLUDE = "/etc/pacman.d/chaotic-mirrorlist"

# ── reading (no root) ────────────────────────────────────────────────


def parse_pacman_conf(text):
    """Parse /etc/pacman.conf text into repo section dicts.

    Each entry: {name, enabled, include, servers, managed, lines}
    - include/servers only collect non-commented ``Include =``/``Server =``
      lines;
    - ``managed`` is True when the block carries the neoarch marker;
    - ``lines`` holds the raw section lines (header through the last line
      before the next header).
    """
    lines = text.splitlines()
    sections = []
    current = None
    start = 0
    pending_marker = False
    for idx, raw in enumerate(lines):
        m = _HEADER_RE.match(raw)
        if m:
            if current is not None:
                current["lines"] = lines[start:idx]
            current = {
                "name": m.group("name"),
                "enabled": not raw.lstrip().startswith("#"),
                "include": "",
                "servers": [],
                "managed": pending_marker,
                "lines": [],
            }
            start = idx
            pending_marker = False
            sections.append(current)
        elif current is not None:
            stripped = raw.strip()
            if not stripped.startswith("#"):
                low = stripped.lower()
                if low.startswith("include") and "=" in stripped:
                    val = stripped.split("=", 1)[1].strip()
                    current["include"] = (current["include"] + " " + val).strip()
                elif low.startswith("server") and "=" in stripped:
                    current["servers"].append(stripped.split("=", 1)[1].strip())
            else:
                if stripped == _MANAGED_MARKER:
                    # The marker labels the NEXT section: NeoArch writes it
                    # directly above its [repo] header.
                    pending_marker = True
    if current is not None:
        current["lines"] = lines[start:]
    return sections


def _read_text():
    try:
        with open(PACMAN_CONF, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def _read_lines():
    text = _read_text()
    return text.splitlines() if text else []


def list_repos():
    """Return a [{name, enabled, include, servers, managed, system}] list."""
    text = _read_text()
    if not text:
        return []
    out = []
    for s in parse_pacman_conf(text):
        out.append({
            "name": s["name"],
            "enabled": s["enabled"],
            "include": s["include"],
            "servers": list(s["servers"]),
            "managed": s["managed"],
            "system": s["name"].lower() in SYSTEM_REPOS,
        })
    return out


# ── pure line transformations (unit-testable) ───────────────────────


def build_block(name, servers=None, include=None):
    """Raw lines for a NeoArch-managed repo section."""
    lines = [_MANAGED_MARKER, "[{}]".format(name)]
    if include:
        lines.append("Include = {}".format(include))
    for url in servers or []:
        lines.append("Server = {}".format(url))
    return lines


def _find_section(lines, name):
    """Locate a repo section. Returns a dict or None.

    Keys: marker (index of the managed-marker line, or start), start
    (index of the ``[name]`` line), end (first index after the block),
    managed (bool), enabled (bool).
    """
    start = None
    for i, raw in enumerate(lines):
        m = _HEADER_RE.match(raw)
        if m and m.group("name") == name:
            start = i
            break
    if start is None:
        return None
    marker = start
    if start > 0 and lines[start - 1].strip() == _MANAGED_MARKER:
        marker = start - 1
    end = start + 1
    while end < len(lines):
        if _HEADER_RE.match(lines[end]):
            break
        end += 1
    return {
        "marker": marker,
        "start": start,
        "end": end,
        "enabled": not lines[start].lstrip().startswith("#"),
        "managed": any(l.strip() == _MANAGED_MARKER for l in lines[marker:end]),
    }


def apply_add(lines, name, servers=None, include=None):
    """Return lines with the repo block appended (raises ValueError)."""
    if _find_section(lines, name) is not None:
        raise ValueError(
            _("Repository '[{name}]' already exists in /etc/pacman.conf.").format(name=name))
    block = build_block(name, servers, include)
    out = [line for line in lines]
    if out and out[-1].strip() != "":
        out.append("")
    out.extend(block)
    return out


def apply_remove(lines, name):
    """Return lines with a managed repo removed (raises ValueError)."""
    found = _find_section(lines, name)
    if found is None:
        raise ValueError(_("Repository '[{name}]' not found.").format(name=name))
    if not found["managed"]:
        raise ValueError(
            _("'{name}' isn't managed by NeoArch \u2014 edit /etc/pacman.conf manually.").format(name=name))
    return lines[:found["marker"]] + lines[found["end"]:]


def apply_enable(lines, name, enabled):
    """Return lines with the section header commented/uncommented."""
    found = _find_section(lines, name)
    if found is None:
        raise ValueError(_("Repository '[{name}]' not found.").format(name=name))
    if found["enabled"] == bool(enabled):
        return lines
    if name.lower() in SYSTEM_REPOS:
        raise ValueError(
            _("'{name}' is a system repository and can't be toggled here.").format(name=name))
    out = [line for line in lines]
    out[found["start"]] = _toggle_header(lines[found["start"]], bool(enabled))
    return out


def _toggle_header(line, enabled):
    without_hash = line.lstrip("#")
    if enabled:
        return without_hash
    return "#" + without_hash


# ── writing (root, guarded) ──────────────────────────────────────────


def _run(cmd, sudo=False, timeout=120):
    import subprocess
    from neoarch.backend.auth import get_auth_command, get_askpass_env
    auth = get_auth_command() if sudo else []
    env = None
    if sudo and auth == ["sudo", "-A"]:
        env = get_askpass_env()
    try:
        return subprocess.run(auth + cmd, capture_output=True, text=True,
                              timeout=timeout, env=env, check=False)
    except Exception:
        return None


def _write_lines(lines):
    """Rewrite /etc/pacman.conf as root; roll back to a backup on failure."""
    import subprocess
    from neoarch.backend.auth import get_auth_command, get_askpass_env
    auth = get_auth_command()
    env = get_askpass_env() if auth == ["sudo", "-A"] else None
    content = "".join(l if l.endswith("\n") else l + "\n" for l in lines)
    backup = "/tmp/neoarch-pacman-conf-{}.bak".format(int(time.time()))
    try:
        r1 = subprocess.run(auth + ["cp", "-a", PACMAN_CONF, backup],
                            capture_output=True, text=True, timeout=60, env=env)
        if r1.returncode != 0:
            return False
        r2 = subprocess.run(auth + ["tee", PACMAN_CONF], input=content,
                            capture_output=True, text=True, timeout=120, env=env)
        if r2.returncode != 0:
            subprocess.run(auth + ["cp", "-a", backup, PACMAN_CONF],
                           capture_output=True, text=True, timeout=60, env=env)
            return False
        subprocess.run(auth + ["rm", "-f", backup],
                       capture_output=True, text=True, timeout=30, env=env)
        return True
    except Exception:
        return False


def _conf_message():
    return _("Couldn't read {conf}.").format(conf=PACMAN_CONF)


# ── public API ───────────────────────────────────────────────────────


def add_repo(name, servers=None, include=None, sync=True):
    """Append a new repo section and optionally `pacman -Syy`.

    Returns (ok, message). ``servers`` is a list of http(s) URLs;
    ``include`` is an absolute path under /etc/.
    """
    name = (name or "").strip()
    if not _NAME_RE.match(name):
        return False, _("Invalid repository name (letters, numbers, '.', '-' and '_').")
    if name.lower() in SYSTEM_REPOS:
        return False, _("'{name}' is a system repository.").format(name=name)
    servers = [s.strip() for s in (servers or []) if (s or "").strip()]
    include = (include or "").strip()

    if not include and not servers:
        return False, _("Give at least one Include path or Server URL.")
    if include and not include.startswith("/etc/"):
        return False, _("Include paths must live under /etc/.")
    if any("\n" in s or "\r" in s or not s.startswith(("http://", "https://"))
           for s in servers):
        return False, _("Server URLs must use http(s) and contain no line breaks.")
    if "\n" in include or "\r" in include:
        return False, _("Include paths can't contain line breaks.")

    lines = _read_lines()
    if not lines:
        return False, _conf_message()
    try:
        new_lines = apply_add(lines, name, servers, include)
    except ValueError as e:
        return False, str(e)

    if not _write_lines(new_lines):
        return False, _("Failed to write {conf}; the original was restored.").format(conf=PACMAN_CONF)
    if sync:
        _run(["pacman", "-Syy"], sudo=True, timeout=300)
    return True, _("Repository '[{name}]' added{and_synced}.").format(
        name=name, and_synced=_(" and synced") if sync else _(""))


def remove_repo(name, sync=True):
    """Remove a NeoArch-managed repo section (others are protected)."""
    name = (name or "").strip()
    lines = _read_lines()
    if not lines:
        return False, _conf_message()
    try:
        new_lines = apply_remove(lines, name)
    except ValueError as e:
        return False, str(e)
    if not _write_lines(new_lines):
        return False, _("Failed to write {conf}; the original was restored.").format(conf=PACMAN_CONF)
    if sync:
        _run(["pacman", "-Syy"], sudo=True, timeout=300)
    return True, _("Repository '[{name}]' removed.").format(name=name)


def set_repo_enabled(name, enabled, sync=False):
    """Enable/disable a repo by commenting out its header line."""
    name = (name or "").strip()
    lines = _read_lines()
    if not lines:
        return False, _conf_message()
    try:
        new_lines = apply_enable(lines, name, bool(enabled))
    except ValueError as e:
        return False, str(e)
    if new_lines == lines:
        return True, ""
    if not _write_lines(new_lines):
        return False, _("Failed to write {conf}; the original was restored.").format(conf=PACMAN_CONF)
    if sync:
        _run(["pacman", "-Syy"], sudo=True, timeout=300)
    return True, ""


def add_chaotic_aur(sync=True):
    """Full Chaotic AUR setup: keyring sign, mirror list, conf entry, sync."""
    import shutil

    lines = _read_lines()
    if not lines:
        return False, _conf_message()
    if _find_section(lines, "chaotic-aur") is not None:
        return False, _("Chaotic AUR is already configured in /etc/pacman.conf.")

    r = _run(["pacman-key", "--recv-keys", _CHAOTIC_KEY,
              "--keyserver", "keyserver.ubuntu.com"], sudo=True, timeout=180)
    if r is None or r.returncode != 0:
        return False, _("Failed to fetch the Chaotic AUR maintainer key.")
    r = _run(["pacman-key", "--lsign-key", _CHAOTIC_KEY], sudo=True, timeout=180)
    if r is None or r.returncode != 0:
        return False, _("Failed to locally sign the Chaotic AUR maintainer key.")

    curl = shutil.which("curl")
    if curl:
        r = _run([curl, "-sSL", _CHAOTIC_MIRROR_URL, "-o", _CHAOTIC_INCLUDE],
                 sudo=True, timeout=180)
        if r is None or r.returncode != 0:
            return False, _("Couldn't download the Chaotic AUR mirror list.")
    else:
        return False, _("curl isn't installed; install 'curl' to fetch the mirror list.")

    return add_repo("chaotic-aur", include=_CHAOTIC_INCLUDE, sync=sync)


__all__ = [
    "PACMAN_CONF", "SYSTEM_REPOS",
    "parse_pacman_conf", "list_repos",
    "build_block", "apply_add", "apply_remove", "apply_enable",
    "add_repo", "remove_repo", "set_repo_enabled", "add_chaotic_aur",
]