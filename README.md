<div align="center">

# NeoArch

### The package manager Arch deserves.

**pacman, AUR, Flatpak, and npm — one app. With a CLI that does everything.**

<br />

<img src="https://github.com/user-attachments/assets/a4e13e1b-8626-401d-b600-60e758a9623d" alt="NeoArch" width="95%" />

<br />

[![Version](https://img.shields.io/github/v/release/Sanjaya-Danushka/Neoarch?style=flat-square&label=Version&color=00BFAE)](https://github.com/Sanjaya-Danushka/Neoarch/releases)
[![Stargazers](https://img.shields.io/github/stars/Sanjaya-Danushka/Neoarch?style=flat-square&label=Stars&color=00BFAE)](https://github.com/Sanjaya-Danushka/Neoarch/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/Sanjaya-Danushka/Neoarch?style=flat-square&label=Last%20commit&color=00BFAE)](https://github.com/Sanjaya-Danushka/Neoarch/commits/dev)
[![License](https://img.shields.io/github/license/Sanjaya-Danushka/Neoarch?style=flat-square&label=License&color=00BFAE)](LICENSE)
[![Website](https://img.shields.io/badge/Website-neoarch.dpdns.org-00BFAE?style=flat-square&logo=netlify&logoColor=white)](https://neoarch.dpdns.org/)

<br />

**Install** · **Discover** · **Update everything** · **Stay clean**

</div>

---

NeoArch removes the juggling act. Stop switching between `pacman`, an AUR helper, Flatpak, and a dozen maintenance scripts — search, install, update, and clean across **all four sources** from one native PyQt6 app, or from the terminal with `neo`.

## Features

- **Multi-source** — unified search, install, and updates for pacman, AUR (live search), Flatpak, and npm.
- **Safety net** — Timeshift snapshots before risky updates, Btrfs system backups, and a static PKGBUILD scanner that flags dangerous scriptlets without executing them.
- **System hygiene** — one-click orphan removal, `.pacnew`/`.pacsave` handling, cache + BleachBit cleaning, and the latest Arch news.
- **Workspace** — Docker and Git managers, portable package bundles, 50+ built-in plugins with Python hooks, and a community plugin store.
- **Cloud sync** — sign in with Supabase via OAuth; favorites and bundles follow you across devices.
- **Scheduled updates** — set-and-forget intervals (1–30 days), with optional snapshot-before-update.
- **CLI everywhere** — the headless `neo` command mirrors the app, with `--json` output for scripts.

## Command line

```bash
neo search cmatrix          # indexed results with source badges
neo install 3               # install result #3 from your last search
neo install yay             # auto-detects AUR
neo upgrade                 # full system upgrade
neo updates --json          # machine-readable update list
neo doctor                  # system health check
neo down firefox -p         # downgrade + pin to IgnorePkg
neo hold linux              # hold a package
neo clean orphans           # remove orphans
neo backup                  # Btrfs system backup
neo scan ./PKGBUILD         # security scan
neo schedule set --days 1,3,5 --time 05:30 --enable
```

```
$ neo install 3
[neoarch] selected [3] cmatrix-git  [aur]
  → cmatrix-git  [aur]
Install cmatrix-git? [y/N]
```

`neo` is the shorthand for `neoarch-cli`. Install-candidate sources are shown and confirmed before anything runs, so you always know where a package comes from.

## Install

```bash
yay -S neoarch        # stable          (or paru -S neoarch)
yay -S neoarch-git    # latest dev build — adds `neo` to PATH
```

**Requirements:** Arch Linux · Python 3.8+ · PyQt6 · sudo. Manual setup:

```bash
sudo pacman -S --needed python python-pyqt6 python-requests qt6-svg git flatpak nodejs npm
python Neoarch.py
```

Prefer a virtual environment? `python -m venv .venv && source .venv/bin/activate && pip install -r requirements_pyqt.txt`. (System `pip` on Arch often triggers "externally-managed-environment" — use pacman, a venv, or `pipx`.)

---

<div align="center">

**Report a bug** · **Request a feature** · **Star the repo** — every contribution counts.

[Issues](https://github.com/Sanjaya-Danushka/Neoarch/issues) · [Releases](https://github.com/Sanjaya-Danushka/Neoarch/releases) · [Website](https://neoarch.dpdns.org/)

<br />

[![Buy me a coffee](https://img.buymeacoffee.com/button-api/?text=Buy+me+a+coffee&emoji=&slug=sanjayadanushka&button_colour=FF5F5F&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00)](https://www.buymeacoffee.com/sanjayadanushka)

</div>