"""
SSRF-hardened, size-capped HTTP fetching for the configured news sources.

Controls (each is covered by a test):
  * Takes a ``NewsSource`` -- there is no code path from a request or a feed to a fetched URL.
  * https only; the host must be in the source's ``allowed_hosts``.
  * Redirects are followed manually (max 3), and every hop is re-checked against the same rules,
    so a feed cannot bounce the server to an internal address.
  * The host is resolved before connecting and refused if *any* answer is private, loopback,
    link-local, reserved or multicast.
  * Explicit connect/read timeouts, and the body is streamed with a hard byte ceiling.
  * Only text-ish content types are accepted; credentials are never forwarded across hosts.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.config import settings
from app.services.news.sources import NewsSource
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_REDIRECTS = 3
USER_AGENT = "AI-CyberSec-Mentor-NewsReader/1.0 (+student learning project; headline and link aggregation only)"
_OK_TYPES = ("xml", "json", "text/plain", "atom", "rss")


class FetchError(Exception):
    """A fetch failed. ``code`` is a coarse, safe-to-publish reason (never a raw exception message)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class FetchResult:
    body: bytes
    truncated: bool
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False


def _is_public_ip(raw: str) -> bool:
    try:
        ip = ipaddress.ip_address(raw.split("%")[0])
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped  # type: ignore[assignment]
    return ip.is_global and not ip.is_multicast


def resolve_public_addresses(host: str) -> list[str]:
    """Resolve ``host``; raise FetchError unless it resolves and *every* address is public."""
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise FetchError("dns_error") from exc
    addresses = sorted({info[4][0] for info in infos})
    if not addresses or not all(_is_public_ip(a) for a in addresses):
        raise FetchError("blocked_address")
    return addresses


def validate_url_for_source(url: str, source: NewsSource) -> str:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host or parts.username or parts.password:
        raise FetchError("blocked_url")
    if host not in source.allowed_hosts:
        raise FetchError("blocked_host")
    try:
        if parts.port not in (None, 443):
            raise FetchError("blocked_url")
    except ValueError as exc:
        raise FetchError("blocked_url") from exc
    return host


def _build_headers(source: NewsSource, *, etag: str | None, last_modified: str | None) -> dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json" if source.kind.value == "nvd-api" else "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8",
        "Accept-Encoding": "gzip",
    }
    if source.kind.value == "nvd-api" and settings.nvd_api_key:
        headers["apiKey"] = settings.nvd_api_key  # header only; never logged or put in a URL
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return headers


def fetch_source_bytes(
    source: NewsSource,
    url: str | None = None,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    client: httpx.Client | None = None,
    check_dns: bool = True,
) -> FetchResult:
    """
    Download ``url`` (default: the source's feed URL) under the controls described above.

    ``client`` and ``check_dns`` exist so tests can inject a mock transport; production callers
    use the defaults.
    """
    current = url or source.feed_url
    max_bytes = settings.news_max_feed_bytes
    timeout = httpx.Timeout(settings.news_fetch_timeout_seconds, connect=min(5.0, settings.news_fetch_timeout_seconds))
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=False)
    try:
        for _hop in range(MAX_REDIRECTS + 1):
            host = validate_url_for_source(current, source)
            if check_dns:
                resolve_public_addresses(host)
            headers = _build_headers(source, etag=etag, last_modified=last_modified)
            try:
                with http.stream("GET", current, headers=headers, timeout=timeout) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError("bad_redirect")
                        current = urljoin(current, location)
                        continue
                    if response.status_code == 304:
                        return FetchResult(b"", False, etag, last_modified, not_modified=True)
                    if response.status_code == 429:
                        raise FetchError("rate_limited")
                    if response.status_code >= 400:
                        raise FetchError(f"http_{response.status_code}")
                    ctype = response.headers.get("content-type", "").lower()
                    if ctype and not any(t in ctype for t in _OK_TYPES):
                        raise FetchError("bad_content_type")
                    deadline = time.monotonic() + settings.news_fetch_timeout_seconds * 3
                    chunks: list[bytes] = []
                    size = 0
                    truncated = False
                    for chunk in response.iter_bytes():
                        if time.monotonic() > deadline:
                            raise FetchError("timeout")  # slow-drip server: per-read timeouts never fire
                        size += len(chunk)
                        if size > max_bytes:
                            keep = len(chunk) - (size - max_bytes)
                            chunks.append(chunk[:keep])
                            truncated = True
                            break
                        chunks.append(chunk)
                    if truncated and source.kind.value == "nvd-api":
                        raise FetchError("too_large")  # truncated JSON is unusable
                    return FetchResult(
                        b"".join(chunks), truncated,
                        response.headers.get("etag"), response.headers.get("last-modified"),
                    )
            except httpx.TimeoutException as exc:
                raise FetchError("timeout") from exc
            except httpx.HTTPError as exc:
                raise FetchError("network_error") from exc
        raise FetchError("too_many_redirects")
    finally:
        if owns_client:
            http.close()
