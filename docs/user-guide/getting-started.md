# User Guide

## Getting Started

Welcome to NeoArch! This guide will help you get started with using NeoArch for package management on Arch Linux.

## Installation

### Quick Install
```bash
# Install from AUR (recommended)
yay -S neoarch-git
# or
paru -S neoarch-git
```

### Manual Installation
See the [README.md](../../README.md) for detailed installation instructions.

## Interface Overview

NeoArch provides an intuitive graphical interface with several key areas:

### Main Window
- **Search Bar**: Find packages across all sources
- **Package Table**: View and manage packages
- **Filters Panel**: Filter packages by source, status, etc.
- **Status Bar**: Shows current operation status

### Navigation
- **Discover**: Browse and search packages
- **Updates**: Manage system updates
- **Bundles**: Create and manage package bundles
- **Plugins**: Access additional tools and features

## Package Management

### Searching for Packages

1. Use the search bar at the top
2. Type package names or descriptions
3. Results appear instantly from all sources

### Installing Packages

1. Search for the desired package
2. Check the checkbox next to the package
3. Click the "Install" button
4. Authenticate if prompted

### Updating Packages

1. Go to the "Updates" tab
2. Review available updates
3. Select packages to update
4. Click "Update Selected" or "Update All"

### Removing Packages

1. Find the installed package
2. Check the checkbox
3. Click the "Uninstall" button
4. Confirm the removal

## Package Sources

NeoArch supports multiple package sources:

### Pacman (Official Repositories)
- Official Arch Linux packages
- Most stable and well-tested
- Default source for system packages

### AUR (Arch User Repository)
- Community-maintained packages
- Cutting-edge software
- Requires careful review (use at your own risk)

### Flatpak
- Universal packages that work across distributions
- Sandboxed applications
- Good for proprietary software

### npm (Node Package Manager)
- JavaScript packages and tools
- Development-focused
- Can install globally or locally

## Advanced Features

### Bundle Management

Create collections of packages for easy deployment:

1. Select packages you want to bundle
2. Go to "Bundles" → "Create Bundle"
3. Name your bundle
4. Save it for later use

### Plugin System

Extend NeoArch with plugins:

1. Go to "Plugins" section
2. Browse available plugins
3. Install plugins you need
4. Restart NeoArch to activate

### Settings

Customize NeoArch behavior:

- **General**: UI preferences, update settings
- **Auto Updates**: Configure automatic update checks
- **Plugins**: Manage installed plugins

## Troubleshooting

### Common Issues

**Authentication Failed**
- Ensure you have sudo privileges
- Check that polkit is properly configured
- Try running NeoArch with `pkexec`

**Package Not Found**
- Check your internet connection
- Refresh package databases
- Verify package name spelling

**Installation Errors**
- Check system logs with `journalctl -xe`
- Ensure all dependencies are installed
- Try installing from a different source

### Getting Help

- Check the [FAQ](faq.md)
- Search existing [issues](https://github.com/Sanjaya-Danushka/Aurora/issues)
- Ask questions in [discussions](https://github.com/Sanjaya-Danushka/Aurora/discussions)

## Best Practices

### Security
- Always review AUR packages before installation
- Keep your system updated
- Use official repositories when possible
- Be cautious with third-party plugins

### Performance
- Regularly clean package cache (`paccache -r`)
- Remove unused packages (`pacman -Qdtq | pacman -Rns -`)
- Use solid-state drives for better performance

### Maintenance
- Check for orphaned packages regularly
- Monitor disk usage
- Backup important configuration files

## Keyboard Shortcuts

- `Ctrl+F`: Focus search bar
- `Ctrl+R`: Refresh package list
- `Ctrl+I`: Install selected packages
- `Ctrl+U`: Update selected packages
- `F1`: Show help

## Next Steps

- Explore the [API documentation](../api/) for plugin development
- Check out [contributing guidelines](../CONTRIBUTING.md) to get involved
- Join the community discussions

Happy packaging! 📦
