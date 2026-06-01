import os
import json

def get_ignore_file_path():
    cfg = os.path.join(os.path.expanduser('~'), '.config', 'neoarch')
    try:
        os.makedirs(cfg, exist_ok=True)
    except Exception:
        pass
    return os.path.join(cfg, 'ignored_updates.json')


def load_ignored_updates():
    p = get_ignore_file_path()
    try:
        with open(p, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data)
    except Exception:
        pass
    return set()


def save_ignored_updates(items):
    p = get_ignore_file_path()
    try:
        with open(p, 'w') as f:
            json.dump(sorted(list(items)), f)
    except Exception:
        pass


def get_local_updates_file_path():
    cfg = os.path.join(os.path.expanduser('~'), '.config', 'neoarch')
    try:
        os.makedirs(cfg, exist_ok=True)
    except Exception:
        pass
    return os.path.join(cfg, 'local_updates.json')


def load_local_update_entries():
    p = get_local_updates_file_path()
    try:
        with open(p, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []
