"""Tests for the network latency recorder and the signal indicator states."""

import http.server
import threading

import pytest

from neoarch.backend.services import network_latency
from neoarch.frontend.components.signal_indicator import _state_for, _fmt


@pytest.fixture(autouse=True)
def _clean_recorder():
    network_latency._recorder._samples = []
    network_latency._recorder._consecutive_failures = 0
    network_latency._online = True
    network_latency._socket_failures = 0
    yield
    network_latency._recorder._samples = []
    network_latency._recorder._consecutive_failures = 0
    network_latency._online = True
    network_latency._socket_failures = 0


def test_average_rolling_window():
    network_latency.record(0.2)
    network_latency.record(0.4)
    assert network_latency.average() == pytest.approx(0.3)


def test_average_keeps_last_n_samples():
    for _ in range(15):
        network_latency.record(0.2)
    assert len(network_latency._recorder._samples) == network_latency._MAX_SAMPLES
    assert network_latency.average() == pytest.approx(0.2)


def test_single_failure_keeps_previous_signal():
    network_latency.record(0.1)
    network_latency.record_failure()
    assert network_latency.average() == pytest.approx(0.1)


def test_consecutive_failures_map_to_no_signal():
    network_latency.record(0.1)
    network_latency.record(0.1)
    network_latency.record_failure()
    network_latency.record_failure()
    assert network_latency.average() is None


def test_install_patches_urlopen_and_records_latency():
    if network_latency._recorder._installed:
        pytest.skip("already installed by app import")
    network_latency.install()

    server = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=5).read()
    finally:
        server.shutdown()
        thread.join()

    avg = network_latency.average()
    assert avg is not None
    assert avg < 5.0


def test_probe_records_success_and_failure():
    if not network_latency._recorder._installed:
        network_latency.install()

    server = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        network_latency.probe(f"http://127.0.0.1:{server.server_port}/", timeout=5)
        assert network_latency.average() is not None
        assert network_latency.average() < 5.0
    finally:
        server.shutdown()
        thread.join()

    network_latency.probe("http://127.0.0.1:1/", timeout=2)
    network_latency.probe("http://127.0.0.1:1/", timeout=2)  # 2nd consecutive failure
    assert network_latency.average() is None


def test_state_mapping():
    assert _state_for(None) == "nosignal"
    assert _state_for(0.1) == "high"
    assert _state_for(0.5) == "medium"
    assert _state_for(1.0) == "low"
    assert _state_for(2.1) == "low"


def test_format_seconds():
    assert _fmt(0.42) == "420 ms"
    assert _fmt(1.25) == "1.2 s"
    assert _fmt(None) == ""
