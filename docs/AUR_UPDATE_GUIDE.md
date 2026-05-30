# AUR Package Update Guide for v1.2-beta

## SSH Public Key
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBqV2VqUECfS/YcNGrTVONmo1hG9vvKYza/liWdYPwQ1
```

## Steps to Update AUR Package

### 1. Clone AUR Repository
```bash
git clone ssh://aur@aur.archlinux.org/neoarch-git.git
cd neoarch-git
```

### 2. Update PKGBUILD
Edit `PKGBUILD` file:

```bash
# Update version
pkgver=1.2.beta

# Update pkgrel if needed
pkgrel=1

# Update source to latest commit
source=("git+https://github.com/Sanjaya-Danushka/Neoarch.git#tag=v1.2-beta")

# Update checksums
sha256sums=('SKIP')  # For git sources
```

### 3. Update .SRCINFO
Generate new `.SRCINFO`:
```bash
makepkg --printsrcinfo > .SRCINFO
```

### 4. Commit and Push Changes
```bash
git add PKGBUILD .SRCINFO
git commit -m "Update to v1.2-beta: 80 code quality fixes, security hardening, performance optimizations"
git push
```

## Sample PKGBUILD for v1.2-beta

```bash
# Maintainer: Sanjaya Danushka <dsanjaya712@gmail.com>
pkgname=neoarch-git
pkgver=1.2.beta
pkgrel=1
pkgdesc="A beautiful, unified GUI package manager for Arch Linux"
arch=('x86_64')
url="https://github.com/Sanjaya-Danushka/Neoarch"
license=('MIT')
depends=('python' 'python-pyqt6' 'python-requests' 'qt6-svg' 'flatpak' 'nodejs' 'npm')
makedepends=('git')
source=("git+https://github.com/Sanjaya-Danushka/Neoarch.git#tag=v1.2-beta")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/Neoarch"
  git describe --long --tags | sed 's/^v//;s/\([^-]*-g\)/r\1/;s/-/./g'
}

package() {
  cd "$srcdir/Neoarch"
  
  # Install main application
  install -Dm755 aurora_home.py "$pkgdir/usr/bin/neoarch"
  
  # Install components
  install -d "$pkgdir/opt/neoarch"
  cp -r components managers services utils assets "$pkgdir/opt/neoarch/"
  
  # Install license
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  
  # Install desktop entry
  install -Dm644 neoarch.desktop "$pkgdir/usr/share/applications/neoarch.desktop"
}
```

## Release Notes for AUR

```
v1.2-beta Release:

Code Quality Improvements (80 fixes):
- Security vulnerabilities eliminated (3 BAN-B607)
- Protected member access resolved (15 PYL-W0212)
- Attributes properly initialized (13 PYL-W0201)
- Unused imports cleaned (12 PY-W2000)
- Static methods identified (7 PYL-R0201)
- Undefined variables fixed (11 PYL-E0602)
- Exception handling improved (5 FLK-E722)
- Code quality optimizations (12 additional)

Performance Optimizations:
- Lazy loading: 4 cards per batch
- Deferred loading: 100ms timer batching
- Caching: 30-second TTL for system data
- Smooth scrolling: 137 plugin cards
- No UI blocking: Responsive performance

Security Enhancements:
- Full absolute paths for subprocess calls
- Explicit subprocess behavior (check=False)
- Proper exception handling
- Protected member access eliminated
- Secure encapsulation patterns

Features:
- 137 plugin cards (pacman, AUR, Flatpak, npm)
- Popular apps slider with shuffle
- Advanced filtering (status + source)
- System health monitoring
- Recent updates display
- Community bundle management
- Git integration
```

## SSH Key Configuration

Add your SSH public key to AUR account:
1. Go to: https://aur.archlinux.org/account/
2. Login to your AUR account
3. Add SSH public key:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBqV2VqUECfS/YcNGrTVONmo1hG9vvKYza/liWdYPwQ1
```
4. Save changes

## Verify SSH Connection
```bash
ssh -T aur@aur.archlinux.org
```

Should output:
```
Hi Sanjaya-Danushka, you successfully authenticated, but AUR does not provide shell access.
```

## Testing Before Push
```bash
# Build locally
makepkg -si

# Test installation
neoarch

# Verify version
neoarch --version  # if supported
```

## Troubleshooting

### Permission Denied
- Verify SSH key is added to AUR account
- Check SSH config: `cat ~/.ssh/config`
- Test connection: `ssh -T aur@aur.archlinux.org`

### Checksum Mismatch
- Regenerate .SRCINFO: `makepkg --printsrcinfo > .SRCINFO`
- Ensure source URL is correct

### Build Fails
- Check dependencies in PKGBUILD
- Verify Python version compatibility
- Test build locally first

## After Push

Your AUR package will be available at:
```
https://aur.archlinux.org/packages/neoarch-git
```

Users can install with:
```bash
yay -S neoarch-git
# or
paru -S neoarch-git
```

## Maintenance

Keep AUR package updated with each release:
1. Update PKGBUILD with new version
2. Regenerate .SRCINFO
3. Commit and push
4. Announce on forums/social media

---

**SSH Public Key**: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBqV2VqUECfS/YcNGrTVONmo1hG9vvKYza/liWdYPwQ1
