# NeoArch

Modern Package Manager for Arch Linux

[![Website](https://img.shields.io/badge/Website-neoarch.dpdns.org-00BFAE?style=for-the-badge&logo=netlify&logoColor=white)](https://neoarch.dpdns.org/)
[![Version](https://img.shields.io/github/v/release/Sanjaya-Danushka/Neoarch?style=for-the-badge&color=00BFAE&label=Version)](https://github.com/Sanjaya-Danushka/Neoarch/releases)
[![License](https://img.shields.io/github/license/Sanjaya-Danushka/Neoarch?style=for-the-badge&color=00BFAE)](LICENSE)
[![Issues](https://img.shields.io/github/issues/Sanjaya-Danushka/Neoarch?style=for-the-badge&color=00BFAE)](https://github.com/Sanjaya-Danushka/Neoarch/issues)

[Features](#features) • [Screenshots](#screenshots) • [Installation](#installation) • [Usage](#usage) • [Command-Line](#command-line-usage) • [Contributing](#contributing) • [License](#license)

<img width="1295" height="860" alt="NeoArch main window" src="https://github.com/user-attachments/assets/a4e13e1b-8626-401d-b600-60e758a9623d" />

NeoArch combines pacman, AUR, Flatpak, and npm in one desktop app — with a fully scriptable CLI (`neo`) for the terminal. Install packages from anywhere, keep your system clean, and automate everything with JSON output.

---

## Features

### Multi-source package management

Unify pacman, AUR, Flatpak, and npm under one interface. Search, install, update, and remove packages from any source — with live AUR search and one-click local package install (`.pkg.tar.zst`, `.pacman`, `.AppImage`, `.flatpakref`).

### System hygiene

Keep your system clean: one-click orphaned package removal (`pacman -Qtdq`), manage leftover `.pacnew`/`.pacsave` files (view diff, accept, or delete), BleachBit and pacman cache cleaning, and the latest Arch Linux news via a built-in RSS reader with offline caching.

### Safety net

- **Timeshift snapshots** — snapshot before risky updates; restore if anything goes wrong. Automatic cleanup of old snapshots.
- **Btrfs system backups** — full backups (package list + config export) with snapshot support and auto-prune (keeps last 5).
- **PKGBUILD scanner** — statically reviews a PKGBUILD and its `.install` scriptlets for risky post-install tools, privilege elevation, dynamic shell construction, local binary sources, obfuscated names, and Unicode homograph spoofing. Exits with code 2 on critical findings, so it is safe to gate scripts on.

### GUI workspace

- **Docker manager** — pull, run, list, stop, and clean containers with port mappings, volumes, environment variables, GPU passthrough, and restart policies.
- **Git manager** — clone, build, update, and clean Git projects. Auto-detects build methods: Cargo, Autotools, Makefile, and custom commands.
- **Bundle system** — create portable package bundles for deployment. Export, import, install, and share bundles locally or as community bundles.
- **Plugin system** — 50+ built-in plugins with an extensible Python hook system (`on_startup`, `on_tick`, `on_view_changed`), plus a community plugin store.

### Cloud and credentials

- **Cloud sync** — sign in with Supabase via OAuth to sync bundle favorites across devices. Session tokens are cached for seamless re-authentication.
- **Credential caching** — secure session-based sudo credential caching with auto-cleaning on exit, and a GUI password dialog with `SUDO_ASKPASS` support.

### Scheduled updates

Set-and-forget auto-updates with configurable intervals (1–30 days), auto-refresh, and optional snapshot-before-update.

### Ignore updates

Mark specific packages to ignore during updates. Persisted to `~/.config/neoarch/ignored_updates.json` — survives reboots and updates.

### Command-line interface

A scriptable terminal frontend that runs headless (no GUI required). `neo` is the friendly shorthand; `neoarch-cli` is the identical full name. Every command supports `--json` output for automation, and search results are indexed so you can act on them by number:

```bash
neo search browserpass                # search pacman + AUR (indexed list)
neo install 3                         # install result #3 from your last search
neo install yay                       # install from any source (auto AUR fallback)
neo install https://host/pkg.pkg.tar.zst   # install a package archive from URL
neo upgrade                           # full system upgrade
neo updates                           # list available updates
neo update pkg                        # update specific packages
neo remove pkg                        # remove packages
neo list                              # list installed packages
neo doctor                            # system health check
neo news                              # latest Arch Linux news
neo scan ./PKGBUILD                   # security scan (risky tools, elevation, homographs)
neo down firefox -l                   # list cached versions
neo down firefox -p                   # downgrade + pin to IgnorePkg
neo hold list                         # show IgnorePkg / HoldPkg
neo hold linux                        # hold a package
neo hold reason firefox explicit      # set install reason
neo keys list                         # trusted pacman keys
neo keys init                         # official Arch keyrings
neo reboot --check --json             # is a reboot recommended?
neo backup                            # create a backup (defaults to create)
neo clean orphans                     # remove orphaned packages
neo clean cache --keep 2              # paccache retention
neo clean corrupt                     # find corrupted cache archives
neo clean flatpak                     # remove unused Flatpak runtimes
neo clean merge /etc/x.pacnew --accept  # three-way .pacnew merge
neo parallel                          # show ParallelDownloads
neo parallel 10                       # set it in /etc/pacman.conf (root)
neo schedule                          # weekly update schedule
neo schedule set --days 1,3,5 --time 05:30 --enable
neo recommend -n 5                    # curated package recommendations
neo appimage list                     # managed AppImages
neo appimage add-repo Obsidian obsidianmd/obsidian-releases
neo appimage check --json             # check for AppImage updates
neo build yay --check                 # AUR build (chroot/check/commit)
neo news --mark-read                  # read news + mark as read
```

Before executing, `neo install` resolves where each package comes from and asks for confirmation, so you always see the source (`[extra]`, `[aur]`, `[flatpak]`) first.

- **Search results** show a source badge and an index — number `1`..`10`; `neo install <number>` installs that exact result. Indexes only apply to the most recent search (and an invalid/out-of-date number is rejected with a hint).
- **`--json`** switches any listing command to machine-readable output.
- The longer `neoarch-cli` spellings (`neoarch-cli list-updates`, `neoarch-cli purify cache`, `neoarch-cli aur-build ...`) still work; `neo` is an alias layer on top.

#### AppImage store

The `appimage` subcommands manage a NeoArch-owned store at `~/.local/share/neoarch/appimages`: `add` (local file), `add-url` (static URL), and `add-repo` (GitHub/GitLab/Codeberg/Forgejo latest release). Each AppImage gets a desktop entry + icon and is tracked for updates via `check`/`update`.

## Screenshots

<img width="1211" height="811" alt="Search and Discover Packages" src="https://github.com/user-attachments/assets/7d63dca2-15cc-406a-bd0a-a5b60ad9d652" />
*Search and Discover Packages*

<img width="1203" height="812" alt="Installed Packages View" src="https://github.com/user-attachments/assets/d4bbb403-7a8a-4693-86e7-38e810c94b05" />
*Installed Packages View*

## Installation

Two AUR packages are published — `neoarch` is the stable release, `neoarch-git` tracks the latest development build:

```bash
yay -S neoarch        # stable    (or paru -S neoarch)
yay -S neoarch-git    # latest dev build
```

Installing `neoarch-git` also puts both `neo` and `neoarch-cli` on your PATH.

### Prerequisites

- **OS:** Arch Linux (or Arch-based distro)
- **Python:** 3.8+
- **PyQt6**
- **Administrative privileges** (sudo) for package operations

### Install dependencies

#### Option A — Arch packages (recommended)

```bash
sudo pacman -S --needed python python-pyqt6 python-requests qt6-svg git flatpak nodejs npm
```

#### Option B — Python virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_pyqt.txt
```

> **Note:** On Arch, using system `pip` often triggers the "externally-managed-environment" error. Prefer Option A (pacman) or use a virtual environment (Option B). You can also use `pipx` (`sudo pacman -S python-pipx`), which manages a dedicated venv for each app.

### Run NeoArch

```bash
python Neoarch.py
```

Or make it executable:

```bash
chmod +x Neoarch.py && ./Neoarch.py
```

## Usage

| Action | Description |
| ------ | ----------- |
| Discover Packages | Search and browse available packages from pacman, AUR, Flatpak, and npm |
| Install Packages | Select and install packages with a single click |
| Manage Updates | View and install available system updates across all sources |
| Plugins | Enable, disable, and create Python hook plugins; browse community plugins |
| Bundles | Create, export, import, and install package bundles |
| Docker | Pull, run, stop, and clean Docker containers with port mappings and volumes |
| Git | Clone, build, update, and clean Git projects with auto-detected build methods |
| Snapshots | Create and restore Timeshift snapshots before risky operations |
| System Backup | Create/restore system backups with Btrfs snapshot support |
| Hygiene | Remove orphaned packages, manage `.pacnew` files, read Arch news |
| Local Files | Install `.pkg.tar.zst`, `.pacman`, `.AppImage`, `.flatpakref` files directly |
| Cloud Sync | Sign in with Supabase to sync favorites across devices |
| CLI | Scriptable `neo` with `--json` output for search/install/backup/etc. |

## Command-line usage

Everything above the GUI is available in the terminal. Use `neo -h` (or `neo <command> -h`) for the full list, and `--json` anywhere a listing is printed to get structured output for scripts.

```bash
neo search cmatrix
#  [1] cmatrix         [pacman]  A curses-based scrolling 'Matrix'-like screen
#  [2] libcmatrix      [pacman]  Matrix client library written in GObject
#  [3] cmatrix-git     [aur]     A curses-based scrolling 'Matrix'-like screen
#  Tip: neo install <number> installs that result

neo install 3   # → selected [3] cmatrix-git  [aur]  → confirm → installs
```

Output adapts to your terminal: wide screens get an aligned table, smaller terminals get a compact numbered list, and colors are used when supported (`NO_COLOR=1` disables them). When piping, a plain single-line format is used automatically.

## Development

```bash
git clone https://github.com/Sanjaya-Danushka/Neoarch.git
cd Neoarch
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_pyqt.txt
python Neoarch.py
```

Run the test suite:

```bash
python -m pytest tests/ -q
```

## Contributing

We welcome contributions! Please follow our guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Standards

- **Security First** — All code must undergo security review
- **Code Quality** — Follow PEP 8, add tests, maintain clean readable code
- **User Experience** — Prioritize intuitive UI/UX and responsive performance
- **Documentation** — All features must be properly documented

## Security

If you discover any security vulnerabilities, report them immediately to <dsanjaya712@gmail.com>.

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

Built by [Sanjaya Danushka](https://github.com/Sanjaya-Danushka)

[Website](https://neoarch.dpdns.org/) • [Issues](https://github.com/Sanjaya-Danushka/Neoarch/issues) • [Discussions](https://github.com/Sanjaya-Danushka/Neoarch/discussions) • [Releases](https://github.com/Sanjaya-Danushka/Neoarch/releases)

[![Buy me a coffee](https://img.buymeacoffee.com/button-api/?text=Buy+me+a+coffee&emoji=&slug=sanjayadanushka&button_colour=FF5F5F&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00)](https://www.buymeacoffee.com/sanjayadanushka)