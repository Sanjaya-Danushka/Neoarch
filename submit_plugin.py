#!/usr/bin/env python3
"""
NeoArch Plugin Submission Tool
Helps users prepare and submit plugins to the community repository
"""

import os
import json
import shutil
from pathlib import Path
from stores.plugin_store import PluginStore

def submit_plugin():
    """Interactive plugin submission workflow"""
    print("🚀 NeoArch Plugin Submission Tool")
    print("=" * 40)

    # Initialize plugin store
    store = PluginStore()

    # Get plugin path from user
    while True:
        plugin_path = input("Enter the path to your plugin file (.py): ").strip()
        if not plugin_path:
            continue

        plugin_path = Path(plugin_path).expanduser()
        if not plugin_path.exists():
            print(f"❌ File not found: {plugin_path}")
            continue
        if plugin_path.suffix != '.py':
            print("❌ Plugin file must have .py extension")
            continue
        break

    print(f"📁 Found plugin: {plugin_path}")

    # Validate plugin
    print("\n🔍 Validating plugin...")
    metadata = store.validate_plugin(str(plugin_path))

    if 'error' in metadata:
        print(f"❌ Validation failed: {metadata['error']}")
        return

    print("✅ Plugin validation successful!")
    print(f"📋 Plugin Name: {metadata.get('name', 'Unknown')}")
    print(f"👤 Author: {metadata.get('author', 'Unknown')}")
    print(f"🏷️ Version: {metadata.get('version', '1.0.0')}")

    # Get additional metadata
    print("\n📝 Additional Information:")

    description = input("Description (what does your plugin do?): ").strip()
    if not description:
        description = metadata.get('description', 'No description provided')

    author = input("Author name: ").strip()
    if not author:
        author = metadata.get('author', 'Unknown')

    version = input("Version (e.g., 1.0.0): ").strip()
    if not version:
        version = metadata.get('version', '1.0.0')

    # Prepare plugin for sharing
    print("\n📦 Preparing plugin for sharing...")
    plugin_id = plugin_path.stem.lower().replace(' ', '_').replace('-', '_')

    share_info = {
        'id': plugin_id,
        'name': metadata.get('name', plugin_path.stem),
        'description': description,
        'author': author,
        'version': version,
        'url': f"https://raw.githubusercontent.com/Sanjaya-Danushka/Aurora/main/community_plugins/{plugin_id}.py",
        'downloads': 0,
        'last_updated': "2024-01-01",  # Will be updated when merged
        'features': []  # User can add features later
    }

    # Create submission package
    submission_dir = Path.home() / 'neoarch_plugin_submission'
    submission_dir.mkdir(exist_ok=True)

    # Copy plugin file
    shutil.copy2(plugin_path, submission_dir / f"{plugin_id}.py")

    # Create submission info
    with open(submission_dir / 'submission_info.json', 'w') as f:
        json.dump(share_info, f, indent=2)

    # Create README for submission
    readme_content = f"""# Plugin Submission: {share_info['name']}

## Plugin Information
- **Name**: {share_info['name']}
- **ID**: {share_info['id']}
- **Author**: {share_info['author']}
- **Version**: {share_info['version']}
- **Description**: {share_info['description']}

## Files Included
- `{plugin_id}.py` - The plugin source code
- `submission_info.json` - Plugin metadata for the repository

## Submission Instructions

1. Fork the [NeoArch repository](https://github.com/Sanjaya-Danushka/Aurora)
2. Copy `{plugin_id}.py` to the `community_plugins/` directory
3. Update `community_plugins/index.json` with the contents of `submission_info.json`
4. Submit a pull request

## Plugin Validation
✅ Plugin syntax validated
✅ Basic structure verified
✅ Metadata extracted successfully

Thank you for contributing to the NeoArch community! 🎉
"""

    with open(submission_dir / 'SUBMISSION_README.md', 'w') as f:
        f.write(readme_content)

    print("\n✅ Plugin prepared for submission!")
    print(f"📁 Submission files created in: {submission_dir}")
    print("\n📋 Next Steps:")
    print("1. Review the generated files in the submission directory")
    print("2. Fork the NeoArch repository on GitHub")
    print("3. Copy the plugin file to community_plugins/ directory")
    print("4. Update community_plugins/index.json with the submission info")
    print("5. Submit a pull request")
    print("\n🔗 Repository: https://github.com/Sanjaya-Danushka/Neoarch")
    print("📚 Documentation: https://github.com/Sanjaya-Danushka/Neoarch/blob/main/community_plugins/README.md")

    # Ask if user wants to open the submission directory
    try:
        import subprocess
        open_dir = input("\n📂 Open submission directory? (y/n): ").strip().lower()
        if open_dir == 'y':
            subprocess.run(['xdg-open', str(submission_dir)])
    except Exception:
        pass

if __name__ == "__main__":
    try:
        submit_plugin()
    except KeyboardInterrupt:
        print("\n\n❌ Submission cancelled by user")
    except Exception as e:
        print(f"\n❌ Submission failed: {e}")
