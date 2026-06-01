# Plugins

Extend NeoArch with custom plugins and features.

## What are Plugins?

Plugins are extensions that add new functionality to NeoArch:

- **System Tools** - Additional utilities
- **Development Tools** - Dev-focused features
- **Customization** - UI/UX enhancements
- **Integration** - Third-party service integration

## Installing Plugins

### From Plugin Store

1. Click **Plugins** tab
2. Browse available plugins
3. Click **Install** on desired plugin
4. Wait for download and installation
5. Restart NeoArch to activate

### From File

1. Click **Plugins** tab
2. Click **Install from File**
3. Select plugin file (.zip or .py)
4. Click **Install**
5. Restart NeoArch

### From GitHub

1. Click **Plugins** tab
2. Click **Install from GitHub**
3. Enter repository URL
4. Click **Install**
5. Restart NeoArch

## Managing Plugins

### View Installed Plugins

1. Click **Plugins** tab
2. See list of installed plugins
3. View plugin details
4. Check version and author

### Enable/Disable Plugins

1. Click **Plugins** tab
2. Find plugin
3. Toggle on/off
4. Changes take effect immediately

### Update Plugins

1. Click **Plugins** tab
2. Look for update indicator
3. Click **Update**
4. Restart NeoArch

### Uninstall Plugins

1. Click **Plugins** tab
2. Right-click plugin
3. Select **Uninstall**
4. Confirm removal
5. Restart NeoArch

## Available Plugins

### System Tools

**System Monitor**
- Real-time CPU/Memory/Disk usage
- Process management
- System health alerts

**Package Cleaner**
- Remove orphaned packages
- Clean package cache
- Optimize system

**Update Manager**
- Scheduled updates
- Update notifications
- Rollback support

### Development Tools

**Git Integration**
- Clone repositories
- Manage repositories
- Git operations

**Docker Manager**
- Manage containers
- Build images
- Deploy applications

**Database Tools**
- MySQL/PostgreSQL management
- Database browser
- Query executor

### Customization

**Theme Manager**
- Custom themes
- Color schemes
- UI customization

**Keyboard Shortcuts**
- Customize shortcuts
- Create macros
- Productivity boost

**Sidebar Customizer**
- Rearrange items
- Custom categories
- Quick access

### Integration

**GitHub Integration**
- Browse repositories
- Clone projects
- Manage issues

**AUR Helper Integration**
- Enhanced AUR support
- Better dependency resolution
- Advanced options

**Flatpak Manager**
- Flatpak permissions
- Remote management
- Advanced options

## Plugin Development

### Create Your Plugin

**Basic Plugin Structure:**

```python
# my_plugin.py
from neoarch.plugins import BasePlugin

class MyPlugin(BasePlugin):
    name = "My Plugin"
    version = "1.0"
    author = "Your Name"
    description = "What my plugin does"
    
    def __init__(self):
        super().__init__()
        self.setup()
    
    def setup(self):
        """Initialize plugin"""
        pass
    
    def execute(self):
        """Main plugin logic"""
        pass
    
    def cleanup(self):
        """Cleanup on uninstall"""
        pass
```

### Plugin Manifest

**plugin.json:**
```json
{
  "name": "My Plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "What my plugin does",
  "main": "my_plugin.py",
  "dependencies": ["requests"],
  "permissions": ["system", "network"],
  "category": "tools"
}
```

### Plugin Permissions

Plugins can request permissions:

- **system** - System access
- **network** - Internet access
- **filesystem** - File system access
- **packages** - Package management
- **settings** - Settings access

### Testing Plugin

```bash
# Copy plugin to plugins directory
cp my_plugin.py ~/.config/neoarch/plugins/

# Restart NeoArch
# Test plugin functionality
```

### Publishing Plugin

1. Create GitHub repository
2. Add plugin files
3. Create plugin.json
4. Submit to plugin registry
5. Plugin appears in store

## Plugin Examples

### System Monitor Plugin

```python
class SystemMonitor(BasePlugin):
    name = "System Monitor"
    
    def execute(self):
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        return {
            'cpu': cpu,
            'memory': memory,
            'disk': disk
        }
```

### Package Cleaner Plugin

```python
class PackageCleaner(BasePlugin):
    name = "Package Cleaner"
    
    def execute(self):
        # Find orphaned packages
        orphans = self.find_orphans()
        
        # Remove them
        for pkg in orphans:
            self.remove_package(pkg)
        
        return f"Removed {len(orphans)} packages"
```

### Git Integration Plugin

```python
class GitIntegration(BasePlugin):
    name = "Git Integration"
    
    def clone_repo(self, url):
        # Clone repository
        subprocess.run(['git', 'clone', url])
    
    def manage_repos(self):
        # Manage repositories
        pass
```

## Plugin Configuration

### Plugin Settings

1. Click **Plugins** tab
2. Right-click plugin
3. Select **Settings**
4. Configure options
5. Save changes

### Plugin Data

Plugins can store data:
- Configuration files
- Cache data
- User preferences

**Data Location:**
```
~/.config/neoarch/plugins/plugin-name/
```

## Troubleshooting

### Plugin Won't Install

**Problem:** Installation fails

**Solutions:**
- Check internet connection
- Verify plugin compatibility
- Check system requirements
- Review error logs

### Plugin Crashes

**Problem:** Plugin causes NeoArch to crash

**Solutions:**
- Disable plugin
- Check plugin logs
- Update plugin
- Report issue to author

### Plugin Conflicts

**Problem:** Plugins conflict with each other

**Solutions:**
- Disable conflicting plugin
- Update plugins
- Check compatibility
- Contact plugin authors

### Plugin Not Working

**Problem:** Plugin installed but doesn't work

**Solutions:**
- Restart NeoArch
- Check permissions
- Verify configuration
- Check system requirements

## Best Practices

### For Users

👤 **Installation**
- Install from official store
- Check reviews and ratings
- Verify author reputation
- Test in safe environment

👤 **Security**
- Review plugin permissions
- Check source code
- Keep plugins updated
- Disable unused plugins

👤 **Performance**
- Don't install too many plugins
- Monitor system resources
- Disable heavy plugins
- Keep system clean

### For Developers

👨‍💻 **Development**
- Follow coding standards
- Document code well
- Test thoroughly
- Handle errors gracefully

👨‍💻 **Security**
- Validate user input
- Don't request unnecessary permissions
- Secure data storage
- Report vulnerabilities

👨‍💻 **Maintenance**
- Keep plugins updated
- Support multiple versions
- Respond to issues
- Maintain documentation

## Resources

### Documentation

- [Plugin Development Guide](Plugin-Development.md)
- [API Reference](https://github.com/Sanjaya-Danushka/Neoarch/wiki/API)
- [Plugin Examples](https://github.com/Sanjaya-Danushka/Neoarch/tree/main/plugins)

### Community

- [GitHub Discussions](https://github.com/Sanjaya-Danushka/Neoarch/discussions)
- [Plugin Registry](https://github.com/Sanjaya-Danushka/Neoarch/wiki/Plugin-Registry)
- [Developer Forum](https://github.com/Sanjaya-Danushka/Neoarch/discussions/categories/plugin-development)

---

**Need help?** Check [FAQ](FAQ.md) or [Troubleshooting](Troubleshooting.md)
