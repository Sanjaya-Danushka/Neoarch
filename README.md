# NeoArch - Package Manager for Arch Linux

NeoArch is a modern, user-friendly package manager designed specifically for Arch Linux. It provides an intuitive graphical interface for managing packages from multiple sources including pacman, AUR, Flatpak, and npm.

website: https://sanjaya-danushka.github.io/Neoarch/

preview: https://drive.google.com/file/d/17cfs7VEui4zfFhghsIWBp2duqpPjWtEQ/view?usp=sharing

<img width="1229" height="851" alt="Screenshot_20251111_185003" src="https://github.com/user-attachments/assets/1539d8eb-7d18-41e9-bc16-96ff061c1b4a" />




## Features

- **Multi-source package management**: Support for pacman, AUR, Flatpak, and npm packages
- **Graphical user interface**: Built with PyQt6 for a smooth desktop experience
- **Plugin system**: Extensible with plugins for additional tools and utilities
- **Bundle management**: Create and manage package bundles for easy deployment
- **Security-focused**: Requires appropriate privileges for package installation to maintain system security

## Installation

### From AUR (Recommended)

Install neoarch-git from the Arch User Repository using your preferred AUR helper:

```bash
yay -S neoarch-git  # or paru -S neoarch-git, etc.
```

### Prerequisites

- Python 3.8+
- PyQt6
- Arch Linux system
- Administrative privileges (sudo) for package management

### Install Dependencies

Option A — Recommended (Arch packages)

```bash
# Install system packages from official repos
sudo pacman -S --needed python python-pyqt6 python-requests qt6-svg git flatpak nodejs npm
```

Option B — Use a Python virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_pyqt.txt
```

Note: On Arch, using system `pip` often triggers the "externally-managed-environment" error. Prefer Option A (pacman) or install into a virtual environment (Option B). Alternatively, you can install apps with `pipx` (`sudo pacman -S python-pipx`) which manages a dedicated venv for each app.

### Run Aurora

```bash
# If you created a virtual environment
source .venv/bin/activate  # skip if not using a venv

python aurora_home.py
```

## Security Notice

As a package manager, Aurora requires administrative privileges to install, update, and remove system packages. This is essential for maintaining system security and integrity. The application will prompt for authentication when performing privileged operations.

## Security

If you discover any security vulnerabilities or have concerns about the security of NeoArch, please report them immediately to our security team at **dsanjaya712@gmail.com**. We take security seriously and will respond promptly to address any issues.

## Usage

1. **Discover Packages**: Search and browse available packages from multiple repositories
2. **Install Packages**: Select and install packages with a single click
3. **Manage Updates**: View and install available system updates
4. **Plugins**: Access additional tools and utilities through the plugin system
5. **Bundles**: Create package bundles for consistent deployments

## Contributing

We welcome contributions from the community! NeoArch aims to provide a secure, user-friendly package management experience for Arch Linux users.

### Our Purpose & Standards

**Purpose**: To create a modern, intuitive package manager that simplifies Arch Linux package management while maintaining the highest security standards.

**Standards**:
- **Security First**: All code must undergo security review. No compromises on system security.
- **Code Quality**: Follow PEP 8 style guidelines, add comprehensive tests, and maintain clean, readable code.
- **User Experience**: Prioritize intuitive UI/UX design and responsive performance.
- **Compatibility**: Ensure compatibility with latest Arch Linux standards and dependencies.
- **Documentation**: All features must be properly documented.

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup

```bash
git clone https://github.com/Sanjaya-Danushka/Neoarch.git
cd Neoarch
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_pyqt.txt
python aurora_home.py
```

### Guidelines

- Write clear, concise commit messages
- Add tests for new features
- Update documentation as needed
- Follow the existing code style
- Ensure all tests pass before submitting PR

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


<a href="https://www.buymeacoffee.com/sanjayadanushka" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
