# Troubleshooting Guide

## Installation Issues

### PyQt6 Installation Fails

**Error:** `ModuleNotFoundError: No module named 'PyQt6'`

**Solutions:**
```bash
# Install PyQt6 from system packages
sudo pacman -S python-pyqt6

# Then install other dependencies
pip install -r requirements_pyqt.txt

# Or upgrade existing installation
pip install --upgrade PyQt6
```

### Permission Denied During Installation

**Error:** `Permission denied: '/usr/local/lib/...'`

**Solutions:**
```bash
# Option 1: Use user installation
pip install --user -r requirements_pyqt.txt

# Option 2: Use virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_pyqt.txt

# Option 3: Use sudo (not recommended)
sudo pip install -r requirements_pyqt.txt
```

### Git Clone Fails

**Error:** `fatal: unable to access 'https://github.com/...'`

**Solutions:**
```bash
# Check internet connection
ping github.com

# Try SSH instead of HTTPS
git clone git@github.com:Sanjaya-Danushka/Neoarch.git

# Update git
sudo pacman -S git

# Clear git cache
git config --global --unset http.proxy
```

## Startup Issues

### NeoArch Won't Start

**Error:** Application crashes or doesn't launch

**Debug Steps:**
```bash
# Run with verbose output
python aurora_home.py --verbose

# Check Python version
python --version  # Should be 3.8+

# Check for missing dependencies
python -c "import PyQt6; print('PyQt6 OK')"
python -c "import requests; print('requests OK')"

# View error logs
journalctl -xe
```

### Module Not Found Error

**Error:** `ModuleNotFoundError: No module named 'X'`

**Solution:**
```bash
# Reinstall all dependencies
pip install --upgrade -r requirements_pyqt.txt

# Or install specific module
pip install PyQt6 requests psutil
```

### Display Server Issues

**Error:** `Could not connect to display` or `No display found`

**Solutions:**
```bash
# Ensure X11 or Wayland is running
echo $DISPLAY  # Should show :0 or similar

# For Wayland
export QT_QPA_PLATFORM=wayland

# For X11
export QT_QPA_PLATFORM=xcb

# Run NeoArch
python aurora_home.py
```

## Authentication Issues

### "Authentication Failed" Error

**Error:** Cannot install/update packages due to auth failure

**Solutions:**
```bash
# Check sudo privileges
sudo -l

# Ensure polkit is installed
sudo pacman -S polkit

# Try running with pkexec
pkexec python aurora_home.py

# Check sudoers configuration
sudo visudo  # Verify your user is listed
```

### Password Prompt Doesn't Appear

**Error:** Installation hangs or fails silently

**Solutions:**
```bash
# Ensure polkit is running
systemctl status polkit

# Restart polkit
sudo systemctl restart polkit

# Try running with sudo directly
sudo python aurora_home.py
```

## Package Management Issues

### Package Installation Fails

**Error:** `Error: failed to prepare transaction`

**Solutions:**
```bash
# Update package databases
sudo pacman -Sy

# Check for disk space
df -h

# Check for conflicting packages
pacman -Qi package-name

# Try installing from different source
# (e.g., AUR instead of Pacman)

# Check system logs
journalctl -xe
```

### Package Not Found

**Error:** `error: target not found: package-name`

**Solutions:**
```bash
# Refresh package databases
sudo pacman -Sy

# Search for package
pacman -Ss package-name

# Check package name spelling
# Try partial name: pacman -Ss partial-name

# Package might be in AUR
# Try searching in AUR directly
```

### Update Fails

**Error:** `error: failed to commit transaction`

**Solutions:**
```bash
# Check for held packages
pacman -Q | grep hold

# Remove package holds
sudo pacman -S --needed package-name

# Check for conflicting packages
pacman -Qi conflicting-package

# Try partial update
sudo pacman -Su --ignore package-name

# Check disk space
df -h
```

### Dependency Resolution Issues

**Error:** `error: unable to satisfy dependencies`

**Solutions:**
```bash
# Check available versions
pacman -Ss package-name

# Install dependencies manually
sudo pacman -S dependency1 dependency2

# Use AUR helper for complex dependencies
yay -S package-name

# Check for conflicting packages
pacman -Qi conflicting-package
```

## Search & Discovery Issues

### Search Results Empty

**Error:** No packages found when searching

