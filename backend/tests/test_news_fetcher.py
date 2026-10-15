"""Phase 22: SSRF, redirect, size, timeout and content-type controls of the news fetcher."""

from __future__ import annotations

import httpx
import pytest

from app.core.config import settings
from app.services.news import fetcher
from app.services.news.fetcher import FetchError, fetch_source_bytes, resolve_public_addresses, validate_url_for_source
from app.services.news.sources import all_sources, get_source

KREBS = get_source("krebs")
_REAL_RESOLVE = fetcher.resolve_public_addresses  # conftest swaps the module attribute for a blocker
FEED = b"<rss><channel><item><title>x</title></item></channel></rss>"


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def ok(body=FEED, ctype="application/rss+xml", **headers):
    return httpx.Response(200, content=body, headers={"content-type": ctype, **headers})


def fetch(handler, source=KREBS, **kw):
    return fetch_source_bytes(source, client=client_for(handler), check_dns=False, **kw)


def test_successful_fetch_returns_body_and_validators():
    result = fetch(lambda r: ok(etag='"abc"', **{"last-modified": "Wed, 14 Oct 2026 10:00:00 GMT"}))
    assert result.body == FEED and not result.truncated and result.etag == '"abc"'


def test_request_sends_identifying_user_agent_and_conditional_headers():
    seen = {}
    def handler(request):
        seen.update(request.headers)
        return httpx.Response(304)
    result = fetch(handler, etag='"abc"', last_modified="x")
    assert result.not_modified and seen["if-none-match"] == '"abc"' and "NewsReader" in seen["user-agent"]


# ---- only configured hosts, https only
@pytest.mark.parametrize("url", [
    "http://krebsonsecurity.com/feed/", "https://evil.example.com/feed", "https://krebsonsecurity.com.evil.example/feed",
    "https://127.0.0.1/feed", "https://169.254.169.254/latest/meta-data", "https://user:pw@krebsonsecurity.com/feed",
    "https://krebsonsecurity.com:8443/feed", "file:///etc/passwd", "gopher://krebsonsecurity.com/",
])
def test_urls_outside_the_source_are_refused_before_any_request(url):
    def handler(request):
        raise AssertionError("no request may be made")
    with pytest.raises(FetchError) as exc:
        fetch(handler, url=url)
    assert exc.value.code in {"blocked_url", "blocked_host"}


def test_every_registered_source_is_https_and_self_consistent():
    for s in all_sources():
        assert validate_url_for_source(s.feed_url, s) in s.allowed_hosts
        assert s.feed_url.startswith("https://") and s.link_domains and not s.allow_images


# ---- redirects
def test_redirect_to_another_host_is_blocked():
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://evil.example.com/steal"})
    with pytest.raises(FetchError) as exc:
        fetch(handler)
    assert exc.value.code == "blocked_host" and calls == [KREBS.feed_url]


def test_redirect_to_internal_address_is_blocked():
    def handler(request):
        return httpx.Response(307, headers={"location": "https://169.254.169.254/latest/meta-data/"})
    with pytest.raises(FetchError) as exc:
        fetch(handler)
    assert exc.value.code in {"blocked_host", "blocked_url"}


def test_redirect_downgrade_to_http_is_blocked():
    def handler(request):
        return httpx.Response(301, headers={"location": "http://krebsonsecurity.com/feed/"})
    with pytest.raises(FetchError) as exc:
        fetch(handler)
    assert exc.value.code == "blocked_url"


def test_same_host_redirect_is_followed_and_loops_are_capped():
    state = {"n": 0}
    def follow(request):
        state["n"] += 1
        return httpx.Response(301, headers={"location": "/feed2/"}) if state["n"] == 1 else ok()
    assert fetch(follow).body == FEED
    with pytest.raises(FetchError) as exc:
        fetch(lambda r: httpx.Response(302, headers={"location": "/again"}))
    assert exc.value.code == "too_many_redirects"
    with pytest.raises(FetchError) as exc:
        fetch(lambda r: httpx.Response(302))
    assert exc.value.code == "bad_redirect"


