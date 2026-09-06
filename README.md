<div align="center">

# NeoArch

<sub>Modern package manager for Arch Linux — pacman · AUR · Flatpak · npm</sub>

<br/>

[![AUR](https://img.shields.io/badge/AUR-neoarch--git-00BFAE?style=flat-square&labelColor=161B22&logo=archlinux&logoColor=white)](https://aur.archlinux.org/packages/neoarch-git)
[![Version](https://img.shields.io/github/v/release/Sanjaya-Danushka/Neoarch?style=flat-square&label=Version&color=00BFAE&labelColor=161B22)](https://github.com/Sanjaya-Danushka/Neoarch/releases)
[![Stars](https://img.shields.io/github/stars/Sanjaya-Danushka/Neoarch?style=flat-square&label=Stars&color=00BFAE&labelColor=161B22)](https://github.com/Sanjaya-Danushka/Neoarch/stargazers)
[![Last commit](https://img.shields.io/github/last-commit/Sanjaya-Danushka/Neoarch?style=flat-square&label=Last%20commit&color=00BFAE&labelColor=161B22)](https://github.com/Sanjaya-Danushka/Neoarch/commits/dev)
[![License](https://img.shields.io/github/license/Sanjaya-Danushka/Neoarch?style=flat-square&label=License&color=00BFAE&labelColor=161B22)](LICENSE)

</div>

<img src="https://github.com/user-attachments/assets/a4e13e1b-8626-401d-b600-60e758a9623d" alt="NeoArch banner" width="100%" style="border-radius:12px;border:1px solid #30363d"/>

> **One app for everything you install.** Search, install, update, and clean across **pacman, AUR (live search), Flatpak, and npm** — from a native PyQt6 desktop app or a headless `neo` CLI with `--json` automation.

---

<sup>Jump to: <kbd>App features</kbd> · <kbd>CLI reference</kbd> · [<kbd>Install</kbd>](#install) · [<kbd>Support</kbd>](#support) · [<kbd>License</kbd>](#license)</sup>

<details open>
<summary><b>App — GUI &amp; features</b> <i>(click to view)</i></summary>

### Discover and manage everything

- **Unified search** — browse pacman, AUR (live RPC search), Flatpak, and npm in one list, with filters per source.
- **One-click actions** — install, remove, hold, downgrade, mark-as-dependency, view package details, and manage `IgnorePkg`/`HoldPkg` — all from a single screen.
- **Update center** — see updates from every source with snapshot-before-update and ignition for staged updates.
- **Local files** — install `.pkg.tar.zst`, `.pacman`, `.AppImage`, and `.flatpakref` by drag-and-drop with automatic type detection.

### Safety and maintenance

- **Snapshots** — Timeshift integration (list, create, restore, prune) before risky operations.
- **System backups** — Btrfs-aware backups (package list + config export) with auto-prune keeping the last 5.
- **Hygiene tools** — orphan removal, `.pacnew`/`.pacsave` diffs and merging, cache + BleachBit cleaning, and Arch news with offline caching.
- **PKGBUILD scanner** — static analysis mode flags risky post-install tools, elevation, dynamic shell, local binaries, and Unicode homograph spoofing.

### Workspace &amp; cloud

- **Docker manager** — pull, run, stop, clean containers; port mappings, volumes, env, GPU passthrough, restart policies.
- **Git manager** — clone, build, update, clean; auto-detects Cargo, Autotools, Makefile, and custom builds.
- **Bundles** — portable package bundles; export, import, install, share locally or as community bundles.
- **Plugin system** — 50+ built-in plugins with Python lifecycle hooks (`on_startup`, `on_tick`, `on_view_changed`) and a community store.
- **Cloud sync** — Supabase OAuth sign-in; favorites and bundles sync across devices with exp-aware token caching.

### Screenshots

<img width="45%" align="top" src="https://github.com/user-attachments/assets/7d63dca2-15cc-406a-bd0a-a5b60ad9d652" alt="Search and Discover Packages" style="border-radius:12px;border:1px solid #30363d"/> <img width="45%" align="top" src="https://github.com/user-attachments/assets/d4bbb403-7a8a-4693-86e7-38e810c94b05" alt="Installed Packages View" style="border-radius:12px;border:1px solid #30363d"/>

### Under the hood

Python 3.8+ · PyQt6 (Signals &amp; Slots, QThread workers) · subprocess-bounded `pacman` calls · AUR RPC live search (rate-limited) · Flatpak user remotes · npm globals · Supabase Auth with cached session tokens · `SUDO_ASKPASS`/pexpect credential caching · config at `~/.config/neoarch` · ignored updates at `~/.config/neoarch/ignored_updates.json`.

</details>

<details>
<summary><b>CLI — full command reference</b> <i>(click to view)</i></summary>

`neo` is the shorthand for `neoarch-cli`; both are identical. Every command accepts `--json`, `-y/--yes`, and `--no-confirm`.

**Search &amp; install**

```bash
neo search cmatrix                    # indexed results + source badges
neo search code --aur -l 5            # AUR only, 5 results
neo install 3                         # install result #3 from last search
neo install yay                       # auto-fallback repo → AUR
neo install --flatpak spotify         # force a Flatpak
neo install --aur yay-bin             # force AUR
neo install https://host/app.pkg.tar.zst   # install from URL
neo install-url https://host/app.pkg.tar.zst
neo remove firefox -c                 # remove + cascade unneeded deps
neo down firefox -l                   # list cached versions
neo down firefox -p                   # downgrade + pin to IgnorePkg
neo build yay --check --install       # AUR build (chroot/check/commit)
```

**Updates &amp; upgrades**

```bash
neo upgrade                           # full system upgrade
neo upgrade --aur                     # AUR packages only
neo upgrade --flatpak / --npm         # that source only
neo updates                           # list available updates (alias: list-updates)
neo updates --flatpak                 # include Flatpak updates
neo update firefox                    # update specific packages
neo list -e                           # explicitly installed packages
neo list -m                           # foreign (AUR) packages
```

**Marks, ignores &amp; keys**

```bash
neo hold list                         # show IgnorePkg / HoldPkg
neo hold linux                        # hold (alias: neo marks hold)
neo hold reason firefox explicit      # set install reason
neo hold unhold linux
neo ignore -a linux-lts               # add to ignore list
neo ignore -l                         # list ignored packages
neo keys list                         # trusted pacman keys
neo keys init                         # initialize keyring
neo keys populate                     # official Arch keyrings
neo keys refresh                      # refresh from keyserver
neo keys sign <KEYID>                 # locally sign a key
```

**Hygiene &amp; safety**

```bash
neo clean orphans                     # remove orphaned packages
neo clean cache --keep 2              # trim package cache (paccache)
neo clean corrupt                     # find corrupted archives
neo clean flatpak                     # remove unused Flatpak runtimes
neo clean merge /etc/x.pacnew --accept   # three-way .pacnew merge
neo backup                            # create a backup (default)
neo backup -l                         # list backups
neo backup -r /path/to/backup         # restore from a backup
neo doctor                            # system health check
neo scan ./PKGBUILD                   # static security scan
```

**System &amp; automation**

```bash
neo reboot --check --json             # is a reboot recommended?
neo parallel                          # show ParallelDownloads
neo parallel 10                       # set it (root)
neo schedule                          # show weekly schedule (default)
neo schedule set --days 1,3,5 --time 05:30 --enable
neo recommend -n 5                    # curated recommendations
neo recommend -n 10 --installed       # include installed
neo news -l 5                         # latest Arch news
neo news --mark-read                  # read + mark as read
neo appimage list                     # managed AppImages
neo appimage add ./Some.AppImage      # add a local file
neo appimage add-repo Code ossia/score
neo appimage check --json             # check for updates
neo appimage update                   # update all managed apps
neo config get theme                  # read a config key
neo config set theme dark             # write a config key
```

Worked example — search, then install by number:

```console
$ neo search cmatrix
 [1] cmatrix         [pacman]  A curses-based scrolling 'Matrix'-like screen
 [2] libcmatrix      [pacman]  Matrix client library written in GObject
 [3] cmatrix-git     [aur]     A curses-based scrolling 'Matrix'-like screen
 Tip: neo install <number> installs that result

$ neo install 3
[neoarch] selected [3] cmatrix-git  [aur]
  → cmatrix-git  [aur]
Install cmatrix-git? [y/N]
```

Output adapts to terminal width (tables on wide, compact lists on small), and colors turn off with `NO_COLOR=1`.

</details>

---

## Install

**Requirements:** Arch Linux · Python 3.8+ · PyQt6 · sudo.

```bash
sudo pacman -S --needed python python-pyqt6 python-requests qt6-svg git flatpak nodejs npm
python Neoarch.py
```

AUR packages — `neoarch` is the stable release, `neoarch-git` tracks latest dev (adds `neo`/`neoarch-cli` to PATH):

```bash
yay -S neoarch        # or paru -S neoarch
yay -S neoarch-git    # latest development build
```

Virtual environment: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements_pyqt.txt`.
On Arch, system `pip` usually triggers "externally-managed-environment" — prefer pacman, a venv, or `pipx`.

---

<div align="center">

<a name="support"></a>

<sub>Something missing or broken? [Open an issue](https://github.com/Sanjaya-Danushka/Neoarch/issues) — or [pull request](https://github.com/Sanjaya-Danushka/Neoarch/pulls) it.</sub>

<br/>

[![Buy me a coffee](https://img.buymeacoffee.com/button-api/?text=Buy+me+a+coffee&emoji=&slug=sanjayadanushka&button_colour=FF5F5F&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00)](https://www.buymeacoffee.com/sanjayadanushka)

<br/>

<a name="license"></a>

<sub>MIT License · [Project](https://github.com/Sanjaya-Danushka/Neoarch) · [Website](https://neoarch.dpdns.org/) · Built by [Sanjaya Danushka](https://github.com/Sanjaya-Danushka)</sub>

</div>