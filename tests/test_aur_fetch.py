"""Tests for AUR cgit plain-text fetching used by pre-install scans."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import neoarch.backend.services.aur_fetch as af
from neoarch.backend.services.aur_fetch import fetch_aur_pkgbuild


class FakeResp:
    """Minimal urllib response stand-in (context manager)."""

    def __init__(self, body=b"", status=200):
        self.body = body
        self.status = status
        self.read_args = []

    def read(self, n=-1):
        self.read_args.append(n)
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeNetwork:
    """Stand-in for the network service, recording requests."""

    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def urlopen(self, req, timeout=None):
        self.requests.append((req.full_url, timeout))
        return self.responses.pop(0)


def test_fetch_returns_pkgbuild_and_scriptlet(monkeypatch):
    net = FakeNetwork([FakeResp(b"pkgname=foo\n"), FakeResp(b"post()\n")])
    monkeypatch.setattr(af.network, "urlopen", net.urlopen)
    res = fetch_aur_pkgbuild("foo")
    assert res["name"] == "foo"
    assert res["pkgbuild"] == "pkgname=foo\n"
    assert res["scriptlets"] == {"foo.install": "post()\n"}
    urls = [u for u, _ in net.requests]
    assert "PKGBUILD?h=foo" in urls[0]
    assert "foo.install?h=foo" in urls[1]


def test_fetch_missing_scriptlet_is_ok(monkeypatch):
    net = FakeNetwork([FakeResp(b"pkgname=foo\n"), FakeResp(status=404)])
    monkeypatch.setattr(af.network, "urlopen", net.urlopen)
    res = fetch_aur_pkgbuild("foo")
    assert res["pkgbuild"] == "pkgname=foo\n"
    assert res["scriptlets"] == {}


def test_fetch_404_package_is_none(monkeypatch):
    net = FakeNetwork([FakeResp(status=404)])
    monkeypatch.setattr(af.network, "urlopen", net.urlopen)
    assert fetch_aur_pkgbuild("does-not-exist") is None


def test_fetch_network_error_is_none(monkeypatch):
    def boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(af.network, "urlopen", boom)
    assert fetch_aur_pkgbuild("foo") is None


def test_fetch_invalid_name(monkeypatch):
    called = []

    def spy(*a, **k):
        called.append(True)
        return FakeResp()

    monkeypatch.setattr(af.network, "urlopen", spy)
    for bad in ("..", "Bad Pkg", "", "; rm -rf /", "-foo"):
        assert fetch_aur_pkgbuild(bad) is None
    assert called == []


def test_fetch_quotes_weird_names(monkeypatch):
    net = FakeNetwork([FakeResp(status=404)])
    monkeypatch.setattr(af.network, "urlopen", net.urlopen)
    fetch_aur_pkgbuild("a+b_c-1")
    assert "PKGBUILD?h=a%2Bb_c-1" in net.requests[0][0]


def test_fetch_applies_read_cap(monkeypatch):
    pkg = FakeResp(b"x" * 10, 200)
    net = FakeNetwork([pkg, FakeResp(b"y", 200)])
    monkeypatch.setattr(af.network, "urlopen", net.urlopen)
    fetch_aur_pkgbuild("foo")
    assert pkg.read_args == [af._MAX_SCRIPTLET_BYTES]
