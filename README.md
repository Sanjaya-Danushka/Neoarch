<div align="center">
  <img src="https://neoarch.netlify.app/logo.png" alt="NeoArch Logo" width="120"/>

  # NeoArch

  **Modern Package Manager for Arch Linux**

  <p>
    <a href="https://neoarch.netlify.app/">
      <img src="https://img.shields.io/badge/Website-neoarch.netlify.app-00BFAE?style=for-the-badge&logo=netlify&logoColor=white" alt="Website"/>
    </a>
    <a href="https://github.com/Sanjaya-Danushka/Neoarch/releases">
      <img src="https://img.shields.io/github/v/release/Sanjaya-Danushka/Neoarch?style=for-the-badge&color=00BFAE&label=Version" alt="Version"/>
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/github/license/Sanjaya-Danushka/Neoarch?style=for-the-badge&color=00BFAE" alt="License"/>
    </a>
    <a href="https://github.com/Sanjaya-Danushka/Neoarch/issues">
      <img src="https://img.shields.io/github/issues/Sanjaya-Danushka/Neoarch?style=for-the-badge&color=00BFAE" alt="Issues"/>
    </a>
  </p>

  <p>
    <a href="#features">Features</a> •
    <a href="#installation">Installation</a> •
    <a href="#usage">Usage</a> •
    <a href="#contributing">Contributing</a> •
    <a href="#license">License</a>
  </p>

<img width="1213" height="816" alt="home" src="https://github.com/user-attachments/assets/3f497a29-bfef-4a86-a100-b898653bdaab" />

</div>
<br>
<br>
Preview: <a href="https://neoarch.netlify.app/">https://neoarch.netlify.app/</a>

---

## Features

<table>
  <tr>
    <td width="50%">
      <h3>Multi-Source Management</h3>
      <p>Unify pacman, AUR, Flatpak, and npm under one interface. Search, install, update, and remove packages from any source seamlessly.</p>
    </td>
    <td width="50%">
      <h3>Plugin System</h3>
      <p>50+ built-in plugins with an extensible Python hook system supporting lifecycle hooks (on_startup, on_tick, on_view_changed). Browse and install community plugins from the store.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>Bundle System</h3>
      <p>Create portable package bundles for easy deployment. Export, import, install, and share bundles locally or as community bundles.</p>
    </td>
    <td width="50%">
      <h3>Docker Manager</h3>
      <p>Pull, run, list, stop, and clean containers with port mappings, volumes, environment variables, GPU passthrough, and restart policies.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>Git Manager</h3>
      <p>Clone, build, update, and clean Git projects with a click. Auto-detects build methods: Cargo, Autotools, Makefile, and custom build commands.</p>
    </td>
    <td width="50%">
      <h3>Snapshot Integration</h3>
      <p>Create and restore Timeshift snapshots before updates. Revert to a known good state if anything goes wrong. Automatic cleanup of old snapshots.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>Cloud Sync</h3>
      <p>Sign in with Supabase via OAuth to sync bundle favorites across devices. Session tokens are cached securely for seamless re-authentication.</p>
    </td>
    <td width="50%">
      <h3>Scheduled Updates</h3>
      <p>Set and forget with configurable auto-update intervals (1-30 days), auto-refresh, and optional snapshot-before-update via built-in plugins.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>Local Package Install</h3>
      <p>Install <code>.pkg.tar.zst</code>, <code>.AppImage</code>, and <code>.flatpakref</code> files with a single click. Auto-detects package type and handles installation with appropriate privileges.</p>
    </td>
    <td width="50%">
      <h3>Auth & Credential Caching</h3>
      <p>Secure session-based sudo credential caching with auto-cleaning on exit. GUI password dialog with SUDO_ASKPASS support for polkit and sudo-A.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>System Cache Cleaning</h3>
      <p>One-click BleachBit cache cleaning and pacman package cache cleanup (<code>pacman -Sc</code>). Reclaim disk space without leaving the app.</p>
    </td>
    <td width="50%">
      <h3>Ignore Updates</h3>
      <p>Mark specific packages to ignore during updates. Persisted to <code>~/.config/neoarch/ignored_updates.json</code> — survives reboots and updates.</p>
    </td>
  </tr>
</table>

## Screenshots

<div align="center">
  <table>
    <tr>
      <td><img src="https://github.com/user-attachments/assets/eedc4d2f-c806-4089-9842-695d04fbd7df" alt="Search Packages" width="400"/></td>
      <td><img src="https://github.com/user-attachments/assets/b34f304e-c521-45de-8fad-2a78642d5dbc" alt="Installed Packages" width="400"/></td>
    </tr>
    <tr>
      <td align="center"><em>Search & Discover Packages</em></td>
      <td align="center"><em>Installed Packages View</em></td>
    </tr>
  </table>
</div>

## Installation

### From AUR (Recommended)

```bash
yay -S neoarch-git    # or paru -S neoarch-git
```

### Prerequisites

- **OS:** Arch Linux (or Arch-based distro)
- **Python:** 3.8+
- **PyQt6**
- **Administrative privileges** (sudo) for package operations

### Install Dependencies

**Option A — Arch packages (recommended)**

```bash
sudo pacman -S --needed python python-pyqt6 python-requests qt6-svg git flatpak nodejs npm
```

**Option B — Python virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_pyqt.txt
```

> **Note:** On Arch, using system `pip` often triggers the "externally-managed-environment" error. Prefer Option A (pacman) or use a virtual environment (Option B). You can also use `pipx` (`sudo pacman -S python-pipx`) which manages a dedicated venv for each app.

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
|--------|-------------|
| **Discover Packages** | Search and browse available packages from pacman, AUR, Flatpak, and npm |
| **Install Packages** | Select and install packages with a single click |
| **Manage Updates** | View and install available system updates across all sources |
| **Plugins** | Enable, disable, and create Python hook plugins; browse community plugins |
| **Bundles** | Create, export, import, and install package bundles |
| **Docker** | Pull, run, stop, and clean Docker containers with port mappings and volumes |
| **Git** | Clone, build, update, and clean Git projects with auto-detected build methods |
| **Snapshots** | Create and restore Timeshift snapshots before risky operations |
| **Local Files** | Install `.pkg.tar.zst`, `.AppImage`, `.flatpakref` files directly |
| **Cloud Sync** | Sign in with Supabase to sync favorites across devices |

## Development

```bash
git clone https://github.com/Sanjaya-Danushka/Neoarch.git
cd Neoarch
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_pyqt.txt
python Neoarch.py
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

If you discover any security vulnerabilities, report them immediately to **dsanjaya712@gmail.com**.

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p>
    Built with ❤️ by <a href="https://github.com/Sanjaya-Danushka">Sanjaya Danushka</a>
  </p>
  <p>
    <a href="https://neoarch.netlify.app/">Website</a> •
    <a href="https://github.com/Sanjaya-Danushka/Neoarch/issues">Issues</a> •
    <a href="https://github.com/Sanjaya-Danushka/Neoarch/discussions">Discussions</a> •
    <a href="https://github.com/Sanjaya-Danushka/Neoarch/releases">Releases</a>
  </p>
  <a href="https://www.buymeacoffee.com/sanjayadanushka" target="_blank">
    <img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=☕&slug=sanjayadanushka&button_colour=FF5F5F&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00" alt="Buy Me A Coffee"/>
  </a>
</div>
