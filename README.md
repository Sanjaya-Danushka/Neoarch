<div align="center">

# NeoArch

<sub>Modern package manager for Arch Linux — pacman · AUR · Flatpak · npm</sub>

<br/>

[![AUR](https://img.shields.io/badge/AUR-neoarch--git-00BFAE?style=flat-square&labelColor=161B22&logo=archlinux&logoColor=white)](https://aur.archlinux.org/packages/neoarch-git)
[![Version](https://img.shields.io/github/v/release/Sanjaya-Danushka/Neoarch?style=flat-square&label=Version&color=00BFAE&labelColor=161B22)](https://github.com/Sanjaya-Danushka/Neoarch/releases)
[![Stars](https://img.shields.io/github/stars/Sanjaya-Danushka/Neoarch?style=flat-square&label=Stars&color=00BFAE&labelColor=161B22)](https://github.com/Sanjaya-Danushka/Neoarch/stargazers)
[![Last commit](https://img.shields.io/github/last-commit/Sanjaya-Danushka/Neoarch?style=flat-square&label=Last%20commit&color=00BFAE&labelColor=161B22)](https://github.com/Sanjaya-Danushka/Neoarch/commits/dev)
[![License](https://img.shields.io/github/license/Sanjaya-Danushka/Neoarch?style=flat-square&label=License&color=00BFAE&labelColor=161B22)](LICENSE)

<br/>

<img src="https://github.com/user-attachments/assets/a4e13e1b-8626-401d-b600-60e758a9623d" alt="NeoArch" width="95%" style="border-radius:12px;border:1px solid #30363d;box-shadow:0 8px 24px rgba(0,0,0,.4)"/>

<br/>

**Search** · **Install** · **Update everything** · **Stay clean**

<br/>

[Website](https://neoarch.dpdns.org/) · [Issues](https://github.com/Sanjaya-Danushka/Neoarch/issues) · [Releases](https://github.com/Sanjaya-Danushka/Neoarch/releases)

</div>

---

NeoArch unifies **pacman, AUR, Flatpak, and npm** in one native PyQt6 app — and the headless **`neo`** CLI mirrors every GUI feature. Indexed search, source badges, confirm-before-install, snapshots, backups, and `--json` automation built in.

## Features

- **Multi-source** — unified search, install, and updates for pacman, AUR (live search), Flatpak, and npm.
- **Safety net** — Timeshift snapshots before risky updates, Btrfs system backups, and a static PKGBUILD security scanner.
- **System hygiene** — orphan removal, `.pacnew`/`.pacsave` management, cache + BleachBit cleaning, Arch news.
- **Workspace** — Docker manager, Git manager, portable bundles, 50+ plugins with Python lifecycle hooks.
- **Cloud sync** — Supabase OAuth sign-in; favorites and bundles follow you across devices.
- **Scheduled updates** — auto-update intervals (1–30 days) with optional snapshot-before-update.
- **Credential caching** — secure session-based sudo caching with pexpect askpass; auto-cleaned on exit.

## Command line

`neo` is the shorthand for `neoarch-cli`; both are identical. Every command accepts `--json`, `-y/--yes`, and `--no-confirm`.

**Search & install**

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

**Updates & upgrades**

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

**Marks, ignores & keys**

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

**Hygiene & safety**

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

**System & automation**

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

Worked example — search, then install by number, with the source confirmed before anything runs:

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

Terminal output adapts to width — aligned tables on wide screens, compact numbered lists on small ones — and colors are used when supported (set `NO_COLOR=1` to disable). AppImage files are stored at `~/.local/share/neoarch/appimages` with desktop entries, and tracked for updates.

## Install

```bash
yay -S neoarch        # stable          (or paru -S neoarch)
yay -S neoarch-git    # latest dev build — adds `neo` to PATH
```

**Requirements:** Arch Linux · Python 3.8+ · PyQt6 · sudo.

```bash
sudo pacman -S --needed python python-pyqt6 python-requests qt6-svg git flatpak nodejs npm
python Neoarch.py
```

Virtual environment: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements_pyqt.txt`.
(Arch's system `pip` triggers "externally-managed-environment" — prefer pacman, a venv, or `pipx`.)

---

<div align="center">

Found a bug or want a feature — [open an issue](https://github.com/Sanjaya-Danushka/Neoarch/issues). Pull requests welcome — fork, branch, submit.

<br/>

[![Buy me a coffee](https://img.buymeacoffee.com/button-api/?text=Buy+me+a+coffee&emoji=&slug=sanjayadanushka&button_colour=FF5F5F&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00)](https://www.buymeacoffee.com/sanjayadanushka)

<br/>

<sub>MIT License · Built by [Sanjaya Danushka](https://github.com/Sanjaya-Danushka)</sub>

</div>