# ---- DNS / private address blocking
@pytest.mark.parametrize("addr", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "172.16.0.9", "169.254.169.254", "::1", "fe80::1", "fc00::1", "::ffff:127.0.0.1", "0.0.0.0", "224.0.0.1"])
def test_private_and_reserved_addresses_are_blocked(monkeypatch, addr):
    monkeypatch.setattr(fetcher.socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", (addr, 443))])
    with pytest.raises(FetchError) as exc:
        resolve_public_addresses("krebsonsecurity.com")
    assert exc.value.code == "blocked_address"


def test_one_private_answer_among_public_ones_blocks_the_host(monkeypatch):
    monkeypatch.setattr(fetcher.socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("93.184.216.34", 443)), (0, 0, 0, "", ("10.0.0.1", 443))])
    with pytest.raises(FetchError):
        resolve_public_addresses("krebsonsecurity.com")


def test_public_address_passes_and_dns_failure_is_clean(monkeypatch):
    monkeypatch.setattr(fetcher.socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("93.184.216.34", 443))])
    assert resolve_public_addresses("krebsonsecurity.com") == ["93.184.216.34"]
    def boom(*a, **k):
        raise OSError("nxdomain")
    monkeypatch.setattr(fetcher.socket, "getaddrinfo", boom)
    with pytest.raises(FetchError) as exc:
        resolve_public_addresses("krebsonsecurity.com")
    assert exc.value.code == "dns_error"


def test_dns_check_runs_before_the_request(monkeypatch):
    monkeypatch.setattr(fetcher, "resolve_public_addresses", _REAL_RESOLVE)
    monkeypatch.setattr(fetcher.socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("10.0.0.1", 443))])
    def handler(request):
        raise AssertionError("must not connect to a private address")
    with pytest.raises(FetchError) as exc:
        fetch_source_bytes(KREBS, client=client_for(handler), check_dns=True)
    assert exc.value.code == "blocked_address"


# ---- size, status, type, timeout
def test_oversized_download_is_truncated_at_the_cap(monkeypatch):
    monkeypatch.setattr(settings, "news_max_feed_bytes", 1000)
    result = fetch(lambda r: ok(b"x" * 50_000))
    assert result.truncated and len(result.body) == 1000


def test_oversized_nvd_json_is_an_error_not_a_truncated_parse(monkeypatch):
    monkeypatch.setattr(settings, "news_max_feed_bytes", 100)
    with pytest.raises(FetchError) as exc:
        fetch(lambda r: ok(b"{" + b" " * 5000, "application/json"), source=get_source("nvd"))
    assert exc.value.code == "too_large"


@pytest.mark.parametrize("status,code", [(429, "rate_limited"), (403, "http_403"), (404, "http_404"), (500, "http_500"), (503, "http_503")])
def test_http_errors_map_to_coarse_codes(status, code):
    with pytest.raises(FetchError) as exc:
        fetch(lambda r: httpx.Response(status))
    assert exc.value.code == code


def test_html_and_binary_content_types_are_refused():
    for ctype in ("text/html", "application/octet-stream", "image/png"):
        with pytest.raises(FetchError) as exc:
            fetch(lambda r, c=ctype: ok(b"<html>", c))
        assert exc.value.code == "bad_content_type"


def test_timeouts_and_network_errors_become_clean_codes():
    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)
    with pytest.raises(FetchError) as exc:
        fetch(slow)
    assert exc.value.code == "timeout"
    def down(request):
        raise httpx.ConnectError("refused", request=request)
    with pytest.raises(FetchError) as exc:
        fetch(down)
    assert exc.value.code == "network_error"


def test_slow_drip_response_hits_the_overall_deadline(monkeypatch):
    ticks = iter(range(0, 10_000, 100))  # each monotonic() call jumps 100s
    monkeypatch.setattr(fetcher.time, "monotonic", lambda: next(ticks))
    def drip(request):
        return httpx.Response(200, headers={"content-type": "application/xml"}, stream=httpx.ByteStream(b"abc" * 10))
    with pytest.raises(FetchError) as exc:
        fetch(drip)
    assert exc.value.code == "timeout"


def test_nvd_api_key_goes_in_a_header_only(monkeypatch):
    monkeypatch.setattr(settings, "nvd_api_key", "SECRET-KEY")
    seen = {}
    def handler(request):
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        return ok(b"{}", "application/json")
    fetch(handler, source=get_source("nvd"))
    assert seen["headers"]["apikey"] == "SECRET-KEY" and "SECRET" not in seen["url"]
    fetch(handler, source=KREBS)
    assert "apikey" not in seen["headers"]  # never sent to non-NVD hosts
