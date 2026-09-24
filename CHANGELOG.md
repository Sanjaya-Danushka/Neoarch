# NeoArch Changelog

All notable changes to NeoArch are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to a pragmatic version of it: one section per release
with `New Features`, `Bug Fixes`, and `Improvements` sub-headings.

This file ships inside every NeoArch build and is what the What's New
dialog shows after an update.

---

## Unreleased

### New Features

- **i18n is now complete**: every string reachable from the interface is
  translated in all ten bundled languages. The redesigned settings pages
  (Security, Logging, Proxy & Network, Maintenance, Repositories),
  the repositories manager, snapshot/snapper dialogs and firmware-update
  flow no longer fall back to English for the de/fr/hi/ja/pt/ru/si/tr/zh
  catalogs, and the Spanish catalog was brought up to date with the latest
  strings too.
- The Updates, Installed and Discover tables now show which pacman repository
  a package comes from (e.g. `Pacman · extra`, `Pacman · chaotic-aur`). The
  source is resolved offline from your synced repo databases, so packages from
  third-party repos like Chaotic AUR are visible at a glance.
- The Settings > **Security** page was redesigned to match the other
  settings tabs (Appearance, Notifications) and now teaches instead of
  merely listing facts:
  - each card explains the *why* behind AUR handling, updates, sudo
    prompts and token caching in plain language;
  - a new **"Do's & Don'ts"** card color-codes the habits that keep an
    Arch system healthy (full upgrades, reading PKGBUILDs, no `curl | bash`)
    and makes clear that risky actions are **warned, never blocked**.
- The header toolbar now has a **Security** quick-link (shield icon, Refresh
  button style) that jumps straight to the Security tab in Settings — on the
  Home header and in the right corner of the Updates/Discover toolbars, next
  to a new Refresh button.
- The Settings > **Logging** page was redesigned to match the other settings
  tabs: the level decoder, console echo and log-file options live in icon
  badged cards with plain-language explanations of *why* each one matters, a
  new **Good Habits** card adds a DO/DON'T quick reference (attach a DEBUG log
  when reporting bugs, leave console echo off during normal use), and the
  size limit uses the same compact stepper as the Notifications page.
- The Settings > **Proxy & Network** page was redesigned to match: proxy
  type, host & port, request timeout and the pacman `ParallelDownloads`
  apply live in icon-badged cards with plain-language explanations, and the
  SSL/parallel toggles are proper switches instead of bare checkboxes.
- The Settings > **Maintenance** page was redesigned to match: each tidy-up
  task (orphans, .pacnew files, corruption scans, cache purging and Arch
  news) is a descriptive card with a consistent action button, and the
  "keep versions per package" choice uses the same compact stepper as the
  other pages.
- The **partial-update warning** is smarter and safer:
  - AUR packages no longer count toward it — they build from source
    against the current system, so only official-repo selections trigger
    the desync warning;
  - the dialog gained a third button: **"Update All (n)"** is now the
    recommended primary action (runs the full system upgrade), the risky
    choice keeps the fully translated **"I understand — Update Selection"**
    text but is now a **red danger** button, and Cancel stays ghost;
  - every string reuses existing catalog entries, so the dialog still
    renders in all ten bundled languages.
- New **Repositories** settings page for managing pacman repositories without
  hand-editing `/etc/pacman.conf`:
  - lists every configured repo (system repos are read-only);
  - **Quick-add Chaotic AUR** — signs the maintainer key, downloads the mirror
    list over HTTPS, appends `[chaotic-aur]` and runs `pacman -Syy`;
  - add any repo by name (optional `Include` / `Server`), enable/disable with a
    toggle, and remove the ones NeoArch added;
  - every write backs up `/etc/pacman.conf` first and restores it on failure;
    hand-written sections are protected from deletion.

---

### Bug Fixes

- Setting up **pipx** from About ▸ Diagnostics no longer "succeeds" while
  installing nothing: the catalog pointed pacman at a literal `pipx` package
  that doesn't exist on Arch (the real one is `python-pipx`). Setup now
  installs `python-pipx`, the Install tooltips in Diagnostics/General/Updates
  show the correct command, and a failed dependency install reports
  "Setup could not complete" instead of the misleading "Setup finished".

## 3.3.1 — 2026-09-22

### New Features

- **Release notes before you update.** The Update Review dialog now has a
  "Release notes" column: packages with a known changelog show a "View
  changes ↗" link that opens the official changelog for that release. It is
  backed by a small curated offline map (package → changelog URL) covering
  common Arch packages and Flatpak apps, so nothing is fetched over the
  network while you review an update.
- **Unusable sources are visibly disabled.** On the Updates, Discover, and
  Installed pages and in Settings, source rows for `flatpak`, `npm`, `pipx`,
  and `fwupd` are greyed out and cannot be toggled when the backing tool is
  not installed, with an install hint (`sudo pacman -S <package>`) on hover.

### Improvements

- **Dependency status now tells required from optional.** The About sidebar
  icon, its count badge, and the Diagnostics nav dot turn red only when a
  *required* dependency is missing. Missing optional components (flatpak,
  npm, docker, pipx, fwupd, …) — which most users do not need — show a green
  state instead, while remaining listed on Diagnostics with their Install
  button. `pipx` was added to the dependency catalog as an optional entry.

---

## 3.3.0 — 2026-09-16

Changes on the `dev` branch that land in this release.

### New Features

- Snapper (BTRFS) support with a reworked Settings UI.
- Header quick actions: Refresh, Security Settings, and Arch News buttons in
  a transparent-black pill alongside quick search and the live signal
  indicator, with uniform 30px icons.

### Bug Fixes

- Navigating between pages no longer discards the page's state. Returning to
  Updates, Installed, or Discover restores your search text, the
  displayed results, and the checked/selected packages instead of wiping the
  page; re-entering Updates during a running install shows the list in
  place (the operation keeps running in the console) rather than a blank
  page. The install/update progress animation and its Cancel button are now
  confined to the page where the operation started: navigating away hides
  them, and returning to that page brings the spinner and the Cancel
  button back (a previous visit to another page had left the button hidden).
  During a running install/update the
  Installed page never claims the system is empty: it reuses the last
  loaded installed list, or shows a calm "Waiting for the update to finish"
  message and refreshes automatically once the operation releases the
  package database. Use the toolbar Refresh button to force a fresh data
  reload.
- Plugins list view now correctly syncs filters, sort, and batch toolbar
  actions (Install Selected, Clear Selection) with the grid view. The table
  model preserves installed-plugin rows as selection-only, and sort changes
  propagate to the list view immediately.
- Header glass panels no longer paint at stale positions when switching
  between table modes (bundles, plugins, discover). Column hide/show now
  explicitly refreshes the section-rect cache so Source and Status column
  headers align correctly with the cells below.

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
- About page now links to the Wiki from the Overview, Documentation, and
  Community tabs. README highlights the Wiki with a "Read before use" note
  and bundles with a "Save your setup for life" callout.

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
