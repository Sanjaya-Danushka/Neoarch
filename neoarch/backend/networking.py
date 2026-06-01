"""Network operations for package searching.

Provides threaded search against pacman official repos and the AUR
via the aur.archlinux.org RPC API.
"""

import subprocess
import json
from threading import Thread

__all__ = ["Networking"]


class Networking:
    """Static networking methods for package search operations."""

    @staticmethod
    def search_pacman(query, callback):
        """Search pacman official repositories for packages matching query.

        Args:
            query: Search string.
            callback: Function to call with list of result dicts.
        """
        def search():
            packages = []
            result = subprocess.run(["pacman", "-Ss", query], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                i = 0
                while i < len(lines):
                    if lines[i].strip() and '/' in lines[i]:
                        parts = lines[i].split()
                        if len(parts) >= 2:
                            name = parts[0].split('/')[-1]
                            version = parts[1]
                            packages.append({
                                'name': name,
                                'version': version,
                                'id': name,
                                'source': 'pacman',
                                'has_update': False
                            })
                    i += 1
            callback(packages)
        Thread(target=search, daemon=True).start()

    @staticmethod
    def search_aur(query, callback):
        """Search AUR packages via the aur.archlinux.org RPC API.

        Args:
            query: Search string.
            callback: Function to call with list of result dicts.
        """
        def search():
            packages = []
            result_aur = subprocess.run(
                ["curl", "-s", f"https://aur.archlinux.org/rpc/?v=5&type=search&by=name&arg={query}"],
                capture_output=True, text=True, timeout=10
            )
            if result_aur.returncode == 0:
                try:
                    data = json.loads(result_aur.stdout)
                    if data.get('results'):
                        for pkg in data['results']:
                            packages.append({
                                'name': pkg.get('Name', ''),
                                'version': pkg.get('Version', ''),
                                'id': pkg.get('Name', ''),
                                'source': 'AUR',
                                'has_update': False,
                                'description': pkg.get('Description', ''),
                                'tags': ', '.join(pkg.get('Keywords', []))
                            })
                except (KeyError, TypeError):
                    pass
            callback(packages)
        Thread(target=search, daemon=True).start()