**Solutions:**
```bash
# Refresh package databases
# Click refresh button in NeoArch

# Check internet connection
ping archlinux.org

# Try exact package name
# Instead of: "web browser"
# Try: "firefox"

# Check if package exists
pacman -Ss firefox

# Enable all package sources
# Go to Settings → Sources
```

### Search is Slow

**Error:** Search takes too long to complete

**Solutions:**
```bash
# Use more specific search terms
# Instead of: "a"
# Try: "apache"

# Filter by package source
# Disable unused sources

# Clear package cache
rm -rf ~/.cache/neoarch/

# Restart NeoArch
```

### Duplicate Results

**Error:** Same package appears multiple times

**Solutions:**
```bash
# This is normal - same package from different sources

# To avoid duplicates:
# Go to Settings → Sources
# Disable duplicate sources

# Or use filters to show only one source
```

## UI & Display Issues

### UI Looks Broken

**Error:** Buttons misaligned, text cut off, pixelated

**Solutions:**
```bash
# Update PyQt6
pip install --upgrade PyQt6

# Check display scaling
# Settings → Display → Scaling

# Try different theme
# Settings → Appearance → Theme

# Restart NeoArch
```

### Window Won't Resize

**Error:** Window stuck at fixed size

**Solutions:**
```bash
# Reset window geometry
rm ~/.config/neoarch/geometry.conf

# Restart NeoArch

# Try maximizing window
# Double-click title bar
```

### High DPI Display Issues

**Error:** Everything too small or too large

**Solutions:**
```bash
# Set DPI scaling
export QT_AUTO_SCREEN_SCALE_FACTOR=1

# Or set specific scale
export QT_SCALE_FACTOR=1.5

# Run NeoArch
python aurora_home.py
```

## Performance Issues

### High CPU Usage

**Error:** NeoArch uses too much CPU

**Solutions:**
```bash
# Close other applications

# Disable auto-refresh
# Settings → General → Auto-refresh

# Reduce search frequency
# Settings → Search → Debounce time

# Check for background processes
top  # Press 'q' to quit
```

### High Memory Usage

**Error:** NeoArch uses too much RAM

**Solutions:**
```bash
# Close unused tabs

# Clear cache
rm -rf ~/.cache/neoarch/

# Restart NeoArch

# Check for memory leaks
# Monitor with: watch free -h
```

### Slow Package Loading

**Error:** Takes long to load package list

**Solutions:**
```bash
# Reduce number of sources
# Settings → Sources → Disable unused

# Clear cache
rm -rf ~/.cache/neoarch/

# Update package databases
sudo pacman -Sy

# Check internet speed
speedtest-cli
```

## System Integration Issues

### NeoArch Doesn't Appear in Application Menu

**Error:** Can't find NeoArch in application launcher

**Solutions:**
```bash
# If installed from AUR, it should appear automatically
# Try refreshing application menu

# Or run manually
python aurora_home.py

# Create desktop shortcut
# ~/.local/share/applications/neoarch.desktop
```

### Keyboard Shortcuts Don't Work

**Error:** Ctrl+F, Ctrl+R, etc. don't work

**Solutions:**
```bash
# Check if shortcuts are enabled
# Settings → Keyboard → Enable shortcuts

# Try different key combinations
# Settings → Keyboard → Customize

# Check for conflicting shortcuts
# System Settings → Keyboard Shortcuts
```

## Getting More Help

### Enable Debug Logging

```bash
# Run with debug output
python aurora_home.py --debug

# Or set environment variable
DEBUG=1 python aurora_home.py

# Check logs
journalctl -xe
tail -f ~/.local/share/neoarch/logs/neoarch.log
```

### Collect System Information

```bash
# For bug reports, collect:
uname -a                    # System info
python --version            # Python version
pacman -Q | grep pyqt       # PyQt version
pacman -Q neoarch-git       # NeoArch version (if from AUR)
```

### Report Issues

1. Check [FAQ](FAQ.md)
2. Search [GitHub Issues](https://github.com/Sanjaya-Danushka/Neoarch/issues)
3. Create new issue with:
   - Error message
   - Steps to reproduce
   - System information
   - Debug output

---

**Still stuck?** Ask in [GitHub Discussions](https://github.com/Sanjaya-Danushka/Neoarch/discussions)
