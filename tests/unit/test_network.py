"""Tests for the network settings service (proxy fallback, opener, env)."""

import urllib.request

import pytest

from neoarch.backend.services import network


@pytest.fixture(autouse=True)
def _clean_proxy_health():
    network._proxy_health.update(url=None, ok=True, checked=0.0)
    yield


def _cfg(proxy_type="http", host="127.0.0.1", port=1, verify_ssl=True):
    return {
        "type": proxy_type,
        "host": host,
        "port": port,
        "verify_ssl": verify_ssl,
        "timeout": 5,
    }


def test_proxy_reachable_returns_false_for_closed_port():
    assert network._proxy_reachable("http://127.0.0.1:1/") is False


def test_proxy_reachable_cached_result_is_reused():
    assert network._proxy_reachable("http://127.0.0.1:1/") is False
    assert network._proxy_reachable("http://127.0.0.1:1/") is False


def test_build_opener_falls_back_to_direct_when_proxy_dead():
    opener = network.build_opener(_cfg())
    assert not any(isinstance(h, urllib.request.ProxyHandler) for h in opener.handlers)


def test_build_opener_keeps_proxy_handler_when_proxy_live():
    import socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    try:
        port = server.getsockname()[1]
        opener = network.build_opener(_cfg(port=port))
    finally:
        server.close()
    assert any(isinstance(h, urllib.request.ProxyHandler) for h in opener.handlers)


def test_apply_network_env_clears_proxy_env_when_proxy_dead():
    env = network.apply_network_env(dict(http_proxy="keep", HTTP_PROXY="keep"))
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        assert env.get(key) is None