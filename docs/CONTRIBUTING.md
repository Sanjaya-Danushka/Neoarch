# Contributing to NeoArch

Thank you for your interest in contributing to NeoArch! We welcome contributions from the community and are grateful for any help you can provide.

## Ways to Contribute

### 🐛 Reporting Bugs
- Use the [bug report template](https://github.com/Sanjaya-Danushka/Neoarch/issues/new?template=bug_report.md)
- Provide detailed steps to reproduce the issue
- Include system information and error logs
- Check if the issue already exists before creating a new one

### 💡 Suggesting Features
- Use the [feature request template](https://github.com/Sanjaya-Danushka/Neoarch/issues/new?template=feature_request.md)
- Describe the problem you're trying to solve
- Explain why this feature would be useful
- Consider alternative solutions

### 🛠️ Code Contributions
- Fork the repository
- Create a feature branch (`git checkout -b feature/amazing-feature`)
- Make your changes
- Add tests for new functionality
- Ensure all tests pass
- Update documentation if needed
- Commit with clear, descriptive messages
- Push to your fork
- Create a Pull Request

### 📚 Documentation
- Improve existing documentation
- Add examples and tutorials
- Translate documentation to other languages
- Fix typos and improve clarity

### 🧪 Testing
- Write unit tests for new features
- Test on different Arch Linux configurations
- Report test failures and help debug issues

## Development Setup

### Prerequisites
- Python 3.8+
- PyQt6
- Git
- Arch Linux (recommended for testing)

### Quick Start
```bash
# Clone the repository
git clone https://github.com/Sanjaya-Danushka/Neoarch.git
cd Neoarch

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements_pyqt.txt

# Run the application
python aurora_home.py
```

### Testing
```bash
# Run basic import tests
python -c "from utils import config_utils, sys_utils; print('✓ Imports work')"

# Run with pytest (if available)
pytest tests/
```

## Code Guidelines

### Python Style
- Follow [PEP 8](https://pep8.org/) style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions small and focused
- Use type hints where appropriate

### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove, etc.)
- Keep the first line under 50 characters
- Add detailed description if needed

### Pull Requests
- Create descriptive PR titles
- Reference related issues
- Provide context and rationale for changes
- Ensure CI checks pass
- Request review from maintainers

## Security Considerations

- Never commit sensitive information (API keys, passwords, etc.)
- Be careful with subprocess calls and shell commands
- Validate user input to prevent injection attacks
- Report security vulnerabilities to dsanjaya712@gmail.com

## Community Guidelines

- Be respectful and constructive in discussions
- Help newcomers and other contributors
- Follow our [Code of Conduct](CODE_OF_CONDUCT.md)
- Focus on the goals of the project

## Getting Help

- Check the [documentation](docs/) first
- Search existing [issues](https://github.com/Sanjaya-Danushka/Aurora/issues) and [discussions](https://github.com/Sanjaya-Danushka/Aurora/discussions)
- Ask questions in GitHub discussions
- Join the community chat (when available)

## Recognition

Contributors will be recognized in:
- Release notes for significant contributions
- The project's contributor list
- GitHub's contributor insights

Thank you for contributing to NeoArch! 🎉
