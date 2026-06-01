# Installation Guide

## Quick Install (Recommended)

### From AUR using yay
```bash
yay -S neoarch-git
```

### From AUR using paru
```bash
paru -S neoarch-git
```

## Manual Installation

### Prerequisites

- **Python 3.8+**
- **PyQt6**
- **Arch Linux** system
- **Administrative privileges** (sudo) for package management

### Step 1: Install System Dependencies

```bash
# Install required packages from official repositories
sudo pacman -S --needed python python-pyqt6 python-requests qt6-svg git flatpak nodejs npm
```

### Step 2: Clone the Repository

```bash
git clone https://github.com/Sanjaya-Danushka/Neoarch.git
cd Neoarch
```

### Step 3: Install Python Dependencies

```bash
# Option A: Using pip (recommended)
pip install -r requirements_pyqt.txt

# Option B: Using virtual environment (isolated)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_pyqt.txt
```

### Step 4: Run NeoArch

```bash
python aurora_home.py
```

## Installation from Source

### Build and Install Locally

```bash
# Clone the repository
git clone https://github.com/Sanjaya-Danushka/Neoarch.git
cd Neoarch

# Install to system
sudo python setup.py install

# Or use pip
sudo pip install .
```

## Troubleshooting Installation

### Issue: PyQt6 Installation Fails

**Solution:**
```bash
# Install PyQt6 system-wide first
sudo pacman -S python-pyqt6

# Then install other dependencies
pip install -r requirements_pyqt.txt
```

### Issue: Permission Denied

**Solution:**
```bash
# Use sudo for system-wide installation
sudo pip install -r requirements_pyqt.txt

# Or use user installation
pip install --user -r requirements_pyqt.txt
```

### Issue: Module Not Found

**Solution:**
```bash
# Ensure all dependencies are installed
pip install --upgrade -r requirements_pyqt.txt

# Check Python version
python --version  # Should be 3.8+
```

## Uninstallation

### If installed from AUR
```bash
yay -R neoarch-git
```

### If installed from source
```bash
pip uninstall neoarch
# or
sudo pip uninstall neoarch
```

## Next Steps

- Read the [Quick Start Guide](Quick-Start.md)
- Check the [User Guide](User-Guide.md)
- Explore [Package Management](Package-Management.md)

---

**Need help?** Check the [FAQ](FAQ.md) or [Troubleshooting](Troubleshooting.md) page.
