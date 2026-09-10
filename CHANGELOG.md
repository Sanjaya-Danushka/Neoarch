# NeoArch Changelog

All notable changes to NeoArch are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to a pragmatic version of it: one section per release
with `New Features`, `Bug Fixes`, and `Improvements` sub-headings.

This file ships inside every NeoArch build and is what the What's New
dialog shows after an update.

---

## Unreleased (dev branch)

Changes on the `dev` branch that will land in the next release.

### Bug Fixes

- Navigating between pages no longer discards the page's state. Returning to
  **Updates**, **Installed**, or **Discover** restores your search text, the
  displayed results, and the checked/selected packages instead of wiping the
  page; re-entering **Updates** during a running install shows the list in
  place (the operation keeps running in the console) rather than a blank
  page. The install/update progress animation and its Cancel button are now
  confined to the page where the operation started: navigating away hides
  them, and returning to that page brings the spinner **and** the Cancel
  button back (a previous visit to another page had left the button hidden).
  During a running install/update the
  **Installed** page never claims the system is empty: it reuses the last
  loaded installed list, or shows a calm "Waiting for the update to finish"
  message and refreshes automatically once the operation releases the
  package database. Use the toolbar Refresh button to force a fresh data
  reload.

### Improvements

- The PKGBUILD pre-install scanner now detects byte-level command obfuscation
  (ANSI-C `$'\\x..'` quoting, `printf`-spelled commands, variable-split
  reassembly), Tor/SOCKS-proxied fetches, downloads straight into system
  paths, AUR self-propagation references, non-interactive mutating
  `pacman --noconfirm` calls, duplicate `source=()` declarations, and
  unchecked mutable MR/PR diff sources — layered defense rules ported from
  the `archcanary` pre-build scanner. Exposed via `neo scan <PKGBUILD>`
  (`--json` supported).
- AUR packages selected for installation are now fetched from the AUR and
  statically scanned before the build starts. Critical findings block the
  install until the risk is explicitly accepted; warnings still require a
  confirmation. If the scan cannot reach the AUR, the install falls back to
  the legacy static notice so it is never stuck — a soft gate, not a hard
  dependency.

---

## 3.2.0 — 2026-09-09

Changes on the `dev` branch that land in this release.

### New Features

- **Full internationalization (i18n).** The entire interface — every dialog,
  table header, tooltip, and notification — is now translatable. Ships with
  10 complete language catalogs (Spanish, Sinhala, Hindi, German, French,
  Portuguese, Chinese, Russian, Turkish, Japanese); the language is detected
  automatically from your system on first launch and can be changed from
  Settings.
- **What's New release notes.** After an update the app shows a card-style
  summary of exactly what this release added and fixed (built from the
  curated `CHANGELOG.md` that ships with the package), and it silently
  notifies you when a newer NeoArch release is available.
- **Security panel in Settings.** A dedicated panel for reviewing package
  sources and gating operations, plus PKGBUILD review tools so you can inspect
  exactly what an AUR package will run before you build it.
- **Update Review dialog.** Updates are now previewed before they run, with
  per-package details, so you always know what is about to change.
- **Partial-update warnings.** Selecting part of the available Arch updates now
  triggers an explicit warning, so silent partial upgrades can never break
  dependencies without you noticing.
- **New installed/updates filters** such as "installed, has update" and a fixed
  "Updates Installed" column, making the lists more useful at a glance.

### Bug Fixes

- Fixed installed-date and download-size reporting for Flatpak and npm
  packages in the updates list.
- Fixed filter/loader edge cases that could hide rows or sort incorrectly on
  the Installed and Updates pages.
