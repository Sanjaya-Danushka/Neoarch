"""Best-effort package → repository map, built once from ``pacman -Sl``.

``pacman -Sl`` lists every package in the synced repo databases under
/var/lib/pacman/sync, so building the map never touches the network and
never needs root. First match wins, in pacman.conf repo order, which
mirrors pacman's own resolution priority.

The map is stored in a module-level cache. Frontend code should prewarm
it in a background thread (see UpdatesTable._start_repo_prewarm) and look
it up with ``get_repo_map()`` for O(1) row stamping.
"""

import subprocess

from neoarch.backend.sys_utils import c_locale_env

_repo_map = {}


def parse_repo_list(stdout, first_wins=True):
    """Parse ``pacman -Sl`` output into {package: repo}.

    Keeps the first repo that lists a package (pacman resolution order);
    a package can appear under several synced repos (e.g. testing first).
    """
    mapping = {}
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        name = parts[1]
        if first_wins and name in mapping:
            continue
        mapping[name] = parts[0]
    return mapping


def refresh_repo_map(timeout=60):
    """(Re)build the module-level map; the cache is cleared if pacman fails."""
    global _repo_map
    new_map = {}
    try:
        proc = subprocess.run(
            ["pacman", "-Sl"],
            capture_output=True, text=True, timeout=timeout, check=False,
            env=c_locale_env(),
        )
        if proc.returncode == 0 and proc.stdout:
            new_map = parse_repo_list(proc.stdout)
    except Exception:
        pass
    _repo_map = new_map
    return new_map


def get_repo_map():
    """Return the current cached {package: repo} map ({} until prewarmed)."""
    return _repo_map