# User Guide

Complete guide to using NeoArch for package management on Arch Linux.

## Getting Started

Welcome to NeoArch! This guide will help you master all features of NeoArch.

## Interface Overview

NeoArch provides an intuitive graphical interface with several key areas:

### Main Window Components

```
┌─────────────────────────────────────────────────────┐
│  NeoArch - Package Manager                          │
├──────────┬────────────────────────────────────────┤
│          │  [Search Bar]                           │
│ Discover │                                         │
│ Updates  │  Package Results                        │
│ Installed│  ┌──────────────────────────────────┐  │
│ Plugins  │  │ Package Name                     │  │
│ Bundles  │  │ Description                      │  │
│          │  │ [Install] [Uninstall] [Details] │  │
│          │  └──────────────────────────────────┘  │
│ Settings │                                         │
│ About    │                                         │
└──────────┴────────────────────────────────────────┘
```

### Sidebar Navigation

- **Discover** - Browse and search packages from all sources
- **Updates** - Manage system updates
- **Installed** - View and manage installed packages
- **Plugins** - Extend NeoArch with plugins
- **Bundles** - Create and manage package collections
- **Settings** - Configure NeoArch preferences
- **About** - View version and credits

## Package Management

### Searching for Packages

1. Click the **Discover** tab
2. Type package name in the search bar
3. Results appear instantly from all sources
4. Click on a package to see details

**Search Tips:**
- Search by name: `firefox`
- Search by description: `web browser`
- Use partial names: `fire` finds `firefox`

### Installing Packages

1. Search for the desired package
2. Click the **Install** button
3. Authenticate with your password
4. Wait for installation to complete

**Installation Options:**
- Install single package
- Install multiple packages at once
- Choose installation source (Pacman, AUR, Flatpak, npm)

### Updating Packages

1. Click the **Updates** tab
2. Review available updates
3. Select packages to update (or click **Update All**)
4. Authenticate and wait

**Update Options:**
- Update all packages
- Update specific packages
- Skip certain packages
- Schedule automatic updates

### Removing Packages

1. Click the **Installed** tab
2. Search for the package
3. Click the **Uninstall** button
4. Confirm removal

**Removal Options:**
- Remove package only
- Remove with dependencies
- Remove configuration files

## Package Sources

### Pacman (Official Repositories)

- **Type:** Official Arch Linux packages
- **Stability:** Very stable, well-tested
- **Use Case:** System packages, core software
- **Updates:** Regular, security-focused

### AUR (Arch User Repository)

- **Type:** Community-maintained packages
- **Stability:** Variable, requires review
- **Use Case:** Latest versions, niche software
- **Updates:** User-driven, cutting-edge

**AUR Safety Tips:**
- Always review PKGBUILD before installation
- Check comments for issues
- Use trusted maintainers
- Test in virtual machine first

### Flatpak

- **Type:** Universal packages
- **Stability:** Good, sandboxed
- **Use Case:** Cross-distro apps, proprietary software
- **Updates:** Automatic, isolated

### npm (Node Package Manager)

- **Type:** JavaScript packages
- **Stability:** Varies by package
- **Use Case:** Dev tools, Node.js libraries
- **Updates:** Frequent, version-managed

## Advanced Features

### Bundle Management

Create collections of packages for easy deployment:

1. Click **Bundles** tab
2. Select packages you want to bundle
3. Click **Create Bundle**
4. Name your bundle
5. Save for later use

**Bundle Uses:**
- Development environment setup
- Server configuration
- System customization
- Sharing configurations

### Plugin System

Extend NeoArch with custom plugins:

1. Click **Plugins** tab
2. Browse available plugins
3. Click **Install** on desired plugin
4. Restart NeoArch to activate

**Plugin Categories:**
- System tools
- Development utilities
- Customization
- Integration tools

### Settings

Customize NeoArch behavior:

**General Settings:**
- Theme (Light/Dark)
- Language
- Window size and position
- Auto-start on login

**Package Sources:**
- Enable/disable sources
- Set default source
- Configure AUR helper
- Manage Flatpak remotes

**Auto Updates:**
- Enable automatic checks
- Set check frequency
- Choose update behavior
- Notification preferences

**Advanced:**
- Cache settings
- Logging level
- Performance options
- Experimental features

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Focus search bar |
| `Ctrl+R` | Refresh package list |
| `Ctrl+I` | Install selected |
| `Ctrl+U` | Update selected |
| `Ctrl+D` | Remove selected |
| `F1` | Show help |
| `F5` | Refresh |
| `Esc` | Clear search |

## Best Practices

### Security

- Always review AUR packages before installation
- Keep your system updated regularly
- Use official repositories when possible
- Be cautious with third-party plugins
- Monitor installed packages

### Performance

- Regularly clean package cache: `paccache -r`
- Remove unused packages: `pacman -Qdtq | pacman -Rns -`
- Use SSDs for better performance
- Disable unused package sources
- Monitor disk usage

### Maintenance

- Check for orphaned packages regularly
- Monitor system updates
- Backup important configurations
- Keep NeoArch updated
- Review plugin compatibility

## Troubleshooting

### Common Issues

**Installation Fails**
- Check internet connection
- Verify package exists
- Check disk space
- Review system logs

**Search Returns No Results**
- Refresh package databases
- Check internet connection
- Try different search terms
- Enable all sources

**Authentication Errors**
- Ensure sudo privileges
- Check polkit installation
- Verify password is correct
- Try running with pkexec

See [Troubleshooting](Troubleshooting.md) for more solutions.

## Tips & Tricks

💡 **Efficiency**
- Use filters to narrow results
- Save frequently used bundles
- Customize keyboard shortcuts
- Use search history

⚡ **Performance**
- Disable unused sources
- Clear cache periodically
- Close other applications
- Use wired internet

🔒 **Security**
- Review packages before install
- Keep system updated
- Use strong passwords
- Monitor installed software

## Next Steps

- Explore [Package Sources](Package-Sources.md)
- Learn about [Bundles](Bundles.md)
- Discover [Plugins](Plugins.md)
- Check [FAQ](FAQ.md) for questions

---

**Need help?** See [Troubleshooting](Troubleshooting.md) or [FAQ](FAQ.md)
