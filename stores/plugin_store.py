#!/usr/bin/env python3
"""
NeoArch Plugin Store
Community plugin sharing and discovery system
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional

# Optional import for requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests module not available. Community plugin features will be limited.")

class PluginStore:
    """Manages community plugin sharing and discovery"""

    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'aurora'
        self.plugins_dir = self.config_dir / 'plugins'
        self.store_cache = self.config_dir / 'plugin_store_cache.json'

        # Community plugin repository
        self.repo_url = "https://raw.githubusercontent.com/Sanjaya-Danushka/Aurora/main/community_plugins/"
        self.local_plugins = {}

        self._load_cache()

    def _load_cache(self):
        """Load cached plugin information"""
        try:
            if self.store_cache.exists():
                with open(self.store_cache, 'r') as f:
                    self.local_plugins = json.load(f)
        except Exception:
            self.local_plugins = {}

    def _save_cache(self):
        """Save plugin cache"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.store_cache, 'w') as f:
                json.dump(self.local_plugins, f, indent=2)
        except Exception:
            pass

    def discover_plugins(self) -> List[Dict]:
        """Discover available community plugins"""
        if not REQUESTS_AVAILABLE:
            print("Community plugin discovery requires the 'requests' module.")
            print("Install with: pip install requests")
            return list(self.local_plugins.values())
        
        try:
            # Try to fetch from GitHub repository
            response = requests.get(f"{self.repo_url}index.json", timeout=10)
            if response.status_code == 200:
                remote_plugins = response.json()
                self.local_plugins.update(remote_plugins)
                self._save_cache()
                return list(remote_plugins.values())
        except Exception as e:
            print(f"Failed to fetch community plugins: {e}")
        
        # Fallback to cached plugins
        return list(self.local_plugins.values())

    def install_community_plugin(self, plugin_id: str) -> bool:
        """Install a plugin from the community repository"""
        if not REQUESTS_AVAILABLE:
            print("Community plugin installation requires the 'requests' module.")
            print("Install with: pip install requests")
            return False
        
        try:
            # Get plugin metadata
            plugins = self.discover_plugins()
            plugin_info = None

            for plugin in plugins:
                if plugin.get('id') == plugin_id:
                    plugin_info = plugin
                    break

            if not plugin_info:
                return False

            # Download plugin file
            plugin_url = plugin_info.get('url')
            if plugin_url:
                response = requests.get(plugin_url, timeout=30)
                if response.status_code == 200:
                    # Save to user plugins directory
                    plugin_filename = f"{plugin_id}.py"
                    plugin_path = self.plugins_dir / plugin_filename

                    self.plugins_dir.mkdir(parents=True, exist_ok=True)
                    with open(plugin_path, 'w') as f:
                        f.write(response.text)

                    return True

            # Alternative: use direct GitHub raw URL
            github_url = f"{self.repo_url}{plugin_id}.py"
            response = requests.get(github_url, timeout=30)
            if response.status_code == 200:
                plugin_path = self.plugins_dir / f"{plugin_id}.py"
                self.plugins_dir.mkdir(parents=True, exist_ok=True)
                with open(plugin_path, 'w') as f:
                    f.write(response.text)
                return True

        except Exception as e:
            print(f"Failed to install community plugin {plugin_id}: {e}")

        return False

    def create_plugin_template(self, plugin_name: str, description: str = "") -> str:
        """Create a plugin template for users to customize"""
        template = f'''"""
{plugin_name} - NeoArch Plugin
{description}

Author: Your Name
Version: 1.0.0
"""

def on_startup(app):
    """
    Called when NeoArch starts up
    Use this to initialize your plugin
    """
    try:
        print(f"🚀 {plugin_name} plugin loaded!")
        # Add your startup code here

    except Exception as e:
        print(f"Error in {plugin_name} startup: {{e}}")

def on_tick(app):
    """
    Called periodically (every 60 seconds)
    Use this for background tasks
    """
    try:
        # Add your periodic tasks here
        pass
    except Exception as e:
        print(f"Error in {plugin_name} tick: {{e}}")

def on_view_changed(app, view_id):
    """
    Called when user switches between views
    view_id can be: "discover", "updates", "installed", "bundles", "plugins", "settings"
    """
    try:
        if view_id == "discover":
            # User switched to discover page
            pass
        elif view_id == "plugins":
            # User switched to plugins page
            pass
    except Exception as e:
        print(f"Error in {plugin_name} view change: {{e}}")

# Add your custom functions below
def my_custom_function(app, param=None):
    """
    Example custom function
    You can call this from other parts of your plugin
    """
    try:
        print(f"{plugin_name}: Custom function called with param: {{param}}")
        # Add your custom logic here
    except Exception as e:
        print(f"Error in {plugin_name} custom function: {{e}}")
'''
        return template

    def validate_plugin(self, plugin_path: str) -> Dict:
        """Validate a plugin file and extract metadata"""
        try:
            with open(plugin_path, 'r') as f:
                content = f.read()

            # Extract basic metadata
            metadata = {
                'name': 'Unknown Plugin',
                'description': '',
                'author': 'Unknown',
                'version': '1.0.0',
                'functions': []
            }

            # Parse docstring for name and description
            lines = content.split('\n')
            in_docstring = False
            docstring_lines = []

            for line in lines[:20]:  # Check first 20 lines
                if '"""' in line:
                    if not in_docstring:
                        in_docstring = True
                    else:
                        break
                elif in_docstring:
                    docstring_lines.append(line.strip())

            if docstring_lines:
                metadata['name'] = docstring_lines[0] if docstring_lines else 'Unknown Plugin'
                if len(docstring_lines) > 1:
                    metadata['description'] = ' '.join(docstring_lines[1:])

            # Extract function names
            import ast
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metadata['functions'].append(node.name)

            return metadata

        except Exception as e:
            return {'error': str(e)}

    def share_plugin(self, plugin_path: str, metadata: Dict) -> bool:
        """Prepare plugin for sharing (creates shareable package)"""
        try:
            # Create a shareable package
            share_dir = self.config_dir / 'shared_plugins'
            share_dir.mkdir(parents=True, exist_ok=True)

            plugin_name = metadata.get('name', 'unknown').replace(' ', '_').lower()
            package_dir = share_dir / plugin_name
            package_dir.mkdir(exist_ok=True)

            # Copy plugin file
            import shutil
            plugin_filename = os.path.basename(plugin_path)
            shutil.copy2(plugin_path, package_dir / plugin_filename)

            # Create metadata file
            with open(package_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            # Create README
            readme_content = f"""# {metadata.get('name', 'Plugin')}

{metadata.get('description', '')}

## Installation

Copy the `.py` file to your NeoArch plugins directory:
```
~/.config/aurora/plugins/
```

Then enable it in Settings → Plugins.

## Author

{metadata.get('author', 'Unknown')}

## Version

{metadata.get('version', '1.0.0')}
"""
            with open(package_dir / 'README.md', 'w') as f:
                f.write(readme_content)

            print(f"Plugin prepared for sharing: {package_dir}")
            return True

        except Exception as e:
            print(f"Failed to prepare plugin for sharing: {e}")
            return False

# Example usage in NeoArch plugin
def plugin_store_example(app):
    """Example of how to integrate PluginStore into NeoArch"""

    store = PluginStore()

    # Discover available plugins
    community_plugins = store.discover_plugins()

    # Install a community plugin
    if store.install_community_plugin("example_plugin"):
        app.log("Successfully installed community plugin!")
        app.reload_plugins()

    # Create a new plugin template
    template = store.create_plugin_template(
        "My Custom Plugin",
        "A plugin that does amazing things"
    )

    # Save template to file
    template_path = store.plugins_dir / "my_custom_plugin_template.py"
    with open(template_path, 'w') as f:
        f.write(template)

    app.log(f"Plugin template created: {template_path}")
