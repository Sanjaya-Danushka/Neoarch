# NeoArch Community Plugins

Welcome to the NeoArch Community Plugins repository! This is where users can share their custom plugins with the NeoArch community.

## 🚀 Getting Started

### For Users - Installing Community Plugins

1. Open NeoArch and go to **Plugins** → **Community Plugins** tab
2. Browse available plugins
3. Click **Install** on any plugin you want
4. Go to **Settings** → **Plugins** to enable the installed plugin

### For Developers - Creating and Sharing Plugins

#### 1. Create Your Plugin

Use the built-in plugin creator in NeoArch:
- Go to **Plugins** → **Community Plugins** tab
- Click **Create Plugin**
- Fill in your plugin details
- Customize the generated template

#### 2. Plugin Structure

```python
"""
Your Plugin Name
Brief description of what your plugin does

Author: Your Name
Version: 1.0.0
"""

def on_startup(app):
    """Called when NeoArch starts"""
    # Your initialization code here

def on_tick(app):
    """Called every 60 seconds"""
    # Your periodic tasks here

def on_view_changed(app, view_id):
    """Called when user switches views"""
    # React to view changes here

# Add your custom functions
def my_custom_function(app, param=None):
    """Custom function description"""
    # Your custom logic here
```

#### 3. Available Plugin Hooks

- `on_startup(app)` - Called when NeoArch starts
- `on_tick(app)` - Called every 60 seconds
- `on_view_changed(app, view_id)` - Called when user switches views

#### 4. NeoArch API

Your plugin can access the main NeoArch application through the `app` parameter:

```python
# Logging
app.log("Your message here")

# Show messages to user
app.show_message.emit("Title", "Message")

# Access settings
setting_value = app.settings.get('setting_name')

# Run system commands
import subprocess
result = subprocess.run(["command"], capture_output=True, text=True)
```

#### 5. Share Your Plugin

To share your plugin with the community:

1. Create your plugin file
2. Test it thoroughly
3. Submit a pull request to this repository
4. Add your plugin to the `index.json` file

## 📋 Plugin Guidelines

### ✅ Do's
- Use clear, descriptive names
- Include comprehensive documentation
- Handle errors gracefully
- Follow Python best practices
- Test on multiple systems

### ❌ Don'ts
- Don't include harmful code
- Don't access private user data without permission
- Don't modify system files without user consent
- Don't spam the console with excessive logging
- Don't create plugins that interfere with core NeoArch functionality

## 🛠️ Development Tools

NeoArch includes built-in tools to help you develop plugins:

- **Plugin Creator**: Generate plugin templates
- **Plugin Validator**: Check plugin syntax and structure
- **Plugin Sharer**: Prepare plugins for sharing

## 📚 Examples

Check out the `example_plugin.py` for a complete working example that demonstrates:
- Startup initialization
- Periodic tasks
- View change handling
- System monitoring
- Custom functions

## 🤝 Contributing

We welcome contributions! Here's how to contribute:

1. Fork this repository
2. Create your plugin
3. Test it thoroughly
4. Update the `index.json` file
5. Submit a pull request

## 📄 License

All community plugins should be compatible with the NeoArch license. Please include appropriate licensing information in your plugin.

## 🆘 Support

- Check the [NeoArch Documentation](https://github.com/Sanjaya-Danushka/Neoarch)
- Open issues for bugs or feature requests
- Join the community discussions

---

Happy plugin development! 🎉
