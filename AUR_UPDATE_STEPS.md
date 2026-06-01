# AUR Package Update Steps for v1.2-beta

## Current Status
- Last Updated: 2025-11-12 08:09 (UTC)
- Current Version: Needs update to v1.2-beta
- SSH Key: ✅ Added to AUR account

## Step-by-Step Update Process

### Step 1: Clone AUR Repository
```bash
git clone ssh://aur@aur.archlinux.org/neoarch-git.git
cd neoarch-git
```

### Step 2: Check Current PKGBUILD
```bash
cat PKGBUILD
```

You should see something like:
```bash
pkgname=neoarch-git
pkgver=1.1.beta  # OLD VERSION
pkgrel=1
```

### Step 3: Edit PKGBUILD
```bash
nano PKGBUILD
# or
vim PKGBUILD
```

**Update these lines:**

**OLD:**
```bash
pkgver=1.1.beta
source=("git+https://github.com/Sanjaya-Danushka/Neoarch.git#tag=v1.1-beta")
```

**NEW:**
```bash
pkgver=1.2.beta
source=("git+https://github.com/Sanjaya-Danushka/Neoarch.git#tag=v1.2-beta")
```

### Step 4: Generate New .SRCINFO
```bash
makepkg --printsrcinfo > .SRCINFO
```

This will update checksums and metadata.

### Step 5: Verify Changes
```bash
git diff PKGBUILD
git diff .SRCINFO
```

Should show:
- Version changed from 1.1.beta to 1.2.beta
- Source URL updated to v1.2-beta tag

### Step 6: Commit Changes
```bash
git add PKGBUILD .SRCINFO
git commit -m "Update to v1.2-beta: 80 code quality fixes, security hardening, performance optimizations"
```

### Step 7: Push to AUR
```bash
git push
```

### Step 8: Verify Update
After pushing, check:
```bash
# Check git log
git log --oneline -n 3

# Verify remote
git branch -vv
```

## Expected Result

After push, AUR page will show:
- **Last Updated**: 2025-11-15 11:06 (UTC) ← NEW
- **Version**: 1.2.beta ← NEW
- **Description**: NeoArch Package Manager for Arch Linux
- **Upstream URL**: https://github.com/Sanjaya-Danushka/Neoarch

## Troubleshooting

### Permission Denied
```bash
# Verify SSH connection
ssh -T aur@aur.archlinux.org

# Should output:
# Hi sanjayadanushka, you successfully authenticated, but AUR does not provide shell access.
```

### SSH Key Issues
- Verify key is added: https://aur.archlinux.org/account/
- Check SSH config: `cat ~/.ssh/config`
- Test key: `ssh -i ~/.ssh/id_ed25519 -T aur@aur.archlinux.org`

### Checksum Mismatch
```bash
# Regenerate .SRCINFO
makepkg --printsrcinfo > .SRCINFO

# Verify it looks correct
cat .SRCINFO | grep sha256sums
```

## Complete PKGBUILD Template for v1.2-beta

```bash
# Maintainer: Sanjaya Danushka <dsanjaya712@gmail.com>
pkgname=neoarch-git
pkgver=1.2.beta
pkgrel=1
pkgdesc="NeoArch Package Manager for Arch Linux"
arch=('x86_64')
url="https://github.com/Sanjaya-Danushka/Neoarch"
license=('MIT')
depends=('python' 'python-pyqt6' 'python-requests' 'qt6-svg' 'flatpak' 'nodejs' 'npm')
makedepends=('git')
conflicts=('neoarch')
provides=('neoarch')
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
}
```

## After Update

Users will be able to install with:
```bash
yay -S neoarch-git
# or
paru -S neoarch-git
```

And they'll get v1.2-beta with:
- 80 code quality fixes
- Security hardening
- Performance optimizations
- 137 plugin cards
- Advanced filtering
- System health monitoring

## Timeline

- **Now**: Update PKGBUILD & .SRCINFO
- **Push**: git push to AUR
- **Sync**: AUR updates (usually within minutes)
- **Available**: Users can install v1.2-beta

---

**SSH Key**: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBqV2VqUECfS/YcNGrTVONmo1hG9vvKYza/liWdYPwQ1
