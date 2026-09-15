"""Lightweight network latency measurement.

Records latency for HTTP requests made through ``urllib.request.urlopen`` and
``requests.get`` (patched by ``install()``), and periodically probes a stable
endpoint (``start_probing()``) so the signal indicator reflects the real
connection even while the app is idle. A failed request is recorded as a
failure, which maps to the "no signal" state.

``install()`` is idempotent and safe to call more than once.
"""

import os
import socket
import threading
import time
import urllib.parse
import urllib.request

_MAX_SAMPLES = 10
_PROBE_URL = "https://archlinux.org/"
_PROBE_TIMEOUT = 5.0
_CONSECUTIVE_FAILURES_THRESHOLD = 2
_SOCKET_CHECK_TIMEOUT = 2.0
_CONNECTIVITY_CHECK_INTERVAL = 1.0
_SOCKET_DEBOUNCE_FAILURES = 3
_HTTP_SUCCESS_FRESH_SECS = 60.0
# Any of these reachable = internet up. Port 443 (not just 53) survives
# networks that filter raw DNS egress, IPs from different providers
# survive single-region outages, and a proxy-only setup is covered by the
# HTTP-success path (record()).
_SOCKET_CHECK_TARGETS = (
    ("1.1.1.1", 443),
    ("8.8.8.8", 443),
    ("1.1.1.1", 53),
)


class _Recorder:
    def __init__(self):
        self._lock = threading.Lock()
        self._samples = []  # (timestamp, seconds-or-None-for-failure)
        self._in_flight = None
        self._installed = False
        self._consecutive_failures = 0

    def record(self, seconds):
        with self._lock:
            if seconds is not None:
                self._consecutive_failures = 0
            self._samples.append((time.monotonic(), seconds))
            if len(self._samples) > _MAX_SAMPLES:
                self._samples = self._samples[-_MAX_SAMPLES:]

    def record_failure(self):
        with self._lock:
            self._consecutive_failures += 1
            self._samples.append((time.monotonic(), None))
            if len(self._samples) > _MAX_SAMPLES:
                self._samples = self._samples[-_MAX_SAMPLES:]

    def average(self):
        with self._lock:
            if not self._samples:
                return None
            if self._consecutive_failures >= _CONSECUTIVE_FAILURES_THRESHOLD:
                return None
            if self._samples[-1][1] is None:
                latencies = [s for _, s in self._samples if s is not None]
                if not latencies:
                    return None
                return sum(latencies) / len(latencies)
            latencies = [s for _, s in self._samples if s is not None]
            return sum(latencies) / len(latencies)

    def has_samples(self):
        with self._lock:
            return bool(self._samples)

    def begin(self):
        with self._lock:
            self._in_flight = time.monotonic()

    def end(self):
        with self._lock:
            self._in_flight = None

    def mark_installed(self):
        with self._lock:
            self._installed = True

    def is_installed(self):
        with self._lock:
            return self._installed


_recorder = _Recorder()

_conn_state = {"online": True, "failures": 0, "last_http_success": 0.0}


def record(seconds):
    """Record a successful request duration in seconds."""
    if seconds is not None:
        _conn_state["last_http_success"] = time.monotonic()
    _recorder.record(seconds)


def record_failure():
    """Record a failed request, which maps to the "no signal" state."""
    _recorder.record_failure()


def average():
    """Recent average latency in seconds, or ``None`` if unknown/failed."""
    return _recorder.average()


def has_samples():
    """True if at least one probe has completed (success or failure)."""
    return _recorder.has_samples()


def is_online():
    """Non-blocking check if the machine has internet connectivity.

    A successful HTTP request within the last ``_HTTP_SUCCESS_FRESH_SECS``
    is authoritative proof of connectivity (the socket check can miss
    proxy-only networks or filtered raw-DNS egress). Otherwise the cached
    result of the background socket loop (see ``_connectivity_loop``) is
    used. Safe to call from the UI thread on every tick.
    """
    if time.monotonic() - _conn_state["last_http_success"] < _HTTP_SUCCESS_FRESH_SECS:
        return True
    return _conn_state["online"]


