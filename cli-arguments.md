# NeoArch CLI Arguments

NeoArch supports various command-line arguments for different use cases.

## Usage

```bash
python aurora_home.py [OPTIONS]
```

## Options

### Help
- `--help`, `-h`: Show help message and exit

### Development
- `--debug`: Enable debug mode with verbose logging
- `--no-sandbox`: Disable security sandboxing (not recommended)

### Configuration
- `--config FILE`: Specify custom configuration file
- `--reset-config`: Reset configuration to defaults

### Package Management
- `--install PACKAGE`: Install specific package directly
- `--remove PACKAGE`: Remove specific package directly
- `--update`: Perform system update and exit
- `--check-updates`: Check for updates without installing

### Interface
- `--minimized`: Start minimized to system tray
- `--no-gui`: Run in headless mode (CLI only)
- `--theme THEME`: Force specific theme (dark/light)

### Plugins
- `--enable-plugins`: Enable all plugins
- `--disable-plugins`: Disable all plugins
- `--plugin-dir DIR`: Specify custom plugin directory

### Advanced
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `--log-file FILE`: Write logs to specified file
- `--version`: Show version information and exit

## Examples

```bash
# Start with debug logging
python aurora_home.py --debug

# Install package directly
python aurora_home.py --install firefox

# Check for updates only
python aurora_home.py --check-updates

# Start minimized
python aurora_home.py --minimized

# Run in headless mode for automation
python aurora_home.py --no-gui --update
```

## Environment Variables

- `NEARCH_CONFIG_DIR`: Override configuration directory
- `NEARCH_PLUGIN_DIR`: Override plugin directory
- `NEARCH_LOG_LEVEL`: Set default log level
- `NEARCH_THEME`: Set default theme

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `10`: Package installation failed
- `11`: Network error
- `12`: Permission denied
