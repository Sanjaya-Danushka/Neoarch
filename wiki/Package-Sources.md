# Package Sources

Learn about the different package sources supported by NeoArch.

## Overview

NeoArch supports four major package sources:

| Source | Type | Stability | Use Case |
|--------|------|-----------|----------|
| **Pacman** | Official | Very Stable | System packages |
| **AUR** | Community | Variable | Latest versions |
| **Flatpak** | Universal | Good | Cross-distro apps |
| **npm** | JavaScript | Varies | Dev tools |

## Pacman (Official Repositories)

### What is Pacman?

Pacman is the official package manager for Arch Linux. It manages packages from the official Arch repositories.

### Repositories

**core** - Essential packages for Arch Linux
**extra** - Additional community-supported packages
**community** - User-maintained packages
**multilib** - 32-bit libraries for 64-bit systems

### Advantages

✅ **Stable** - Well-tested, production-ready  
✅ **Secure** - Signed packages, verified sources  
✅ **Fast** - Optimized for Arch systems  
✅ **Reliable** - Official support and updates  

### Disadvantages

❌ **Limited** - Fewer packages than AUR  
❌ **Outdated** - Sometimes behind latest versions  
❌ **Conservative** - Prioritizes stability over features  

### Installation

```bash
# Via NeoArch
# Discover → Search → Select Pacman source → Install

# Via Terminal
sudo pacman -S package-name
```

### Best For

- System packages
- Core applications
- Stable software
- Production systems

---

## AUR (Arch User Repository)

### What is AUR?

The Arch User Repository is a community-driven repository containing user-submitted packages.

### How It Works

1. User submits PKGBUILD script
2. Community reviews and votes
3. Popular packages move to official repos
4. Packages are built from source

### Advantages

✅ **Comprehensive** - Thousands of packages  
✅ **Latest** - Cutting-edge software versions  
✅ **Flexible** - Custom build options  
✅ **Community** - Active user support  

### Disadvantages

❌ **Unstable** - Variable quality  
❌ **Requires Review** - Security concerns  
❌ **Build Time** - Compiled from source  
❌ **Dependencies** - Complex dependency chains  

### AUR Helpers

NeoArch supports popular AUR helpers:

**yay** - Feature-rich, written in Go
```bash
yay -S package-name
```

**paru** - Rust-based, fast and modern
```bash
paru -S package-name
```

**pikaur** - Minimalist, simple interface
```bash
pikaur -S package-name
```

### Safety Tips

⚠️ **Always Review PKGBUILD**
```bash
# View PKGBUILD before installation
cat PKGBUILD
```

⚠️ **Check Comments**
- Look for reported issues
- Verify maintainer reputation
- Check installation success rate

⚠️ **Test First**
- Use virtual machine
- Check for conflicts
- Verify functionality

⚠️ **Trusted Maintainers**
- Check maintainer history
- Look for package votes
- Verify package popularity

### Installation

```bash
# Via NeoArch
# Discover → Search → Select AUR source → Install

# Via Terminal with yay
yay -S package-name

# Via Terminal with paru
paru -S package-name
```

### Best For

- Latest software versions
- Niche applications
- Development tools
- Cutting-edge features

---

## Flatpak

### What is Flatpak?

Flatpak is a universal package format that works across Linux distributions.

### Advantages

✅ **Universal** - Works on any Linux distro  
✅ **Sandboxed** - Isolated, secure applications  
✅ **Easy Updates** - Automatic updates  
✅ **Consistent** - Same on all systems  

### Disadvantages

❌ **Larger** - Bigger download/install size  
❌ **Slower** - Slight performance overhead  
❌ **Limited** - Fewer packages than Pacman/AUR  
❌ **Permissions** - Requires permission management  

### Remotes

**Flathub** - Main Flatpak repository
```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

### Permissions

Flatpak apps run in sandbox with limited permissions:

- **File System** - Access to specific directories
- **Network** - Internet access
- **Devices** - Hardware access
- **System** - System resource access

### Installation

```bash
# Via NeoArch
# Discover → Search → Select Flatpak source → Install

# Via Terminal
flatpak install flathub package-name
```

### Best For

- Proprietary software
- Cross-distro applications
- Isolated environments
- Easy updates

---

## npm (Node Package Manager)

### What is npm?

npm is the package manager for JavaScript/Node.js packages.

### Advantages

✅ **Comprehensive** - Millions of packages  
✅ **Latest** - Frequent updates  
✅ **Flexible** - Version management  
✅ **Development** - Perfect for developers  

### Disadvantages

❌ **Quality** - Highly variable  
❌ **Security** - Requires careful review  
❌ **Dependencies** - Complex dependency trees  
❌ **System** - Not ideal for system packages  

### Installation Types

**Global (System-wide):**
```bash
npm install -g package-name
```

**Local (Project):**
```bash
npm install package-name
```

### Package.json

Manage dependencies in `package.json`:

```json
{
  "name": "my-project",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.17.1",
    "lodash": "^4.17.21"
  }
}
```

### Installation

```bash
# Via NeoArch
# Discover → Search → Select npm source → Install

# Via Terminal
npm install package-name

# Global installation
npm install -g package-name
```

### Best For

- JavaScript packages
- Development tools
- Node.js applications
- Web development

---

## Comparison

### Feature Comparison

| Feature | Pacman | AUR | Flatpak | npm |
|---------|--------|-----|---------|-----|
| Stability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Package Count | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Latest Versions | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Security | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

### Use Case Recommendations

**Use Pacman for:**
- System packages
- Core applications
- Stable software
- Production systems

**Use AUR for:**
- Latest versions
- Niche applications
- Development tools
- Cutting-edge features

**Use Flatpak for:**
- Proprietary software
- Cross-distro apps
- Isolated environments
- Easy updates

**Use npm for:**
- JavaScript packages
- Development tools
- Node.js apps
- Web development

---

## Managing Sources

### Enable/Disable Sources

**In NeoArch:**
1. Go to **Settings**
2. Select **Sources**
3. Toggle sources on/off

### Set Default Source

**In NeoArch:**
1. Go to **Settings**
2. Select **Sources**
3. Choose default source

### Configure AUR Helper

**In NeoArch:**
1. Go to **Settings**
2. Select **AUR**
3. Choose helper (yay, paru, etc.)

---

## Best Practices

### Security

🔒 **Pacman:**
- Trust official repositories
- Keep system updated
- Verify signatures

🔒 **AUR:**
- Review PKGBUILD scripts
- Check maintainer reputation
- Test in VM first

🔒 **Flatpak:**
- Review permissions
- Use trusted remotes
- Monitor updates

🔒 **npm:**
- Check package reputation
- Review dependencies
- Use lock files

### Performance

⚡ **Optimize:**
- Use Pacman for system packages
- Limit AUR packages
- Clean cache regularly
- Remove unused packages

---

**Need help?** Check [FAQ](FAQ.md) or [Troubleshooting](Troubleshooting.md)
