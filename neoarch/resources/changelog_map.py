"""Curated, offline release-notes map used by the update-review dialog.

There is no unified source of software changelogs, so NeoArch ships a small,
hand-curated map of package name -> human-readable release-notes page.  It is
loaded only when the update-review dialog opens and is purely additive:
packages that are not in the map simply show no notes link (current behavior).

Lookups are keyed on Arch package names.  Flatpak packages arrive with reverse
DNS app IDs (e.g. ``org.mozilla.firefox``), so a small alias table resolves
those back to an Arch-style name.  npm has no canonical per-package changelog
and is intentionally left un-mapped.

Maintenance notes:
    * Keep entries to stable, long-lived URLs (project sites / release feeds).
    * Never point at a volatile URL that requires JS or a login to read.
    * Add/remove entries with pull requests; keep the mapping alphabetized.
"""

from types import MappingProxyType

__all__ = ["CHANGELOG_MAP", "FLATPAK_ALIASES", "get_changelog_url"]

# Lower-case Arch package name -> release-notes URL.
_CHANGELOG_MAP = {
    "audacity": "https://github.com/audacity/audacity/releases",
    "blender": "https://www.blender.org/download/releases/",
    "brave-bin": "https://brave.com/latest/",
    "brave-browser": "https://brave.com/latest/",
    "btop": "https://github.com/aristocratos/btop/releases",
    "chromium": "https://chromereleases.googleblog.com/",
    "code": "https://code.visualstudio.com/updates",
    "curl": "https://curl.se/changes.html",
    "emacs": "https://www.gnu.org/software/emacs/history.html",
    "firefox": "https://www.mozilla.org/en-US/firefox/releases/",
    "firefox-developer-edition": "https://www.mozilla.org/en-US/firefox/developer/releases/",
    "gimp": "https://www.gimp.org/release-notes/",
    "git": "https://git-scm.com/docs/RelNotes/",
    "htop": "https://github.com/htop-dev/htop/releases",
    "inkscape": "https://inkscape.org/release/",
    "linux": "https://kernelnewbies.org/LinuxChanges",
    "linux-hardened": "https://kernelnewbies.org/LinuxChanges",
    "linux-lts": "https://kernelnewbies.org/LinuxChanges",
    "linux-zen": "https://kernelnewbies.org/LinuxChanges",
    "libreoffice-fresh": "https://wiki.documentfoundation.org/ReleaseNotes/",
    "libreoffice-still": "https://wiki.documentfoundation.org/ReleaseNotes/",
    "mesa": "https://docs.mesa3d.org/relnotes/",
    "neovim": "https://github.com/neovim/neovim/releases",
    "nginx": "http://nginx.org/en/CHANGES",
    "nodejs": "https://nodejs.org/en/blog/release/",
    "nodejs-lts": "https://nodejs.org/en/blog/release/",
    "obs-studio": "https://github.com/obsproject/obs-studio/releases",
    "openssh": "https://www.openssh.com/releasenotes.html",
    "php": "https://www.php.net/releases/",
    "postgresql": "https://www.postgresql.org/docs/release/",
    "qemu": "https://wiki.qemu.org/ChangeLog/",
    "qemu-base": "https://wiki.qemu.org/ChangeLog/",
    "qemu-desktop": "https://wiki.qemu.org/ChangeLog/",
    "samba": "https://www.samba.org/samba/history/",
    "systemd": "https://github.com/systemd/systemd/releases",
    "thunderbird": "https://www.thunderbird.net/en-US/thunderbird/releases/",
    "virtualbox": "https://www.virtualbox.org/wiki/Changelog",
    "visual-studio-code-bin": "https://code.visualstudio.com/updates",
    "vlc": "https://www.videolan.org/vlc/releases/",
    "vscodium": "https://github.com/VSCodium/vscodium/releases",
    "vscodium-bin": "https://github.com/VSCodium/vscodium/releases",
}

# Flatpak app ID -> Arch-style name resolved against the map above.  IDs are
# matched case-insensitively (real IDs vary in casing, e.g. org.videolan.VLC),
# so keys are normalized to lowercase at build time.
_FLATPAK_ALIASES_RAW = {
    "org.blender.Blender": "blender",
    "org.chromium.Chromium": "chromium",
    "org.gimp.GIMP": "gimp",
    "org.inkscape.Inkscape": "inkscape",
    "org.mozilla.firefox": "firefox",
    "org.mozilla.Thunderbird": "thunderbird",
    "org.videolan.VLC": "vlc",
}

# Expose read-only views so callers cannot mutate the shipped maps.
CHANGELOG_MAP = MappingProxyType(_CHANGELOG_MAP)
FLATPAK_ALIASES = MappingProxyType(
    {key.lower(): value for key, value in _FLATPAK_ALIASES_RAW.items()})


def get_changelog_url(name, source=""):
    """Return the release-notes URL for a package, or None.

    ``name`` is matched case-insensitively against the Arch map first.  If the
    name looks like a Flatpak app ID (reverse DNS, e.g.
    ``org.mozilla.firefox``) it is resolved through the alias table.  npm
    packages have no canonical changelog and simply fall through to None.
    Unknown packages return None and callers show no notes link.  Never raises.

    ``source`` is accepted for forward compatibility; it does not change the
    lookup result because Arch, AUR and Flatpak names cannot collide.
    """
    key = (name or "").strip().lower()
    url = CHANGELOG_MAP.get(key)
    if url:
        return url
    resolved = FLATPAK_ALIASES.get(key)
    if resolved:
        return CHANGELOG_MAP.get(resolved.lower())
    return None