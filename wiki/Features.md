# Features

A complete overview of NeoArch — version 3.3.0 ("Lynx" Edition). One app for
everything you install: search, install, update, and clean across **pacman,
AUR, Flatpak, and npm**, from a native PyQt6 desktop GUI or a headless
`neo` CLI with `--json` automation.

> **📖 Read before use** — the [Wiki Home](Home.md) covers every feature with
> screenshots and tutorials. Start there before your first install.

---

## Table of contents

1. [Overview](#overview)
2. [Package sources](#package-sources)
3. [Home / Discover dashboard](#home--discover-dashboard)
4. [Installed packages page](#installed-packages-page)
5. [Updates center](#updates-center)
6. [Package actions & details](#package-actions--details)
7. [PKGBUILD security scanner](#pkgbuild-security-scanner)
8. [System snapshots & backups](#system-snapshots--backups)
9. [Maintenance & hygiene tools](#maintenance--hygiene-tools)
10. [Sources & plugins](#sources--plugins)
11. [Bundles](#bundles)
12. [AppImage manager](#appimage-manager)
13. [Git repositories manager](#git-repositories-manager)
14. [Docker container manager](#docker-container-manager)
15. [Arch news](#arch-news)
16. [Cloud sync & accounts](#cloud-sync--accounts)
17. [Authentication & privileges](#authentication--privileges)
18. [Settings panels](#settings-panels)
19. [Themes, window & appearance](#themes-window--appearance)
20. [Internationalization](#internationalization)
21. [Notifications](#notifications)
22. [Network & proxy](#network--proxy)
23. [CLI reference](#cli-reference)
24. [Scheduled updates & automation](#scheduled-updates--automation)
25. [Under the hood](#under-the-hood)
26. [What's new / release notes](#whats-new--release-notes)

---

## Overview

NeoArch is a modern package-manager frontend for Arch Linux that unifies
multiple package ecosystems into a single native desktop application and a
scriptable CLI. It lets you:

- **Search, install, remove, hold, downgrade, and update** packages from
  pacman, the AUR (live RPC search), Flatpak, and npm globals from one screen.
- **Keep the system clean and healthy** with orphan removal, `.pacnew` diffs
  and merging, cache + BleachBit cleaning, corruption scans, and Arch news
  with offline caching.
- **Protect the system before risky operations** with snapshots (Timeshift or
  Snapper/BTRFS) and automatic snapshot-before-update.
- **Scan PKGBUILDs for dangerous code** before installing anything from the
  AUR (rules ported from ArchCanary).
- **Manage the wider desktop**: Docker containers, Git-based projects,
  AppImages, plus a 500+ item plugin/extension store.
- **Sync favourites and bundles across devices** via Supabase OAuth (Clerk
  portal), with expiry-aware token caching.
- **Run everything headless** via the `neo` CLI with `--json` automation.

## Package sources

- **pacman** — official Arch Linux repositories (core, extra, multilib).
- **AUR** — Arch User Repository, live RPC search (rate-limited).
- **Flatpak** — user Flatpak remotes (Flathub, automatic user-remote setup).
- **npm** — global npm packages.
- **Local files** — install by drag-and-drop with automatic type detection:
  `.pkg.tar.zst`, `.pacman`, `.AppImage`, `.flatpakref`.
- **URL archives** — install a package archive (`.pkg.tar.*` / `.pacman`)
  directly from an HTTP(S) URL with source validation.

## Home / Discover dashboard

- **Unified search** across pacman / AUR / Flatpak / npm in one results list,
  with per-source filters.
- **Live source cards** with a health ring, storage and stats footers, and
  iOS-style quick actions.
- **Streaming results** as you type (debounced live search) with a loading
  indicator and a no-results / "did you mean" suggestion fallback.
- Sortable, filterable results ("hide installed", sort options, source
  badges).
- Live selection counter and per-selection toolbar actions.
- Header quick actions in a transparent-black pill: Refresh, Security
  Settings, Arch News, quick search, and a live network signal indicator.
- Grid and list/table view modes.

## Installed packages page

- List all installed packages with an installed-date column, a per-package
  update flag, search filtering, and an uninstall menu.
- Filters such as "installed, has update" and an "Updates Installed" column.
- During a running install/update the page reuses the last loaded list or
  shows "Waiting for the update to finish" and refreshes automatically.

## Updates center

- See updates from every source (pacman, AUR, Flatpak, npm, firmware) merged
  into one list.
- **Snapshot-before-update** with "ignition" for staged updates.
- **Update Review dialog** — updates previewed before they run with
  per-package details.
- **Partial-update warnings** — selecting part of the available Arch updates
  triggers an explicit warning to prevent silent partial upgrades that can
  break dependencies.
- Update Selected / Update All actions, per-package update, ignore individual
  updates (persisted to `~/.config/neoarch/ignored_updates.json`).
- Per-package AUR updates, not only a bulk refresh.

## Package actions & details

From a single screen:

- Install · Remove / Uninstall (with cascade of unneeded deps) · Hold /
  Unhold · Downgrade (choose cached version, optionally pin to IgnorePkg).
- Mark-as-dependency / set install reason (explicit vs dependency).
- Manage IgnorePkg / HoldPkg.
- View full package details — source, ID, install reason, size, required-by
  (reverse dependencies), description, update status.
- Launch installed applications · check for updates on a package.
- Open package pages / AUR pages in the browser.
- AUR actions — View PKGBUILD, View Changes (commit history), Download
  snapshot tarball.
- Right-click context menus per source: Launch / Uninstall / Install / View
  in browser / Copy name / Update / Ignore update / View Details.

## PKGBUILD security scanner

Static analysis of PKGBUILD and `.install` files before AUR installs. Flags
dangerous patterns including:

- Risky post-install tools · elevation (sudo/root escalation) · dynamic shell
  (`eval`, `$(...)`, variable command execution) · local binaries.
- Unicode homograph spoofing.
- Byte-level command obfuscation (ANSI-C `$'\x..'` quoting, `printf`-spelled
  commands, variable-split reassembly).
- Tor/SOCKS-proxied fetches · downloads straight into system paths · AUR
  self-propagation references.
- Non-interactive mutating `pacman --noconfirm` calls · duplicate `source=()`
  declarations · unchecked mutable MR/PR diff sources.

AUR packages are fetched and scanned **before** the build starts. Critical
findings block the install until the risk is accepted; warnings require
confirmation; if the AUR is unreachable the install falls back to a legacy
static notice (a soft gate, not a hard dependency). Exposed via
`neo scan <PKGBUILD>` (`--json` supported). Rules ported from the ArchCanary
project (MIT).

## System snapshots & backups

- **Snapshot engine selection**: Timeshift or Snapper (BTRFS).
- List, create, revert, and delete snapshots.
- Automatically taken before risky operations (snapshot-before-update), with
  optional pacman hooks so every update captures a Snapper snapshot.
- **System backups** — Btrfs-aware backups (package list + config export) with
  auto-prune keeping the last 5, restorable from the GUI or CLI.
- Cleanup of stale/orphaned snapshot processes from interrupted sessions at
  startup.

## Maintenance & hygiene tools

- Orphan removal — packages installed as dependencies that nothing needs.
- `.pacnew` / `.pacsave` handling — list, diff, three-way merge, delete,
  accept.
- Package-cache cleaning (paccache trim, keep N versions per package).
- Corrupted-archive detection and removal.
- Unused Flatpak runtime removal.
- BleachBit integration (launchable as a plugin).
- Arch Linux News reader with offline caching and "mark as read".
- Disk usage / package-cache-size visibility.
- System health check (`neo doctor`).

## Sources & plugins

- 500+ built-in plugin entries organized in categories:
  Development (101) · System (57) · Utility (49) · Multimedia (41) ·
  Graphics (40) · Internet (39) · Games (31) · Office (28) · Security (25) ·
  Communication (22) · Customization (19) · Monitor (18) · Backup (17) ·
  Education (14) · GPU (7).
- Cards-only view with a category source panel and install statuses.
- Batch install, hover uninstall, real-time card state.
- Grid and list views with synchronized filters, sort, and toolbar actions.
- Python lifecycle hooks: `on_startup`, `on_tick`, `on_view_changed`.
- Community plugin store and index (`community_plugins/`).
- Plugin submission script (`submit_plugin.py`).
- Plugins like BleachBit and Timeshift are installable/launchable from here.

## Bundles

- Capture any set of packages into a portable bundle (name, source, version)
  — save your setup for life.
- Export / import bundles (local or portable file).
- Install an entire bundle at once.
- Autosave bundles to a configurable file path.
- **Cloud bundles** — sync via Supabase; table layout, share/import code
  cards, sync and restore buttons.
- **Community bundles** — list, import, and share community bundles.
- Add selected packages to a bundle, remove from bundle, clear.

## AppImage manager

- List and manage AppImage applications (store on disk).
- Add an AppImage from a local file, from a URL, or from a GitHub repository
  release (latest release).
- Update checks with version parsing and `--json` output for the CLI.
- Install updates, remove AppImages, register/unregister desktop entries.
- Reconcile store with disk (sync).
- Metadata/icon extraction and desktop-entry generation.

## Git repositories manager

- Clone, build, update, clean Git-based software projects.
- Auto-detects build systems: Cargo, Autotools, Makefile, and custom builds.
- Install the built result, open repos, view build history, per-repo stats,
  remove repositories.
- Advanced run dialog with build preview and proceed/cancel.

## Docker container manager

- Pull and run containers with an advanced run dialog supporting **port
  mappings, volumes, environment variables, GPU passthrough, and restart
  policies**.
- Start, stop, restart, remove containers; remove images, volumes, networks;
  create volumes.
- Container logs, live stats, open an interactive shell into a container.
- Network and volume listings; image cards; after-action synchronization of
  lists.

## Arch news

- In-app reader for the official Arch Linux news feed.
- Offline fallback and cached copy for reading without a connection.
- "Mark as read" and unread counts.

## Cloud sync & accounts

- Supabase OAuth sign-in with login-changed notifications.
- Favourites and bundles sync across devices.
- Expiry-aware token caching (OAuth tokens cached with an expiry).
- Clerk account-settings portal enabled.
- Versioned Supabase schema with SQL migrations.
- Account avatar / menu in the sidebar; nav greeting customized by username.

## Authentication & privileges

- **Unified authentication** — all privileged operations share one themed,
  session-cached password dialog.
- Sudo password cached in the system keyring (0600 fallback file) and wiped
  when the app exits.
- `SUDO_ASKPASS` / pexpect credential caching; the GUI sudo prompt never
  stores the password.
- `pkexec` removed from snapshots/plugins so there is a single predictable
  auth flow.
- Single-flight guard for parallel sudo requests plus a working Cancel button
  (no double prompts or hangs).
- Correct detection of gnome-keyring / supported keyring daemons.
- Refuses to run as root (app exits if euid == 0).

## Settings panels

**General**
- Auto check updates on launch · firmware update checks (fwupd) · npm user
  mode (install globals to `~/.npm-global` without sudo).
- AUR helper selection (Auto / yay / paru / trizen / pikaur) · language
  (culture) selection.
- Bundle autosave toggle + autosave path.
- Diagnostics: "Test AUR API" connectivity check · export/import settings.

**Appearance**
- Themes (Dark default; Lights, Nord, Dracula marked "Coming soon").
- Window frame: glow-border toggle, corner radius.

**Auto Update**
- Enable automatic updates (schedule days/time) · scheduled update checks
  (interval in days/min, re-check while open).
- Create backup before updates · backup method.
- Create/Delete snapshots · Revert to Snapshot · prune; uses Timeshift or
  Snapper per filesystem (BTRFS native snapshots).
- Install/remove pacman update-time hooks.

**Maintenance**
- Remove orphans · purge old cache (keep N versions) · scan for corrupted
  archives · manage `.pacnew` files · show Arch News (with unread count).

**Security**
- Safety overview / status bar (AUR community recipes, partial updates, sudo
  prompt policy).
- Package-source explanations and review toggles.
- PKGBUILD review tools and AUR resource links.

**Notifications**
- Desktop notifications · in-app toasts · sound on events.
- Event toggles: package install/uninstall complete, updates available,
  errors and warnings.
- Rate limiting with per-channel cooldown.

**Logging**
- Log level (DEBUG/INFO/WARNING/ERROR) · log file path · max size · echo to
  terminal.

**Proxy & Network**
- Proxy type (None / HTTP / HTTPS / SOCKS5) with host/port.
- Request timeout · verify SSL certificates.
- `pacman ParallelDownloads` setting (writes `/etc/pacman.conf`, root).

## Themes, window & appearance

- PyQt6 with a token-based dark theme stylesheet by default.
- ThemeManager with `theme_changed` signals.
- Frameless translucent window with edge resizing (all edges/corners, resize
  watchdog for safety), rounded corners, optional glow border.
- Sidebar navigation with icons, tooltips, and an updates-count badge.
- Grid/table view toggles · centered window · header quick actions · custom
  title bar · closing fade · show/hide console output.

## Internationalization

- **Full translation coverage** — every dialog, table header, tooltip, and
  notification.
- **10 complete language catalogs**: Spanish, Sinhala, Hindi, German, French,
  Portuguese, Chinese, Russian, Turkish, Japanese.
- System language auto-detected on first launch; changeable in Settings.
- Rebuilt pipeline — adding a language means dropping in a catalog file.

## Notifications

- Desktop notifications, in-app toast banners, and optional sound.
- Events: new updates, install/uninstall completion, errors/warnings.
- Rate-limited per event type with configurable cooldown.
- Connection-state notifications (restored / lost signal).

## Network & proxy

- Live network latency signal indicator (bars) in the header.
- Retries transient source failures; merges every source into the final
  update list instead of dropping a source that briefly failed.
- AUR RPC live search is rate-limited.
- Configurable proxy (HTTP/HTTPS/SOCKS5), timeouts, SSL verification.

## CLI reference

Global flags accepted everywhere: `--json`, `-y/--yes`, `--no-confirm`.
Output adapts to terminal width (tables vs compact lists) and honors
`NO_COLOR=1`. Shorthand aliases: `updates`, `down`, `hold`, `clean`, `keys`,
`reboot`, `build`. Both `neo` and `neoarch-cli` are installed to `/usr/bin`.

### Search & install

```bash
neo search <query> [--pacman] [--aur] [--flatpak] [-l N]
neo install <names> [--aur] [--flatpak] [--npm]
neo install <number>            # result #N from last search (indexed list)
neo install https://host/app.pkg.tar.zst   # install from URL
neo install-url <url>
neo remove <pkgs> [-c cascade] [-n keep-config]
neo downgrade <pkg> [-l list-only] [-p pin to IgnorePkg] [--version V]
neo build <name> [--chroot] [--check] [--install] [--commit SHA]   # AUR build
```

### Update & upgrade

```bash
neo upgrade [--aur | --flatpak | --npm | --firmware]
neo update <pkgs>               # update specific packages
neo updates  (list-updates) [--aur] [--flatpak] [--firmware]
neo list [-e explicit] [-m foreign/AUR] [--aur] [--flatpak]
```

### Marks, ignores & keys

```bash
neo hold list | <pkg> | unhold | reason <pkg> explicit|deps
neo marks   (list | ignore | unignore | hold | unhold | reason)
neo ignore -a <pkgs> | -r <pkgs> | -l | --show
neo keyring (list | details <key> | init | populate | refresh | receive | sign)
```

### Hygiene & safety

```bash
neo clean orphans | cache [--keep N] | corrupt | flatpak | merge <file> [--accept]
neo purge  (orphans | cache | pacnew)
neo backup [-c create] [-l list] [-r PATH restore]
neo scan <PKGBUILD>             # static security scan (--json)
neo doctor                      # system health check
neo news [-l N] [--mark-read]
```

### System & automation

```bash
neo restart check               # is a reboot recommended? (--check --json)
neo parallel [N]                # show/set ParallelDownloads (1-32)
neo schedule show | set --days 1,3,5 --time 05:30 [--enable|--disable]
neo recommend -n N [--installed]
neo config get|set|reset <key> [value]
neo appimage list|sync|add <file>|add-url <name> <url>|add-repo <name> OWNER/REPO [--host]|remove <id>|check [id]|update [id]
version --version
```

### Worked example

```console
$ neo search cmatrix
 [1] cmatrix    [pacman]  A curses-based scrolling 'Matrix'-like screen
 [2] libcmatrix [pacman]  Matrix client library written in GObject
 [3] cmatrix-git [aur]    A curses-based scrolling 'Matrix'-like screen
 Tip: neo install <number> installs that result

$ neo install 3
```

## Scheduled updates & automation

- Weekly update schedule configurable via the GUI (Settings → Auto Update) or
  CLI (`neo schedule set --days … --time … --enable`).
- systemd service + timer packaging (`neoarch-update.service`,
  `neoarch-update.timer`) for scheduled background updates.
- Deep-clean shell script (`scripts/deep_clean.sh`), Arch dependency
  installer, and desktop-entry installer scripts.
- Update-time pacman hooks for Snapper snapshots.

## Under the hood

- **GUI**: PyQt6, frameless window, signals & slots, QThread workers.
- **Backend**: subprocess-bounded `pacman` calls; AUR RPC live search
  (rate-limited); Flatpak user remotes; npm globals.
- **Auth**: Supabase Auth with cached session tokens; `SUDO_ASKPASS`/pexpect
  credential caching (wiped at exit); single-flight parallel sudo.
- **Config**: `~/.config/neoarch`; ignored updates at
  `~/.config/neoarch/ignored_updates.json`.
- **Structure**: `neoarch/frontend` (main window, mixins, components,
  settings pages), `neoarch/backend` (services, auth, cloud auth,
  sys_utils, workers, askpass), `neoarch/managers` (docker, git, plugins).
- **Tests**: automated suite (46+ tests — installers, uninstallers, core
  helpers, release-notes, catalog coverage).
- **Packaging**: AUR PKGBUILD (stable and `-git`), icons, desktop entries,
  appdata; CLI binaries installed to `/usr/bin` (`neo` → `neoarch-cli`).

## What's new / release notes

The app ships `CHANGELOG.md` inside the build and shows a card-style "What's
New" dialog after an update, plus silently notifies when a newer release is
available (dev preview toggles: `NEOARCH_PREVIEW_WHATS_NEW`,
`NEOARCH_PREVIEW_UPDATE`).

Latest notable additions:

- **3.3.0** — Snapper (BTRFS) support with reworked Settings UI; header quick
  actions pill (Refresh, Security Settings, Arch News, quick search, live
  signal); strengthened PKGBUILD scanner; AUR packages scanned before build
  starts; page-state preservation when navigating between pages.
- **3.2.0** — Full i18n with 10 language catalogs; What's New release notes;
  Security panel in Settings; Update Review dialog; partial-update warnings;
  new installed/updates filters.
- **3.1.x** — Rewritten terminal output with indexed badges; install from
  archive URL; CLI aliases & PATH installs; Arch News in-app; per-package
  AUR updates; unified session-cached auth; dependency center; window-frame
  settings; redesigned About page; real automated test suite.

---

**Last updated:** September 2026  
**Version:** 3.3.0 "Lynx"