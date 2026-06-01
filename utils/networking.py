import subprocess
import json
from threading import Thread

class Networking:
    @staticmethod
    def search_pacman(query, callback):
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
        def search():
            packages = []
            result_aur = subprocess.run(["curl", "-s", f"https://aur.archlinux.org/rpc/?v=5&type=search&by=name&arg={query}"], capture_output=True, text=True, timeout=10)
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
                    # Handle malformed API response data gracefully
                    pass
            callback(packages)
        Thread(target=search, daemon=True).start()