- Lights, Nord, and Dracula themes are temporarily disabled (marked "Coming
  soon") until they are finished, so selecting them can no longer half-apply
  a broken appearance.
- Repaired four orphaned dev files: the plugin-submission script (broken
  import of a removed module), the stale deep-clean script (checked for the
  legacy `aurora_home.py`), the scheduled-update systemd service (pointed at a
  missing script), and the community-plugins index (listed plugins that did
  not exist).
- 10-language catalog coverage passes strict verification (0 missing strings).

### Improvements

- Rebuilt the i18n pipeline so adding a language means dropping a catalog file
  in — no code changes needed.
- New automated tests for the release-notes service and the 10 catalog
  coverage checks.

---

## 3.1.3 — 2026-09-06

### New Features

- Rewritten terminal output. The CLI now renders search results as an
  indexed list with color-coded source badges, a compact card layout for
  narrow terminals, and column-aligned tables with headers and line wrapping.
- Smarter `neo install`. Installing by search index shows the resolved
  source (pacman / AUR / URL archive) and asks for confirmation before running.
- `neo install <archive-url>`. Install a package archive directly from an
  HTTP(S) URL, with source validation.
- Simple CLI aliases. `updates`, `down`, `hold`, `clean`, `keys`, `reboot`
  and `build` are available as shortcuts (e.g. `neo updates` lists available
  updates).
- CLI on PATH. Both `neo` and `neoarch-cli` are installed to `/usr/bin` by
  the package, so they work no matter the working directory.

### Bug Fixes

- Fixed the packaged binaries: the install step now creates `/usr/bin` and
  points both CLI symlinks at the correct install path, so `neo` no longer
  resolves to a stale or missing file after installation.

### Improvements

- Full CLI reference in the README, plus a dark-styled cover, a side-by-side
  framed screenshot gallery, and a verified install section.
- Packaging cleanup: `pkgver` no longer contains forbidden hyphens and the AUR
  workflow tags releases correctly.

---

## 3.1.2 — 2026-09-06

### New Features

- Arch News in-app. A button on the Home (Discover) view reads the official
  Arch Linux news feed, with an offline fallback and a cached copy so you can
  read the latest announcements without a connection.
- Per-package AUR updates. Individual AUR packages can be updated on their
  own instead of only as part of a bulk refresh.
- Cloud portal. The Clerk account-settings portal is enabled and the
  Supabase schema is versioned with migrations, so cloud bundle sync is safer
  to evolve.
- Real automated test suite. 46 tests covering installers, uninstallers,
  and core helpers, so regressions are caught earlier.

### Bug Fixes

- Network latency signal bars no longer flicker, lag, or fire false
  "connection restored" notifications.
- Replaced 38 silent `except: pass` handlers with proper logging so hidden
  failures are visible in the log instead of being swallowed.
- Fixed broken test imports and made the appimage/install_url tests
  deterministic (no more flaky network tests).

### Improvements

- Removed 30 dead functions across 14 files (−463 lines of dead code).
- CodeQL and Codacy lint findings resolved (redundant imports, unused symbols).
- Website links now point to neoarch.dpdns.org.

---

## 3.1.1 — 2026-08-24

### New Features

- Unified authentication. All privileged operations now share one themed,
  session-cached password dialog. The sudo password is cached in the system
  keyring (with a `0600` fallback file) so you are not prompted for every
  command — and it is wiped when the app exits.
- Snapshots and plugins use the same prompt. `pkexec` was removed from both
  so there is a single, predictable authentication flow.
- Dependency Center UX. Installing a missing package from the update flow
  is clearer, and dependency status is surfaced in one place.
- Window frame settings. Configure the window decorations toggled from
  Settings instead of relying on the desktop environment.
- Redesigned About page with a Community tab, book-style documentation, and
  a refreshed look; the old Profile page was replaced by an avatar account menu.

### Bug Fixes

- Fixed a false-positive gnome-keyring check that claimed the keyring daemon
  was missing when only the binary name had changed.
- Parallel `sudo` requests are now guarded with a single-flight mechanism and a
  working Cancel button — no more double prompts or hangs.
- Update checks retry transient source failures and merge every source into the
  final list instead of dropping a source that briefly failed.

### Improvements

- Removed orphaned components and unused view methods (dead-code cleanup).
- AUR package versioning is now monotonic (`.r<count>.<g<hash>`), so `yay` and
  `paru` always detect a newer dev build as an upgrade.

---

## 3.1.0 — 2026-08-21

### New Features

- Redesigned Home dashboard. Live source cards with a health ring, storage
  and stats footers, iOS-style quick actions; a live selection counter and an
  "update selected" action on the Updates panel.
- Search improvements. Sorted and filtered results ("hide installed",
  sort options), "did you mean" suggestions for zero-result searches, and
  results rendered through the shared updates table.
- Installed page. Search filtering, an installed-date column, an update
  flag per package, and an uninstall menu.
- Extended discovery. Search results stream in as you type, with a loading
  indicator and a no-results message instead of a silent empty page.
- Plugins revamped. Cards-only view, category source panel with statuses,
  batch install, hover uninstall, and real-time card state.
- AppImages, Git Projects, and Docker pages redesigned to match one
  cohesive visual identity.
- Cloud bundles redesign. Table layout, share/import code cards, compact
  sizing, and darker dialogs to match the theme.

### Bug Fixes

- Removed the `nanoid` dependency vulnerability (upgraded to `>=3.3.18`).
- Fixed several packaging paths: the icon, desktop entry, and install scripts
  now resolve correctly under `/opt/neoarch/Neoarch`; `.SRCINFO` is generated
  from the git revision in CI.
- Cache cleanup now runs with the right privileges and refreshes the health
  counts immediately afterwards.
- Fixed a toast crash and made the cancel button stay visible during long
  operations.

### Improvements

- AUR auto-publish workflow runs on every push to `dev`, pushing via SSH with
  a permissions block added to the workflows.
- Health scoring softened and orphan/pacnew counts applied immediately.
- Reorganized the icon set into `sources/`, `toolbar/`, `status/`, `ui/`, and
  `screenshots/` and reused it across pages.
