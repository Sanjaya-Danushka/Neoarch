"""Plugin store for community plugin sharing and discovery.

Manages community plugins via a GitHub-based repository, supporting
discovery, installation, template creation, validation, and sharing.
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

__all__ = ["PluginStore"]


class PluginStore:
    """Manages community plugin sharing and discovery.

    Connects to a GitHub repository of community plugins, caches them
    locally, and provides installation, template creation, and validation.
    """

    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'neoarch'
        self.plugins_dir = self.config_dir / 'plugins'
        self.store_cache = self.config_dir / 'plugin_store_cache.json'

        self.repo_url = "https://raw.githubusercontent.com/Sanjaya-Danushka/Aurora/main/community_plugins/"
        self.local_plugins = {}

        self._load_cache()

    def _load_cache(self):
        """Load cached plugin information from disk."""
        try:
            if self.store_cache.exists():
                with open(self.store_cache, 'r') as f:
                    self.local_plugins = json.load(f)
        except Exception:
            self.local_plugins = {}

    def _save_cache(self):
        """Save plugin cache to disk."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.store_cache, 'w') as f:
                json.dump(self.local_plugins, f, indent=2)
        except Exception:
            pass

    def discover_plugins(self) -> List[Dict]:
        """Discover available community plugins from the remote repository.

        Returns:
            list: Plugin metadata dictionaries, falling back to cache on failure.
        """
        if not REQUESTS_AVAILABLE:
            return list(self.local_plugins.values())
        assert requests is not None

        try:
            response = requests.get(f"{self.repo_url}index.json", timeout=10)
            if response.status_code == 200:
                remote_plugins = response.json()
                self.local_plugins.update(remote_plugins)
                self._save_cache()
                return list(remote_plugins.values())
        except Exception as e:
            print(f"Failed to fetch community plugins: {e}")

        return list(self.local_plugins.values())

    def validate_plugin(self, plugin_path: str) -> Dict:
        """Validate a plugin file and extract metadata.

        Args:
            plugin_path: Path to the plugin file.

        Returns:
            dict: Plugin metadata (name, description, author, version, functions).
        """
        try:
            with open(plugin_path, 'r') as f:
                content = f.read()

            metadata = {
                'name': 'Unknown Plugin',
                'description': '',
                'author': 'Unknown',
                'version': '1.0.0',
                'functions': []
            }

            lines = content.split('\n')
            in_docstring = False
            docstring_lines = []

            for line in lines[:20]:
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

            import ast
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metadata['functions'].append(node.name)

            return metadata
        except Exception as e:
            return {'error': str(e)}

    def share_plugin(self, plugin_path: str, metadata: Dict) -> bool:
        """Prepare plugin for sharing (creates shareable package).

        Args:
            plugin_path: Path to the plugin file.
            metadata: Plugin metadata dictionary.

        Returns:
            bool: True if the plugin was prepared successfully.
        """
        try:
            share_dir = self.config_dir / 'shared_plugins'
            share_dir.mkdir(parents=True, exist_ok=True)

            plugin_name = metadata.get('name', 'unknown').replace(' ', '_').lower()
            package_dir = share_dir / plugin_name
            package_dir.mkdir(exist_ok=True)

            plugin_filename = os.path.basename(plugin_path)
            shutil.copy2(plugin_path, package_dir / plugin_filename)

            with open(package_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            readme_content = (
                f"# {metadata.get('name', 'Plugin')}\n\n"
                f"{metadata.get('description', '')}\n\n"
                "## Installation\n\n"
                "Copy the `.py` file to your NeoArch plugins directory:\n"
                "```\n~/.config/neoarch/plugins/\n```\n\n"
                "Then enable it in Settings > Plugins.\n\n"
                "## Author\n\n"
                f"{metadata.get('author', 'Unknown')}\n\n"
                "## Version\n\n"
                f"{metadata.get('version', '1.0.0')}\n"
            )
            with open(package_dir / 'README.md', 'w') as f:
                f.write(readme_content)

            print(f"Plugin prepared for sharing: {package_dir}")
            return True
        except Exception as e:
            print(f"Failed to prepare plugin for sharing: {e}")
            return False
