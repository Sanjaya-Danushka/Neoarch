# Frequently Asked Questions (FAQ)

## General Questions

### What is NeoArch?
NeoArch is a modern, user-friendly GUI package manager for Arch Linux. It provides a unified interface to manage packages from multiple sources: Pacman (official), AUR (community), Flatpak (universal), and npm (JavaScript).

### Why should I use NeoArch instead of the terminal?
- **Visual Interface**: Easier to browse and discover packages
- **Multi-Source**: Manage all package types in one place
- **Beginner-Friendly**: No need to memorize commands
- **Powerful**: Still supports advanced features
- **Beautiful**: Modern, intuitive design

### Is NeoArch safe to use?
Yes! NeoArch is designed with security in mind:
- Requires authentication for system operations
- Respects system permissions
- Doesn't bypass security mechanisms
- Always review AUR packages before installation

### Can I use NeoArch on non-Arch systems?
NeoArch is specifically designed for Arch Linux. It may work on Arch-based distributions (Manjaro, EndeavourOS, etc.) but is not officially supported.

## Installation & Setup

### How do I install NeoArch?
The easiest way is from AUR:
```bash
yay -S neoarch-git
```
See [Installation Guide](Installation.md) for other methods.

### What are the system requirements?
- Python 3.8+
- PyQt6
- Arch Linux
- Internet connection
- Administrative privileges (sudo)

### Do I need to install all dependencies manually?
No! The AUR package handles dependencies automatically. If installing from source, use:
```bash
pip install -r requirements_pyqt.txt
```

### Can I run NeoArch without sudo?
NeoArch requires sudo for package operations (install, update, remove). You can browse packages without sudo, but can't perform actions.

## Usage Questions

### How do I search for packages?
1. Click the **Discover** tab
2. Type in the search bar
3. Results appear instantly from all sources

### What's the difference between Pacman, AUR, Flatpak, and npm?
- **Pacman**: Official Arch packages (stable, well-tested)
- **AUR**: Community packages (latest versions, more variety)
- **Flatpak**: Universal packages (work across distros, sandboxed)
- **npm**: JavaScript packages (dev tools, libraries)

See [Package Sources](Package-Sources.md) for details.

### How do I install a package?
1. Search for the package
2. Click the **Install** button
3. Enter your password when prompted
4. Wait for installation to complete

### Can I install multiple packages at once?
Yes! Select multiple packages and click **Install All** or **Update All**.

### How do I update my system?
1. Click the **Updates** tab
2. Review available updates
3. Click **Update All** or select specific packages
4. Enter password and wait

### How do I uninstall a package?
1. Click the **Installed** tab
2. Find the package
3. Click **Uninstall**
4. Confirm removal

### What are Bundles?
Bundles are collections of packages you can save and install together. Useful for:
- Setting up development environments
- Sharing configurations
- Quick system setup

See [Bundles](Bundles.md) for details.

## Troubleshooting

### NeoArch won't start
**Solution:**
```bash
# Check Python version
python --version  # Should be 3.8+

# Reinstall dependencies
pip install --upgrade -r requirements_pyqt.txt

# Run with verbose output
python aurora_home.py --verbose
```

### Authentication fails
**Solution:**
- Ensure you have sudo privileges
- Check that polkit is installed: `sudo pacman -S polkit`
- Try running with pkexec: `pkexec python aurora_home.py`

### Package installation fails
**Solution:**
- Check internet connection
- Verify package exists: `pacman -Ss package-name`
- Check system logs: `journalctl -xe`
- Try installing from different source

### Search results are empty
**Solution:**
- Refresh package databases: Click refresh button
- Check internet connection
- Try different search terms
- Ensure package exists

### UI looks broken or pixelated
**Solution:**
- Update PyQt6: `pip install --upgrade PyQt6`
- Check display scaling settings
- Try restarting NeoArch

## Performance

### Why is the first search slow?
The first search loads package databases from all sources. Subsequent searches are faster as data is cached.

### How can I speed up NeoArch?
- Use filters to narrow results
- Search by exact package name
- Disable unused package sources
- Close other applications

### Does NeoArch use a lot of resources?
NeoArch is lightweight:
- ~100MB RAM during normal use
- Minimal CPU usage
- Efficient caching system

## Plugins

### What are plugins?
Plugins extend NeoArch's functionality with additional tools and features.

### How do I install plugins?
1. Click the **Plugins** tab
2. Browse available plugins
3. Click **Install**
4. Restart NeoArch

### Can I create custom plugins?
Yes! See [Plugin Development](Plugin-Development.md) for details.

## Advanced Questions

### Can I use NeoArch with custom AUR helpers?
NeoArch auto-detects AUR helpers (yay, paru, etc.). Make sure your helper is installed and in PATH.

### How do I contribute to NeoArch?
See [Contributing](Contributing.md) for guidelines on:
- Reporting bugs
- Suggesting features
- Submitting code
- Improving documentation

### Where can I find the source code?
GitHub: https://github.com/Sanjaya-Danushka/Neoarch

### Is there a command-line version?
NeoArch is GUI-focused, but you can use Arch's built-in tools:
- `pacman` - Official packages
- `yay` or `paru` - AUR packages
- `flatpak` - Flatpak packages
- `npm` - JavaScript packages

## Getting Help

### I found a bug, what should I do?
1. Check [Troubleshooting](Troubleshooting.md)
2. Search existing [GitHub Issues](https://github.com/Sanjaya-Danushka/Neoarch/issues)
3. Create a new issue with:
   - Error message
   - Steps to reproduce
   - System information

### Where can I ask questions?
- [GitHub Discussions](https://github.com/Sanjaya-Danushka/Neoarch/discussions)
- [GitHub Issues](https://github.com/Sanjaya-Danushka/Neoarch/issues)

### How do I report security issues?
See [Security Policy](https://github.com/Sanjaya-Danushka/Neoarch/security/policy)

---

**Still have questions?** Check [Troubleshooting](Troubleshooting.md) or ask in [GitHub Discussions](https://github.com/Sanjaya-Danushka/Neoarch/discussions)
