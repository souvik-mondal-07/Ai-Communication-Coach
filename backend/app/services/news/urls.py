"""URL canonicalisation and validation for article links and image URLs."""

from __future__ import annotations

import hashlib
import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.services.news.sources import NewsSource

MAX_URL_LENGTH = 2048
_TRACKING_PARAMS = {"fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ref", "ref_src", "spm", "cmpid", "ncid"}
_ID_RE = re.compile(r"^[a-f0-9]{24}$")


def _host_matches(host: str, domains: frozenset[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in domains)


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def _split_safely(url: object):
    """Parse a URL, or return None if it is not an acceptable absolute http(s) URL."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    if not url or len(url) > MAX_URL_LENGTH or any(ord(c) < 33 or ord(c) == 127 for c in url):
        return None  # whitespace / control characters never belong in a link
    try:
        parts = urlsplit(url)
        host = parts.hostname
        _ = parts.port  # raises on a malformed port
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not host:
        return None
    if parts.username is not None or parts.password is not None:
        return None  # credentials in a URL are a phishing tell
    if _is_ip_literal(host) or "." not in host:
        return None
    return parts


def canonicalize_url(url: object) -> str | None:
    """Normalised form used for de-duplication and as the stored link, or None if unacceptable."""
    parts = _split_safely(url)
    if parts is None:
        return None
    host = parts.hostname.lower().rstrip(".")  # type: ignore[union-attr]
    port = parts.port
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/") or "/"
    query = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    )
    scheme = "https" if parts.scheme == "http" else parts.scheme  # same article either way
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))


def safe_article_url(url: object, source: NewsSource) -> str | None:
    """Canonical article URL, only if it is on one of the source's own domains."""
    canonical = canonicalize_url(url)
    if canonical is None:
        return None
    host = urlsplit(canonical).hostname or ""
    return canonical if _host_matches(host, source.link_domains) else None


def safe_image_url(url: object) -> str | None:
    """https-only image URL without credentials; anything else is dropped."""
    canonical = canonicalize_url(url)
    if canonical is None or not canonical.startswith("https://"):
        return None
    return canonical


def article_id_for(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode()).hexdigest()[:24]


def is_valid_article_id(value: str) -> bool:
    return bool(_ID_RE.match(value))