def _socket_check():
    """Single TCP socket check against a set of fallback targets.

    Returns True if any target is reachable.
    """
    for host, port in _SOCKET_CHECK_TARGETS:
        try:
            sock = socket.create_connection(
                (host, port),
                timeout=_SOCKET_CHECK_TIMEOUT,
            )
            sock.close()
            return True
        except OSError:
            continue
    return False


def _connectivity_loop():
    """Background thread that checks connectivity every second.

    Uses debounce: only transitions to offline after
    ``_SOCKET_DEBOUNCE_FAILURES`` consecutive socket failures. Transitions
    to online on the first success (instant restore).
    """
    while True:
        reachable = _socket_check()
        if reachable:
            _conn_state["failures"] = 0
            _conn_state["online"] = True
        else:
            _conn_state["failures"] += 1
            if _conn_state["failures"] >= _SOCKET_DEBOUNCE_FAILURES:
                _conn_state["online"] = False
        time.sleep(_CONNECTIVITY_CHECK_INTERVAL)


def probe(url=_PROBE_URL, timeout=_PROBE_TIMEOUT):
    """Measure latency to a stable endpoint (blocking, runs in a thread).

    Goes through the patched ``urlopen``, so it records a success or failure
    sample automatically.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return
    req = urllib.request.Request(
        url, headers={"User-Agent": "NeoArch-signal-probe"}
    )
    try:
        from neoarch.backend.services.network import urlopen as _urlopen
        with _urlopen(req, timeout=timeout) as resp:
            resp.read(1)
    except Exception:
        pass


def start_probing(interval=30.0):
    """Probe the connection periodically on a daemon thread.

    Also starts the connectivity checker (socket-based, every 1s) so the
    signal indicator can react to sudden disconnections without waiting for
    the next probe cycle.

    Runs the first probe immediately, then once every ``interval`` seconds.
    """
    if os.environ.get("NEOARCH_TEST"):
        return

    def _probe_loop():
        while True:
            try:
                probe()
            except Exception:
                pass
            time.sleep(interval)

    threading.Thread(target=_probe_loop, daemon=True).start()
    threading.Thread(target=_connectivity_loop, daemon=True).start()


def install():
    """Wrap ``urllib.request.urlopen``, ``network.urlopen`` and ``requests.get`` once."""
    if _recorder.is_installed():
        return
    _recorder.mark_installed()

    _urlopen_original = urllib.request.urlopen

    def wrapped_urlopen(*args, **kwargs):
        _recorder.begin()
        start = time.monotonic()
        try:
            result = _urlopen_original(*args, **kwargs)
        except Exception:
            _recorder.record_failure()
            raise
        finally:
            _recorder.end()
        _recorder.record(time.monotonic() - start)
        return result

    urllib.request.urlopen = wrapped_urlopen

    try:
        from neoarch.backend.services.network import urlopen as _network_urlopen_original
    except ImportError:
        _network_urlopen_original = None

    if _network_urlopen_original is not None:

        def wrapped_network_urlopen(*args, **kwargs):
            _recorder.begin()
            start = time.monotonic()
            try:
                result = _network_urlopen_original(*args, **kwargs)
            except Exception:
                _recorder.record_failure()
                raise
            finally:
                _recorder.end()
            _recorder.record(time.monotonic() - start)
            return result

        import neoarch.backend.services.network as _network_mod

        _network_mod.urlopen = wrapped_network_urlopen

    try:
        import requests

        _requests_get_original = requests.get

        def wrapped_get(*args, **kwargs):
            _recorder.begin()
            start = time.monotonic()
            try:
                result = _requests_get_original(*args, **kwargs)
            except Exception:
                _recorder.record_failure()
                raise
            finally:
                _recorder.end()
            _recorder.record(time.monotonic() - start)
            return result

        requests.get = wrapped_get
    except ImportError:
        pass
