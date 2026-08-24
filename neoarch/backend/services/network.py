"""Network settings service backing Settings ▸ Proxy & Network.

Makes these controls real:
  - proxy_type/host/port  → applied to every in-app HTTP request AND exported
                            as http_proxy/https_proxy env vars so child
                            processes (pacman wrappers, npm, curl) inherit it
  - verify_ssl            → TLS certificate verification for in-app requests
  - request_timeout       → default timeout for in-app HTTP requests

Call `apply_network_env()` at startup and whenever any of these settings
change; use `urlopen()`/`default_timeout()` from this module instead of
urllib directly inside the backend.
"""

import os
import ssl
import urllib.request
import threading

__all__ = ["urlopen", "default_timeout", "build_opener", "apply_network_env",
           "proxy_enabled"]

_lock = threading.Lock()
_opener = None


def default_timeout() -> int:
    """Configured request timeout in seconds (fallback 30)."""
    try:
        from neoarch.backend.services.settings import DEFAULT_SETTINGS
        return int(DEFAULT_SETTINGS.get('request_timeout', 30))
    except Exception:
        return 30


def _read_network_settings() -> dict:
    """Read proxy/SSL settings straight from the settings file.

    Read on each rebuild — cheap, and keeps the service decoupled from the
    GUI process state.
    """
    from neoarch.backend.services.settings import load_settings
    s = load_settings()
    return {
        "type": str(s.get('proxy_type', 'none') or 'none'),
        "host": str(s.get('proxy_host', '') or ''),
        "port": int(s.get('proxy_port', 8080) or 8080),
        "verify_ssl": bool(s.get('verify_ssl', True)),
        "timeout": int(s.get('request_timeout', 30) or 30),
    }


def proxy_url(cfg=None):
    cfg = cfg or _read_network_settings()
    if cfg["type"] == "none" or not cfg["host"]:
        return None
    scheme = cfg["type"] if cfg["type"] in ("http", "https", "socks5") else "http"
    # urllib natively supports http proxies; https/socks5 URLs require a
    # handler that most environments lack, so route them via http CONNECT.
    netloc = f"{cfg['host']}:{cfg['port']}"
    return f"http://{netloc}"


def build_opener(cfg=None) -> urllib.request.OpenerDirector:
    """Opener honouring proxy + SSL settings."""
    cfg = cfg or _read_network_settings()
    handlers = []
    purl = proxy_url(cfg)
    if purl:
        handlers.append(urllib.request.ProxyHandler({
            "http": purl,
            "https": purl,
        }))
    else:
        handlers.append(urllib.request.ProxyHandler({}))  # direct, ignore env
    if not cfg["verify_ssl"]:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener(*handlers)


def apply_network_env(env: dict = None) -> dict:
    """Sync proxy config into an environment dict (os.environ by default).

    Child processes launched after this call inherit the proxy.
    """
    target = os.environ if env is None else env
    cfg = _read_network_settings()
    purl = proxy_url(cfg)
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        target.pop(key, None)
    target.pop("no_proxy", None)
    if purl:
        target["http_proxy"] = purl
        target["https_proxy"] = purl
    return target


def refresh():
    """Rebuild the shared opener; call after network settings change."""
    global _opener
    with _lock:
        _opener = build_opener()
        urllib.request.install_opener(_opener)
    apply_network_env()


def urlopen(req, timeout=None):
    """urllib.request.urlopen with configured opener and timeout."""
    with _lock:
        opener = _opener
    if opener is None:
        refresh()
        with _lock:
            opener = _opener
    return opener.open(req, timeout=timeout if timeout is not None else default_timeout())


def proxy_enabled() -> bool:
    return bool(proxy_url())
