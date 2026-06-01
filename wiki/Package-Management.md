# Package Management

Complete guide to managing packages with NeoArch.

## Overview

NeoArch provides a unified interface for managing packages from multiple sources:
- **Pacman** - Official Arch repositories
- **AUR** - Arch User Repository
- **Flatpak** - Universal packages
- **npm** - JavaScript packages

## Searching Packages

### Basic Search

1. Click the **Discover** tab
2. Type in the search bar
3. Results appear instantly

### Search Operators

| Operator | Example | Result |
|----------|---------|--------|
| Name | `firefox` | Packages named firefox |
| Description | `web browser` | Packages with description |
| Partial | `fire` | Packages containing "fire" |
| Exact | `"firefox"` | Exact match only |

### Advanced Filtering

**By Source:**
- Pacman only
- AUR only
- Flatpak only
- npm only

**By Status:**
- Installed
- Not installed
- Upgradeable
- All

**By Category:**
- System
- Development
- Multimedia
- Internet
- Utilities

## Installation

### Single Package Installation

1. Search for package
2. Click **Install** button
3. Enter password
4. Wait for completion

### Batch Installation

1. Select multiple packages (checkboxes)
2. Click **Install Selected**
3. Authenticate
4. Wait for all installations

### Installation from Different Sources

**From Pacman:**
```
Search → Select Pacman source → Install
```

**From AUR:**
```
Search → Select AUR source → Install
```

**From Flatpak:**
```
Search → Select Flatpak source → Install
```

**From npm:**
```
Search → Select npm source → Install
```

## Updates

### Check for Updates

1. Click **Updates** tab
2. View available updates
3. Review changelog (if available)

### Update Strategies

**Update All:**
- Click **Update All**
- Fastest method
- Updates all packages

**Selective Update:**
- Select specific packages
- Click **Update Selected**
- More control

**Skip Updates:**
- Right-click package
- Select **Skip Update**
- Useful for problematic packages

### Automatic Updates

**Enable Auto-Update:**
1. Go to **Settings**
2. Select **Auto Updates**
3. Set check frequency
4. Choose update behavior

**Update Frequency Options:**
- Daily
- Weekly
- Monthly
- Manual only

## Removal

### Uninstall Package

1. Click **Installed** tab
2. Search for package
3. Click **Uninstall**
4. Confirm removal

### Removal Options

**Remove Package Only:**
- Removes application
- Keeps configuration files

**Remove with Dependencies:**
- Removes package and unused dependencies
- Cleans up system

**Remove Configuration:**
- Removes all traces
- Useful for clean reinstall

### Batch Removal

1. Select multiple packages
2. Click **Uninstall Selected**
3. Confirm
4. Wait for removal

## Package Information

### View Package Details

Click on package to see:
- **Name** - Package identifier
- **Version** - Current version
- **Size** - Installation size
- **Description** - What it does
- **Dependencies** - Required packages
- **Conflicts** - Incompatible packages
- **Maintainer** - Package maintainer
- **URL** - Project website
- **License** - License type

### Check Installation Status

- **Installed** - Package is installed
- **Not Installed** - Available but not installed
- **Upgradeable** - Update available
- **Broken** - Installation issues

## Dependency Management

### Automatic Dependency Resolution

NeoArch automatically handles:
- Installing required dependencies
- Resolving version conflicts
- Checking for incompatibilities

### Manual Dependency Management

**Install Dependencies:**
```
Right-click package → Install Dependencies
```

**View Dependencies:**
```
Click package → View Dependencies
```

**Check Conflicts:**
```
Click package → Check Conflicts
```

## Cache Management

### Clear Package Cache

**Via NeoArch:**
1. Go to **Settings**
2. Select **Cache**
3. Click **Clear Cache**

**Via Terminal:**
```bash
# Clear all cache
paccache -r

# Keep last 3 versions
paccache -rk3

# Dry run (show what would be deleted)
paccache -rk3 --dryrun
```

### Manage Downloaded Packages

**Location:** `/var/cache/pacman/pkg/`

**Clean up:**
```bash
# Remove old packages
sudo pacman -Sc

# Remove all cached packages
sudo pacman -Scc
```

## Orphaned Packages

### Find Orphaned Packages

```bash
# List orphaned packages
pacman -Qdtq

# Or in NeoArch:
# Settings → Maintenance → Find Orphans
```

### Remove Orphaned Packages

```bash
# Remove all orphans
pacman -Qdtq | pacman -Rns -

# Or in NeoArch:
# Settings → Maintenance → Remove Orphans
```

## AUR-Specific Features

### AUR Helper Support

NeoArch supports:
- **yay** - Feature-rich AUR helper
- **paru** - Rust-based AUR helper
- **pikaur** - Minimalist AUR helper

**Configure AUR Helper:**
1. Go to **Settings**
2. Select **AUR**
3. Choose preferred helper

### Review AUR Packages

Before installing AUR packages:

1. **Check PKGBUILD:**
   - Review build script
   - Check for suspicious commands
   - Verify dependencies

2. **Read Comments:**
   - Check for reported issues
   - Look for solutions
   - Verify maintainer reputation

3. **Test Installation:**
   - Use virtual machine first
   - Check for conflicts
   - Verify functionality

## Flatpak Management

### Flatpak Remotes

**Add Remote:**
```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

**List Remotes:**
```bash
flatpak remotes
```

### Flatpak Permissions

**View Permissions:**
```
Right-click Flatpak → Permissions
```

**Manage Permissions:**
- File system access
- Network access
- Device access
- System access

## npm Package Management

### Global vs Local Installation

**Global (System-wide):**
```bash
npm install -g package-name
```

**Local (Project):**
```bash
npm install package-name
```

### npm Configuration

**In NeoArch:**
1. Go to **Settings**
2. Select **npm**
3. Configure preferences

## Troubleshooting

### Installation Issues

**Problem:** Installation fails
**Solution:** See [Troubleshooting](Troubleshooting.md)

**Problem:** Dependency conflicts
**Solution:** Check package conflicts, try different source

**Problem:** Insufficient disk space
**Solution:** Clean cache, remove old packages

### Update Issues

**Problem:** Update fails
**Solution:** Check system logs, verify disk space

**Problem:** Broken packages
**Solution:** Reinstall package, check dependencies

### Removal Issues

**Problem:** Can't remove package
**Solution:** Check for dependent packages, force removal

---

**Need help?** Check [FAQ](FAQ.md) or [Troubleshooting](Troubleshooting.md)
