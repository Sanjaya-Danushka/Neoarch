# NeoArch Roadmap

Feature plan derived from a feature-gap comparison with Shelly-ALPM. Each item lists the implementation targets (services/tests/UI) following the existing architecture: backend services in `neoarch/backend/services/`, UI mixins in `neoarch/frontend/mixins/`, views in `neoarch/frontend/views/`, tests in `tests/`.

## Phase 1 — CLI (v2.3) ✅ Implemented

Command-line interface mirroring the GUI, enabling scripting and automation.

- **Done** — `neoarch/cli.py` (argparse) invoked via `python -m neoarch.cli` and `bin/neoarch-cli`.
- Commands implemented: `search`, `install`, `remove`, `upgrade`, `update`, `list`, `list-updates`, `news`, `backup`, `purge`, `ignore`, `config get/set/reset`, `doctor`.
- Flags: `--json`, `--no-confirm`, `--yes` (accepted before or after the subcommand).
- Reuses pure backend services (`search.py`, `sys_utils.py`, `config_utils.py`, `hygiene.py`) — Qt-free, runs headless.
- Tests: `tests/test_cli.py` (7 tests).

## Phase 2 — PKGBUILD Security Scanner (v2.3) ✅ Implemented

Pre-install security review for AUR installs/updates.

- **Done** — `neoarch/backend/services/security_scan.py`:
  - Static scan of PKGBUILD + `.install` scriptlets (never executes).
  - Detects: risky post-install tools (`npm`, `npx`, `pip`, `curl`, `wget`, `bun`, `yarn`, `pnpm`), dynamic command construction (`eval`, `$(...)`, backticks, `${!var}`, `base64 -d | sh`, pipe-to-shell), local ELF/binary `source=()` files (magic-byte/`\x7fELF` check), privilege elevation (`sudo`, `doas`, `pkexec`, `run0`, `su`), Unicode homograph spoofing (mixed-script/confusable chars, zero-width/bidi controls).
  - Lightweight de-obfuscation before matching (`b''u''n`, `cur\l`).
  - Returns findings with severity (`info`/`warning`/`critical`), rule, context, matched line.
- **Done** — CLI: `neoarch-cli scan <PKGBUILD...>` (human + `--json`), exit code 2 on critical findings.
- **Todo** — UI: security banner + finding list in the AUR package review dialog before install.
- **Done** — Tests: `tests/test_security_scan.py` (27 tests).

## Phase 3 — Package Lifecycle (v2.4)

### Downgrade ✅ Implemented

- **Done** — `neoarch/backend/services/downgrade.py`: `list_cached_versions` (parses `/var/cache/pacman/pkg` via pacman.conf `CacheDir`), `install_version` (`pacman -U --noconfirm`, version or explicit path), optional `add_to_ignorepkg`/`remove_from_ignorepkg` (`/etc/pacman.conf`), `vercmp`-ordered version sorting (binary + stdlib fallback).
- **Done** — CLI: `neoarch-cli downgrade <pkg> [--version ...] [-l|--list-only] [-p|--pin]`.
- **Todo** — UI: "Downgrade" action on installed package; version picker dialog.
- **Done** — Tests: `tests/test_downgrade.py` (17 tests).

### IgnorePkg / HoldPkg / install-reason marking

- `neoarch/backend/services/marks.py`: read/write `IgnorePkg` and `HoldPkg` in `/etc/pacman.conf`, and `pacman -D --asdeps/--asexplicit` reason marking.
- UI: per-package "Ignore updates" now drives real `IgnorePkg`; new Hold + explicit/dependency toggles.
- Tests: `tests/test_marks.py`.

### AppImage manager

- `neoarch/backend/services/appimage.py`: managed store (`~/.local/share/neoarch/appimages`), metadata DB, update-check via static URL or GitHub/GitLab/Codeberg/Forgejo repo releases, sync, desktop-entry + icon registration, removal.
- UI: AppImage tab under Discover/Installed; per-AppImage update tracking.
- Tests: `tests/test_appimage.py`.

## Phase 4 — System Depth (v2.4)

### Pacman keyring manager

- `neoarch/backend/services/keyring.py`: `pacman-key --init/--populate/--refresh-keys`, list keyring, receive/locally-sign keys, GUI-backed.
- Tests: `tests/test_keyring.py`.

### Purify / cache retention

- Extend `hygiene.py`: corrupted-archive detection, `paccache -rk<N>` retention, Flatpak unused-dependency cleanup (`flatpak uninstall --unused`).
- Tests extended in `tests/test_hygiene.py`.

### Three-way pacnew merge

- Extend `hygiene.py`: `diff3`/`meld`-style three-way merge using cached package archives as base; `.bak` backup before accept.
- Tests extended in `tests/test_hygiene.py`.

### Restart-required detection

- `neoarch/backend/services/restart_check.py`: flag kernel/vulkan/glibc/other upgrades needing a reboot; prompt in update flow.
- Tests: `tests/test_restart_check.py`.

## Phase 5 — UX & Integration (v2.5)

### Tray icon + scheduled checks

- `QSystemTrayIcon` with update-count badge; weekly schedule (days-of-week + time) configurable in Settings; click-to-open main window.
- Extend `settings_auto_update.py`.

### Parallel downloads

- Configurable `ParallelDownloadCount` written to `/etc/pacman.conf` (`ParallelDownloads`).

### Recommended packages

- Curated recommendations feed in Discover (sourced from local plugin data + popularity).

### Translations / i18n

- `gettext`-based `.ts`/`.qm` pipeline (Qt Linguist) + `Culture` setting; start with English + Sinhala + Spanish stubs.

## Phase 6 — Headless helpers (v2.5)

- `install_from_url`: install package archives from HTTP(S) URLs.
- AUR build depth: clean-chroot (`makechrootpkg`) opt-in, `check()` enable, install-at-commit.
- News read-tracking: per-entry `seen` state persisted alongside the existing RSS cache.

---

## Priority summary

| Priority | Items |
| --- | --- |
| P0 | CLI, PKGBUILD security scanner |
| P1 | Downgrade, IgnorePkg/HoldPkg marks, AppImage manager |
| P2 | Keyring, purify, three-way merge, restart detection |
| P3 | Tray, parallel downloads, recommended, i18n, URL install, chroot builds, news read-tracking |

License note: all items are clean-room implementations; no GPL code is copied from Shelly-ALPM (NeoArch stays MIT).
