"""Lightweight network latency measurement.

Records latency for HTTP requests made through ``urllib.request.urlopen`` and
``requests.get`` (patched by ``install()``), and periodically probes a stable
endpoint (``start_probing()``) so the signal indicator reflects the real
connection even while the app is idle. A failed request is recorded as a
failure, which maps to the "no signal" state.

``install()`` is idempotent and safe to call more than once.
"""

import os
import threading
import time
import urllib.request

_MAX_SAMPLES = 10
_PROBE_URL = "https://archlinux.org/"
_PROBE_TIMEOUT = 5.0


class _Recorder:
    def __init__(self):
        self._lock = threading.Lock()
        self._samples = []  # (timestamp, seconds-or-None-for-failure)
        self._in_flight = None
        self._installed = False

    def record(self, seconds):
        with self._lock:
            self._samples.append((time.monotonic(), seconds))
            if len(self._samples) > _MAX_SAMPLES:
                self._samples = self._samples[-_MAX_SAMPLES:]

    def record_failure(self):
        self.record(None)

    def average(self):
        with self._lock:
            latencies = [s for _, s in self._samples if s is not None]
            if not latencies:
                return None
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

    def in_flight_elapsed(self):
        with self._lock:
            if self._in_flight is None:
                return None
            return time.monotonic() - self._in_flight


_recorder = _Recorder()


def record(seconds):
    """Record a successful request duration in seconds."""
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


def begin():
    """Mark the start of an in-flight request."""
    _recorder.begin()


def end():
    """Mark the end of an in-flight request."""
    _recorder.end()


def in_flight_elapsed():
    """Seconds since the current in-flight request started, or ``None``."""
    return _recorder.in_flight_elapsed()


def probe(url=_PROBE_URL, timeout=_PROBE_TIMEOUT):
    """Measure latency to a stable endpoint (blocking, runs in a thread).

    Goes through the patched ``urlopen``, so it records a success or failure
    sample automatically.
    """
    req = urllib.request.Request(
        url, headers={"User-Agent": "NeoArch-signal-probe"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(1)
    except Exception:
        pass


def start_probing(interval=30.0):
    """Probe the connection periodically on a daemon thread.

    Runs the first probe immediately, then once every ``interval`` seconds.
    """
    if os.environ.get("NEOARCH_TEST"):
        return

    def _loop():
        while True:
            try:
                probe()
            except Exception:
                pass
            time.sleep(interval)

    threading.Thread(target=_loop, daemon=True).start()


def install():
    """Wrap ``urllib.request.urlopen`` and ``requests.get`` once."""
    if _recorder._installed:
        return
    _recorder._installed = True

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
