# Development Setup

This guide will help you set up NeoArch for development.

## Prerequisites

- Python 3.8 or higher
- Git
- PyQt6 dependencies (see installation guide)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Sanjaya-Danushka/Neoarch.git
cd Neoarch

# Switch to development branch
git checkout dev

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements_pyqt.txt

# Run the application
python aurora_home.py
```

## Development Workflow

1. Create a feature branch from `dev`
2. Make your changes
3. Test thoroughly
4. Create a Pull Request to `dev` branch
5. After review and merge, changes will be included in the next release

## Code Quality

- Run `python -m flake8` for linting
- Follow PEP 8 style guidelines
- Add docstrings to new functions
- Write tests for new features

## Building for Distribution

### AUR Package
```bash
cd neoarch-git
makepkg -si
```

### Source Distribution
```bash
python setup.py sdist bdist_wheel
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed contribution guidelines.
