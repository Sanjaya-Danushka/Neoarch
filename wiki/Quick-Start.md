# Quick Start Guide

Get NeoArch up and running in 5 minutes!

## Installation (2 minutes)

```bash
# Install from AUR
yay -S neoarch-git

# Or manually
git clone https://github.com/Sanjaya-Danushka/Neoarch.git
cd Neoarch
pip install -r requirements_pyqt.txt
python aurora_home.py
```

## Launch NeoArch

```bash
# From terminal
python aurora_home.py

# Or from application menu (if installed from AUR)
# Search for "NeoArch" in your application launcher
```

## First Steps

### 1. **Discover New Packages**
- Click the **Discover** tab in the sidebar
- Use the search bar to find packages
- Browse across Pacman, AUR, Flatpak, and npm sources

### 2. **Search for a Package**
- Type a package name (e.g., "firefox", "vscode")
- Results appear instantly from all sources
- Click on a package to see details

### 3. **Install a Package**
- Find the package you want
- Click the **Install** button
- Authenticate when prompted
- Wait for installation to complete

### 4. **Check Updates**
- Click the **Updates** tab
- Review available updates
- Click **Update All** or select specific packages
- Authenticate and wait for updates

### 5. **Manage Installed Packages**
- Click the **Installed** tab
- View all installed packages
- Search for specific packages
- Click **Uninstall** to remove packages

## Main Interface

```
┌─────────────────────────────────────────────┐
│  NeoArch - Package Manager                  │
├──────────┬──────────────────────────────────┤
│ Discover │  [Search Bar]                    │
│ Updates  │                                  │
│ Installed│  Package Results                 │
│ Plugins  │                                  │
│ Bundles  │  [Install] [Uninstall]           │
│          │                                  │
│ Settings │                                  │
│ About    │                                  │
└──────────┴──────────────────────────────────┘
```

## Navigation

| Tab | Purpose |
|-----|---------|
| **Discover** | Search and install new packages |
| **Updates** | Manage system updates |
| **Installed** | View and manage installed packages |
| **Plugins** | Extend NeoArch with plugins |
| **Bundles** | Create package collections |

## Common Tasks

### Search for a Package
1. Click **Discover**
2. Type package name in search bar
3. Browse results from all sources

### Install a Package
1. Search for the package
2. Click **Install** button
3. Enter password when prompted
4. Wait for installation

### Update System
1. Click **Updates** tab
2. Review available updates
3. Click **Update All** or select packages
4. Enter password and wait

### Uninstall a Package
1. Click **Installed** tab
2. Search for the package
3. Click **Uninstall** button
4. Confirm removal

### Create a Bundle
1. Click **Bundles** tab
2. Select packages you want
3. Click **Create Bundle**
4. Name and save your bundle

## Package Sources

| Source | Type | Use Case |
|--------|------|----------|
| **Pacman** | Official | System packages, stable software |
| **AUR** | Community | Latest versions, niche software |
| **Flatpak** | Universal | Cross-distro apps, sandboxed |
| **npm** | JavaScript | Dev tools, Node.js packages |

## Tips & Tricks

💡 **Search Tips**
- Search by package name: `firefox`
- Search by description: `web browser`
- Use partial names: `fire` finds `firefox`

⚡ **Performance**
- Use filters to narrow results
- Sort by relevance or popularity
- Cache is updated automatically

🔒 **Security**
- Always review AUR packages before install
- Keep system updated regularly
- Use official repos when possible

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Focus search bar |
| `Ctrl+R` | Refresh packages |
| `Ctrl+I` | Install selected |
| `Ctrl+U` | Update selected |
| `F1` | Show help |

## Next Steps

- Read the full [User Guide](User-Guide.md)
- Learn about [Package Sources](Package-Sources.md)
- Explore [Plugins](Plugins.md)
- Check [FAQ](FAQ.md) for common questions

---

**Stuck?** Check [Troubleshooting](Troubleshooting.md) or ask in [GitHub Discussions](https://github.com/Sanjaya-Danushka/Neoarch/discussions)
