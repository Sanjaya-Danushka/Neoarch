import os
import json
import subprocess
from threading import Thread


def load_updates(app):
    try:
        app._updates_loading = True
    except Exception:
        pass
    app.package_table.setRowCount(0)
    app.all_packages = []
    app.current_page = 0
    app.cancel_update_load = False
    app.loading_context = "updates"

    app.loading_widget.setVisible(True)
    try:
        app.loading_widget.set_message("Checking for updates...")
    except Exception:
        pass
    app.package_table.setVisible(False)
    app.load_more_btn.setVisible(False)
    app.loading_widget.start_animation()
    try:
        if hasattr(app, 'loading_container'):
            app.loading_container.setVisible(True)
    except Exception:
        pass
    try:
        app.cancel_install_btn.setVisible(False)
    except Exception:
        pass
    try:
        if hasattr(app, 'console_toggle_btn'):
            app.console_toggle_btn.setVisible(True)
            app.console_toggle_btn.setToolTip("Show Console")
    except Exception:
        pass

    def load_in_thread():
        try:
            packages = []

            # Sync package database first to get latest updates
            try:
                app.log("Syncing package database...")
                env, _ = app.prepare_askpass_env()
                sync_result = subprocess.run(["sudo", "-A", "pacman", "-Sy", "--noconfirm"], 
                                            capture_output=True, text=True, timeout=120, env=env)
                if sync_result.returncode == 0:
                    app.log("Package database synced successfully")
                else:
                    err = sync_result.stderr or ""
                    app.log(f"Warning: Database sync failed: {err}")
                    low = err.lower()
                    if ("could not lock database" in low) or ("unable to lock database" in low):
                        try:
                            app.ui_call.emit(lambda: app.show_busy_pm_warning(err))
                        except Exception:
                            pass
            except Exception as e:
                app.log(f"Warning: Could not sync database: {str(e)}")

            result = subprocess.run(["pacman", "-Qu"], capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        if ' -> ' in line:
                            parts = line.split(' -> ')
                            if len(parts) == 2:
                                package_info = parts[0].strip().split()
                                new_version = parts[1].strip()
                                if len(package_info) >= 2:
                                    package_name = package_info[0]
                                    current_version = package_info[1]
                                    packages.append({
                                        'name': package_name,
                                        'version': current_version,
                                        'new_version': new_version,
                                        'id': package_name,
                                        'source': 'pacman'
                                    })

            try:
                result_aur = subprocess.run(["yay", "-Qua"], capture_output=True, text=True, timeout=60)
                if result_aur.returncode == 0 and result_aur.stdout:
                    for line in result_aur.stdout.strip().split('\n'):
                        if line.strip() and ' -> ' in line:
                            parts = line.split(' -> ')
                            if len(parts) == 2:
                                package_info = parts[0].strip().split()
                                new_version = parts[1].strip()
                                if len(package_info) >= 2:
                                    package_name = package_info[0]
                                    current_version = package_info[1]
                                    packages.append({
                                        'name': package_name,
                                        'version': current_version,
                                        'new_version': new_version,
                                        'id': package_name,
                                        'source': 'AUR'
                                    })
            except (subprocess.CalledProcessError, FileNotFoundError):
                for aur_helper in ['paru', 'trizen', 'pikaur']:
                    try:
                        result_aur = subprocess.run([aur_helper, "-Qua"], capture_output=True, text=True, timeout=60)
                        if result_aur.returncode == 0 and result_aur.stdout:
                            for line in result_aur.stdout.strip().split('\n'):
                                if line.strip() and ' -> ' in line:
                                    parts = line.split(' -> ')
                                    if len(parts) == 2:
                                        package_info = parts[0].strip().split()
                                        new_version = parts[1].strip()
                                        if len(package_info) >= 2:
                                            package_name = package_info[0]
                                            current_version = package_info[1]
                                            packages.append({
                                                'name': package_name,
                                                'version': current_version,
                                                'new_version': new_version,
                                                'id': package_name,
                                                'source': 'AUR'
                                            })
                            break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue

            added_flatpak = False
            try:
                installed_map = {}
                for scope in ([], ["--user"], ["--system"]):
                    try:
                        cmd = ["flatpak"] + scope + ["list", "--app", "--columns=application,version"]
                        li = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        if li.returncode == 0 and li.stdout:
                            for ln in [x for x in li.stdout.strip().split('\n') if x.strip()]:
                                c = ln.split('\t')
                                if c and c[0].strip():
                                    installed_map[c[0].strip()] = (c[1].strip() if len(c) > 1 else '')
                    except Exception:
                        continue

                seen_apps = set()
                for scope in ([], ["--user"], ["--system"]):
                    try:
                        cmd = ["flatpak"] + scope + ["list", "--app", "--updates", "--columns=application,version"]
                        fp = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        if fp.returncode == 0 and fp.stdout:
                            for line in [l for l in fp.stdout.strip().split('\n') if l.strip()]:
                                cols = line.split('\t')
                                app_id = cols[0].strip() if len(cols) > 0 else ''
                                inst = cols[1].strip() if len(cols) > 1 else ''
                                if app_id and app_id not in seen_apps:
                                    packages.append({
                                        'name': app_id,
                                        'version': inst or installed_map.get(app_id, ''),
                                        'new_version': '',
                                        'id': app_id,
                                        'source': 'Flatpak'
                                    })
                                    seen_apps.add(app_id)
                                    added_flatpak = True
                    except Exception:
                        continue

                if not added_flatpak:
                    try:
                        rl = subprocess.run(["flatpak", "remote-ls", "--updates", "--columns=application,version"], capture_output=True, text=True, timeout=60)
                        if rl.returncode == 0 and rl.stdout:
                            for ln in [x for x in rl.stdout.strip().split('\n') if x.strip()]:
                                c = ln.split('\t')
                                app_id = c[0].strip() if len(c) > 0 else ''
                                latest = c[1].strip() if len(c) > 1 else ''
                                if app_id and app_id in installed_map and app_id not in seen_apps:
                                    packages.append({
                                        'name': app_id,
                                        'version': installed_map.get(app_id, ''),
                                        'new_version': latest,
                                        'id': app_id,
                                        'source': 'Flatpak'
                                    })
                                    seen_apps.add(app_id)
                                    added_flatpak = True
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                results = []
                np_def = subprocess.run(["npm", "outdated", "-g", "--json"], capture_output=True, text=True, timeout=60)
                results.append((np_def.returncode, np_def.stdout))
                env_user = os.environ.copy()
                try:
                    npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                    os.makedirs(npm_prefix, exist_ok=True)
                    env_user['npm_config_prefix'] = npm_prefix
                    env_user['NPM_CONFIG_PREFIX'] = npm_prefix
                    env_user['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env_user.get('PATH', '')
                except Exception:
                    pass
                np_user = subprocess.run(["npm", "outdated", "-g", "--json"], capture_output=True, text=True, env=env_user, timeout=60)
                results.append((np_user.returncode, np_user.stdout))
                seen = set()
                for code, out in results:
                    if code in (0, 1) and out and out.strip():
                        try:
                            data = json.loads(out)
                            if isinstance(data, dict):
                                for name, info in data.items():
                                    cur = (info.get('current') or info.get('installed') or '').strip()
                                    lat = (info.get('latest') or '').strip()
                                    key = (name, cur, lat)
                                    if name and cur and lat and cur != lat and key not in seen:
                                        packages.append({
                                            'name': name,
                                            'version': cur,
                                            'new_version': lat,
                                            'id': name,
                                            'source': 'npm'
                                        })
                                        seen.add(key)
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                entries = app.load_local_update_entries()
                for e in entries:
                    name = (e.get('name') or '').strip()
                    if not name:
                        continue
                    installed = (e.get('installed_version') or '').strip()
                    if not installed and e.get('installed_version_cmd'):
                        try:
                            r = subprocess.run(["bash", "-lc", e['installed_version_cmd']], capture_output=True, text=True, timeout=30)
                            if r.returncode == 0:
                                installed = (r.stdout or '').strip().splitlines()[0].strip()
                        except Exception:
                            installed = ''
                    latest = (e.get('latest_version') or '').strip()
                    if not latest and e.get('latest_version_cmd'):
                        try:
                            r = subprocess.run(["bash", "-lc", e['latest_version_cmd']], capture_output=True, text=True, timeout=30)
                            if r.returncode == 0:
                                latest = (r.stdout or '').strip().splitlines()[0].strip()
                        except Exception:
                            latest = ''
                    if installed and latest and installed != latest:
                        packages.append({
                            'name': name,
                            'version': installed,
                            'new_version': latest,
                            'id': (e.get('id') or name),
                            'source': 'Local'
                        })
            except Exception:
                pass

            try:
                ignored = app.load_ignored_updates()
                if ignored:
                    packages = [p for p in packages if p.get('name') not in ignored]
            except Exception:
                pass

            if not app.cancel_update_load and app.loading_context == 'updates' and app.current_view == 'updates':
                try:
                    app._updates_loading = False
                except Exception:
                    pass
                app.packages_ready.emit(packages)
        except Exception as e:
            app.log(f"Error: {str(e)}")
            try:
                app._updates_loading = False
            except Exception:
                pass
            app.load_error.emit()

    Thread(target=load_in_thread, daemon=True).start()



def load_installed_packages(app):
    app.package_table.setRowCount(0)
    app.all_packages = []
    app.current_page = 0
    app.loading_context = "installed"

    def load_in_thread():
        try:
            result = subprocess.run(["pacman", "-Q"], capture_output=True, text=True, timeout=60)
            packages = []
            updates = {}

            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            packages.append({
                                'name': parts[0],
                                'version': parts[1],
                                'id': parts[0],
                                'source': 'pacman',
                                'has_update': False
                            })
                    if i % 100 == 0 and i > 0:
                        import time
                        time.sleep(0.01)

            result_updates = subprocess.run(["pacman", "-Qu"], capture_output=True, text=True, timeout=30)
            if result_updates.returncode == 0 and result_updates.stdout:
                for line in result_updates.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            updates[parts[0]] = parts[2] if len(parts) > 2 else parts[1]

            for pkg in packages:
                if pkg['name'] in updates:
                    pkg['has_update'] = True
                    pkg['new_version'] = updates[pkg['name']]

            result_aur = subprocess.run(["pacman", "-Qm"], capture_output=True, text=True, timeout=30)
            aur_packages = set()
            if result_aur.returncode == 0 and result_aur.stdout:
                for line in result_aur.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 1:
                            aur_packages.add(parts[0])

            for pkg in packages:
                if pkg['name'] in aur_packages:
                    pkg['source'] = 'AUR'

            try:
                aur_updates = {}
                helper = None
                for h in ['yay', 'paru', 'trizen', 'pikaur']:
                    try:
                        r = subprocess.run([h, "-Qua"], capture_output=True, text=True, timeout=60)
                        if r.returncode in (0, 1):
                            helper = h
                            output = (r.stdout or '').strip()
                            if output:
                                for ln in [x for x in output.split('\n') if x.strip()]:
                                    parts = ln.split()
                                    if len(parts) >= 2:
                                        name = parts[0]
                                        if '->' in ln:
                                            try:
                                                new_v = parts[-1]
                                            except Exception:
                                                new_v = ''
                                        else:
                                            new_v = parts[1]
                                        aur_updates[name] = new_v
                            break
                    except Exception:
                        continue
                if aur_updates:
                    for pkg in packages:
                        if pkg.get('source') == 'AUR' and pkg['name'] in aur_updates:
                            pkg['has_update'] = True
                            pkg['new_version'] = aur_updates.get(pkg['name'], pkg.get('new_version', ''))
            except Exception:
                pass

            try:
                installed_map = {}
                seen = set()
                for scope in ([], ["--user"], ["--system"]):
                    cmd = ["flatpak"] + scope + ["list", "--app", "--columns=application,version"]
                    fp = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if fp.returncode == 0 and fp.stdout:
                        for ln in [x for x in fp.stdout.strip().split('\n') if x.strip()]:
                            c = ln.split('\t')
                            app_id = c[0].strip() if len(c) > 0 else ''
                            ver = c[1].strip() if len(c) > 1 else ''
                            if app_id:
                                installed_map[app_id] = ver
                            if app_id and app_id not in seen:
                                packages.append({
                                    'name': app_id,
                                    'version': ver,
                                    'id': app_id,
                                    'source': 'Flatpak',
                                    'has_update': False
                                })
                                seen.add(app_id)
            except Exception:
                pass

            try:
                update_ids = set()
                for scope in ([], ["--user"], ["--system"]):
                    cmdu = ["flatpak"] + scope + ["list", "--app", "--updates", "--columns=application,version"]
                    fu = subprocess.run(cmdu, capture_output=True, text=True, timeout=60)
                    if fu.returncode == 0 and fu.stdout:
                        for ln in [x for x in fu.stdout.strip().split('\n') if x.strip()]:
                            cols = ln.split('\t')
                            if cols:
                                update_ids.add(cols[0].strip())
                if not update_ids:
                    try:
                        rl = subprocess.run(["flatpak", "remote-ls", "--updates", "--columns=application,version"], capture_output=True, text=True, timeout=60)
                        if rl.returncode == 0 and rl.stdout:
                            for ln in [x for x in rl.stdout.strip().split('\n') if x.strip()]:
                                c = ln.split('\t')
                                app_id = c[0].strip() if len(c) > 0 else ''
                                latest = c[1].strip() if len(c) > 1 else ''
                                if app_id and app_id in installed_map:
                                    update_ids.add(app_id)
                                    for pkg in packages:
                                        if pkg.get('source') == 'Flatpak' and pkg.get('name') == app_id:
                                            if latest:
                                                pkg['new_version'] = latest
                    except Exception:
                        pass
                if update_ids:
                    for pkg in packages:
                        if pkg.get('source') == 'Flatpak' and pkg.get('name') in update_ids:
                            pkg['has_update'] = True
            except Exception:
                pass

            try:
                results = []
                np_def = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True, timeout=60)
                results.append((np_def.returncode, np_def.stdout))
                env_user = os.environ.copy()
                try:
                    npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                    os.makedirs(npm_prefix, exist_ok=True)
                    env_user['npm_config_prefix'] = npm_prefix
                    env_user['NPM_CONFIG_PREFIX'] = npm_prefix
                    env_user['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env_user.get('PATH', '')
                except Exception:
                    pass
                np_user = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True, env=env_user, timeout=60)
                results.append((np_user.returncode, np_user.stdout))
                seen = set()
                for code, out in results:
                    if code == 0 and out and out.strip():
                        try:
                            data = json.loads(out)
                            deps = (data.get('dependencies') or {}) if isinstance(data, dict) else {}
                            for name, info in deps.items():
                                ver = (info.get('version') or '').strip()
                                if name and ver and (name, ver) not in seen:
                                    packages.append({
                                        'name': name,
                                        'version': ver,
                                        'id': name,
                                        'source': 'npm',
                                        'has_update': False
                                    })
                                    seen.add((name, ver))
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                results = []
                np_def = subprocess.run(["npm", "outdated", "-g", "--json"], capture_output=True, text=True, timeout=60)
                results.append((np_def.returncode, np_def.stdout))
                env_user = os.environ.copy()
                try:
                    npm_prefix = os.path.join(os.path.expanduser('~'), '.npm-global')
                    os.makedirs(npm_prefix, exist_ok=True)
                    env_user['npm_config_prefix'] = npm_prefix
                    env_user['NPM_CONFIG_PREFIX'] = npm_prefix
                    env_user['PATH'] = os.path.join(npm_prefix, 'bin') + os.pathsep + env_user.get('PATH', '')
                except Exception:
                    pass
                np_user = subprocess.run(["npm", "outdated", "-g", "--json"], capture_output=True, text=True, env=env_user, timeout=60)
                results.append((np_user.returncode, np_user.stdout))
                outdated = {}
                for code, out in results:
                    if code in (0, 1) and out and out.strip():
                        try:
                            data = json.loads(out)
                            if isinstance(data, dict):
                                for name, info in data.items():
                                    lat = (info.get('latest') or '').strip()
                                    cur = (info.get('current') or info.get('installed') or '').strip()
                                    if name and lat and cur and cur != lat:
                                        outdated[name] = lat
                        except Exception:
                            pass
                if outdated:
                    for pkg in packages:
                        if pkg.get('source') == 'npm' and pkg.get('name') in outdated:
                            pkg['has_update'] = True
                            pkg['new_version'] = outdated[pkg['name']]
            except Exception:
                pass

            try:
                entries = app.load_local_update_entries()
                for e in entries:
                    name = (e.get('name') or '').strip()
                    if not name:
                        continue
                    installed = (e.get('installed_version') or '').strip()
                    if not installed and e.get('installed_version_cmd'):
                        try:
                            r = subprocess.run(["bash", "-lc", e['installed_version_cmd']], capture_output=True, text=True, timeout=30)
                            if r.returncode == 0 and r.stdout:
                                installed = (r.stdout or '').strip().splitlines()[0].strip()
                        except Exception:
                            installed = ''
                    latest = (e.get('latest_version') or '').strip()
                    if not latest and e.get('latest_version_cmd'):
                        try:
                            r = subprocess.run(["bash", "-lc", e['latest_version_cmd']], capture_output=True, text=True, timeout=30)
                            if r.returncode == 0 and r.stdout:
                                latest = (r.stdout or '').strip().splitlines()[0].strip()
                        except Exception:
                            latest = ''
                    if installed:
                        pkg = {
                            'name': name,
                            'version': installed,
                            'new_version': latest or installed,
                            'id': (e.get('id') or name),
                            'source': 'Local',
                            'has_update': (bool(latest) and latest != installed)
                        }
                        packages.append(pkg)
            except Exception:
                pass

            try:
                ignored = app.load_ignored_updates()
                if ignored:
                    for pkg in packages:
                        if pkg.get('name') in ignored and pkg.get('has_update'):
                            pkg['has_update'] = False
            except Exception:
                pass

            app.packages_ready.emit(packages)
        except Exception as e:
            app.log(f"Error: {str(e)}")
            app.load_error.emit()

    Thread(target=load_in_thread, daemon=True).start()
