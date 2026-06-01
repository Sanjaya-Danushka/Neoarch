#!/bin/bash
# NeoArch Deep Clean Script
# Removes all build artifacts, cache files, and temporary data

set -e

echo "🧹 NeoArch Deep Clean"
echo "===================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "aurora_home.py" ]; then
    print_error "Not in NeoArch directory. Please run from the project root."
    exit 1
fi

echo "Cleaning NeoArch project..."

# Python cache files
print_status "Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*.pyd" -delete

# Virtual environments
print_status "Removing virtual environments..."
rm -rf venv/ env/ ENV/ .venv/

# Build artifacts
print_status "Removing build artifacts..."
rm -rf build/ dist/ *.egg-info/
rm -f *.tar.gz *.zip *.deb *.rpm *.AppImage

# IDE files
print_status "Removing IDE files..."
rm -rf .vscode/ .idea/
find . -name "*.swp" -delete
find . -name "*.swo" -delete
find . -name "*~" -delete

# OS specific files
print_status "Removing OS-specific files..."
rm -f .DS_Store Thumbs.db
find . -name ".DS_Store" -delete

# Logs
print_status "Removing log files..."
rm -f *.log
rm -rf logs/

# Temporary files
print_status "Removing temporary files..."
find . -name "*.tmp" -delete
find . -name "*.bak" -delete
find . -name "*.old" -delete

# Test artifacts
print_status "Removing test artifacts..."
rm -rf .coverage .pytest_cache/ .tox/ .cache/
rm -f nosetests.xml coverage.xml *.cover
find . -name ".hypothesis" -type d -exec rm -rf {} + 2>/dev/null || true

# Flatpak artifacts
print_status "Removing Flatpak artifacts..."
rm -rf .flatpak-builder/ build-dir/

# AUR artifacts
print_status "Removing AUR artifacts..."
rm -f *.pkg.tar.zst *.pkg.tar.xz

# Node.js artifacts (if any)
print_status "Removing Node.js artifacts..."
rm -rf node_modules/
rm -f package-lock.json npm-debug.log*

# Database files
print_status "Removing database files..."
find . -name "*.db" -delete
find . -name "*.sqlite" -delete
find . -name "*.sqlite3" -delete

# Secrets and config
print_warning "Checking for sensitive files..."
if [ -f ".env" ]; then
    print_warning ".env file found - not removing (contains sensitive data)"
fi
if [ -f "secrets.json" ]; then
    print_warning "secrets.json found - not removing (contains sensitive data)"
fi

# Git clean (optional - ask user)
echo ""
read -p "Also run 'git clean -fdx'? This will remove ALL untracked files (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Running git clean -fdx..."
    git clean -fdx
fi

echo ""
print_status "Deep clean completed!"
print_status "NeoArch project is now clean and ready for fresh build."

# Show disk usage if possible
if command -v du >/dev/null 2>&1; then
    echo ""
    echo "Current directory size:"
    du -sh . 2>/dev/null || true
fi
