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

### IgnorePkg / HoldPkg / install-reason marking ✅ Implemented

- **Done** — `neoarch/backend/services/marks.py`: read/write `IgnorePkg` and `HoldPkg` in `/etc/pacman.conf` (append + safe sed removal, shell-injection guarded), `pacman -D --asexplicit/--asdeps` reason marking, `pacman -Qi` reason lookup.
- **Done** — CLI: `neoarch-cli marks list|ignore|unignore|hold|unhold|reason <pkg> [explicit|deps]` (with `--json`).
- **Done** — `downgrade.py` now delegates IgnorePkg handling to `marks.py`.
- **Todo** — UI: per-package "Ignore updates" drives real `IgnorePkg`; Hold + explicit/dependency toggles.
- **Done** — Tests: `tests/test_marks.py` (15 tests).

### AppImage manager ✅ Implemented

- **Done** — `neoarch/backend/services/appimage.py`: managed store (`~/.local/share/neoarch/appimages`), JSON metadata DB, install from file/URL/repo release, update-check via static URL or GitHub/GitLab/Codeberg/Forgejo releases, `--appimage-extract` metadata introspection (name/icon/desktop, never executes), desktop-entry + icon registration, `pacman`-style version compare, update install, removal, disk sync. Pure stdlib — headless.
- **Done** — CLI: `neoarch-cli appimage list|add|add-url|add-repo|remove|check|update|sync` (with `--json`).
- **Todo** — UI: AppImage tab under Discover/Installed; per-AppImage update tracking.
- **Done** — Tests: `tests/test_appimage.py` (20 tests).

## Phase 4 — System Depth (v2.4)

### Pacman keyring manager ✅ Implemented

- **Done** — `neoarch/backend/services/keyring.py`: `pacman-key --init/--populate/--refresh-keys`, list trusted keys (fingerprint/uid/created), key details, receive + locally-sign keys. Pure stdlib; mutations run elevated via the app's auth helpers; key ids validated against `^[0-9A-Fa-f]{8,40}$`.
- **Done** — CLI: `neoarch-cli keyring list|details|init|populate|refresh|receive|sign` (with `--json`).
- **Todo** — UI: keyring tab with receive/sign workflows.
- **Done** — Tests: `tests/test_keyring.py` (8 tests).

### Purify / cache retention ✅ Implemented

- **Done** — `hygiene.py`: corrupted-archive detection (`bsdtar -tf` verification across all `CacheDir`s), `paccache -r -k<N>` retention, Flatpak unused-dependency cleanup (`flatpak uninstall --unused`).
- **Done** — CLI: `neoarch-cli purify corrupt|cache [--keep N]|flatpak` (with `--json`).
- **Todo** — UI: corruption scan + cache-age chart in Purify dialog.
- **Done** — Tests: `tests/test_hygiene.py` extended (4 new tests).

### Three-way pacnew merge ✅ Implemented

- **Done** — `hygiene.py` `merge_pacnew()`: `diff3 -m` three-way merge. Base extracted from the owning package's cached archive (`bsdtar -xOf`), falling back to the current original; `.pacsave` backup before accept; conflict-marked `.merged` output for manual review when conflict-free acceptance is not possible.
- **Done** — CLI: `neoarch-cli purify merge <path> [--accept]` (exits 2 on conflicts).
- **Todo** — UI: merge preview in the .pacnew dialog.
- **Done** — Tests: `tests/test_hygiene.py` (4 merge tests).

### Restart-required detection ✅ Implemented

- **Done** — `neoarch/backend/services/restart_check.py`: flags new kernels installed but not booted (`/usr/lib/modules` vs `uname -r`, pacman version ordering), plus glibc/systemd/openssl/nss libraries replaced after boot time (`/proc/uptime`). Prompt surfaces in the update flow.
- **Done** — CLI: `neoarch-cli restart check [--json]`.
- **Todo** — UI: restart banner + action button after system upgrade.
- **Done** — Tests: `tests/test_restart_check.py` (9 tests).

## Phase 5 — UX & Integration (v2.5)

### Tray icon + scheduled checks

- **Done** — `neoarch/backend/services/scheduler.py`: pure, Qt-free weekly schedule model — `parse_time`, `validate_schedule`, `next_run` (next matching weekday at HH:MM), `is_due`. Settings keys: `schedule_enabled`, `schedule_days` (0=Monday..6), `schedule_time`.
- **Done** — CLI: `neoarch-cli schedule show|set [--days] [--time] [--enable|--disable]`; config keys settable via `config set`.
- **Todo** — `QSystemTrayIcon` with update-count badge; click-to-open main window; weekly schedule UI in Settings (Auto Update card); a `QTimer` driving `is_due` at startup.
- **Done** — Tests: `tests/test_scheduler.py` (8 tests).

### Parallel downloads

- **Done** — `neoarch/backend/services/pacman_conf.py`: line-preserving read/write of `/etc/pacman.conf` options (`tee` via the app's elevation); `get_parallel_downloads`/`set_parallel_downloads(1..32)`; option names validated against `^[A-Za-z][A-Za-z0-9_]*$`; appends under `[options]` when absent.
- **Done** — CLI: `neoarch-cli parallel [count]`.
- **Todo** — UI: `ParallelDownloads` control in Settings → Network/Performance.
- **Done** — Tests: `tests/test_pacman_conf.py` (7 tests).

### Recommended packages

- **Done** — `neoarch/backend/services/recommend.py`: curated feed (30 packages across browser/terminal/editor/notes/media/graphics/utilities/security/development/productivity/communication) merged with optional cached AUR popularity scores; `installed` flags; popularity-sorted, no network at read time.
- **Done** — CLI: `neoarch-cli recommend [--limit N] [--installed]` (with `--json`).
- **Todo** — UI: recommendations feed in Discover.
- **Done** — Tests: `tests/test_recommend.py` (6 tests).

### Translations / i18n

- **Done** — `neoarch/backend/services/i18n.py`: lightweight gettext-style `.po` loader (no msgfmt step) from `neoarch/locale/<lang>/LC_MESSAGES/neoarch.po`; `set_language`/`get_language`/`translate`/`_`, graceful English fallback, empty-catalog fallback.
- **Done** — Bundled stubs: `neoarch/locale/si` (Sinhala) and `neoarch/locale/es` (Spanish) with starter entries; `culture` setting (default `en`).
- **Todo** — Qt Linguist `.ts`/`.qm` pipeline for widget strings; `Culture` UI in Settings.
- **Done** — Tests: `tests/test_i18n.py` (8 tests, includes loading the shipped stubs).

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
