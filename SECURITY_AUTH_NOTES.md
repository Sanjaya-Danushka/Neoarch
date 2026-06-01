# Authentication & Security - NeoArch Package Manager

## ✅ Fixed Security Issue

### Problem
The app was previously wrapping AUR commands with `pkexec`, which runs them as root. This is a **critical security vulnerability** because:
- AUR packages are community-maintained and untrusted
- Running AUR helpers as root bypasses security checks
- AUR helpers (yay, paru) are designed to run as normal user

### Solution
**File:** `services/install_service.py` (lines 124-131)

**Before (UNSAFE):**
```python
if source == 'AUR':
    cmd = ["pkexec"] + cmd  # ❌ Runs as root!
```

**After (SECURE):**
```python
if source == 'AUR':
    # AUR helpers MUST run as normal user for security
    # Setup askpass so the helper can authenticate internally
    if not env.get('SUDO_ASKPASS'):
        env, cleanup_path = app.prepare_askpass_env()
    # cmd runs WITHOUT pkexec wrapper ✅
```

## 🔐 Authentication Strategy

### 1. **Pacman (System Packages)** - Needs Root
```python
# Uses pkexec for GUI password dialog
exec_cmd = ["pkexec", "pacman", "-S", "package"]
```
- ✅ Runs with pkexec (polkit authentication)
- ✅ Shows GUI password dialog via polkit agent
- ✅ Properly authenticates as root

### 2. **AUR (Community Packages)** - Runs as User
```python
# AUR helper runs as normal user
exec_cmd = ["yay", "-S", "package"]  # No pkexec!
# Environment has SUDO_ASKPASS set for internal sudo calls
```
- ✅ Runs as normal user (never root)
- ✅ Helper internally uses sudo only when needed (e.g., `pacman -U`)
- ✅ Uses `--sudoflags -A` to use GUI askpass dialogs
- ✅ Respects AUR security model

### 3. **Flatpak** - User or System
```python
# User-scoped (no auth needed)
cmd = ["flatpak", "--user", "install", "app"]

# System-wide (needs auth)
cmd = ["flatpak", "install", "app"]  # Uses polkit internally
```

### 4. **npm** - User-scoped
```python
# Installs to ~/.npm-global (no root needed)
cmd = ["npm", "install", "-g", "package"]
```

## 🚫 Why NOT to Run App with Sudo

### ❌ Bad Idea:
```bash
sudo python aurora_home.py  # DON'T DO THIS!
```

### Problems:
1. **AUR will refuse to work** - Most AUR helpers detect root and exit
2. **Security risk** - Entire GUI runs as root
3. **File permissions** - Config files owned by root
4. **D-Bus issues** - GUI components may break
5. **No benefit** - pkexec/askpass work fine from normal user

## ✅ Correct Usage

### Run as Normal User:
```bash
python aurora_home.py  # Correct! ✅
```

### Authentication Flow:
1. App runs as normal user
2. When installing pacman packages → pkexec shows GUI password prompt
3. When installing AUR packages → runs as user, internally uses sudo with GUI askpass
4. Best of both worlds: security + convenience

## 📋 Required Tools

For GUI password prompts to work, install one of:
```bash
# KDE
sudo pacman -S ksshaskpass

# GNOME/GTK
sudo pacman -S seahorse

# Generic
sudo pacman -S x11-ssh-askpass

# Alternative
sudo pacman -S lxqt-openssh-askpass
```

For polkit (pkexec) GUI dialogs:
```bash
# KDE
sudo pacman -S polkit-kde-agent

# GNOME
sudo pacman -S polkit-gnome

# Already installed on most systems
```

## 🔧 How It Works

### Package Database Sync (Updates View)
```python
# Before checking updates, sync the database
env, _ = app.prepare_askpass_env()
subprocess.run(["sudo", "-A", "pacman", "-Sy", "--noconfirm"], env=env)
# Now check for updates
subprocess.run(["pacman", "-Qu"])
```
- Uses sudo with askpass for GUI password prompt
- Syncs database so updates are current
- No more stale update information

### AUR Helper Authentication
```python
# Setup askpass environment
env, _ = app.prepare_askpass_env()
env['SUDO_ASKPASS'] = "/path/to/askpass/script"

# Run AUR helper as normal user
subprocess.run(["yay", "-S", "package"], env=env)
# When yay needs sudo, it will:
# 1. Use SUDO_ASKPASS to show GUI dialog
# 2. Get password from user
# 3. Run pacman -U with that password
```

## 🎯 Summary

| Operation | User | Auth Method | Security |
|-----------|------|-------------|----------|
| Pacman Install | root | pkexec GUI | ✅ Secure |
| AUR Install | normal | askpass + internal sudo | ✅ Secure |
| Flatpak (user) | normal | none | ✅ Secure |
| Flatpak (system) | root | polkit | ✅ Secure |
| npm (user) | normal | none | ✅ Secure |
| DB Sync | root | sudo + askpass | ✅ Secure |

**Result:** Maximum security with good user experience! 🎉
