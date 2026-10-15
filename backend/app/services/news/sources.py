"""
The fixed list of news sources.

This list is the *only* place a URL can come from. The fetcher takes a ``NewsSource`` (never a
URL string), refuses any host that is not in ``allowed_hosts`` -- including after redirects --
and article links are only accepted when they sit on one of the source's ``link_domains``.
Nothing in an HTTP request, a feed entry or an environment variable can add to it.

Verification status (see docs/PHASE22_PUBLIC_NEWS.md for how each was checked):
  * Feed/endpoint URLs were confirmed to exist from public documentation or feed directories;
    Krebs's feed was additionally fetched live while developing the parser.
  * Run ``python -m app.services.news.check_sources`` on a machine with internet access to
    check every source against its live endpoint.

Images: ``allow_images`` is False for every source. Hotlinking a publisher's image is a
licensing decision that has not been reviewed per source, so the image pipeline exists and is
tested but stays off until a source is explicitly reviewed and switched on here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.core.config import settings
from app.schemas.news import NewsCategory


class SourceKind(StrEnum):
    RSS = "rss"
    ATOM = "atom"
    NVD_API = "nvd-api"


@dataclass(frozen=True)
class NewsSource:
    id: str
    name: str
    homepage_url: str
    kind: SourceKind
    # Feed / API endpoint. Must be https.
    feed_url: str
    # Hosts the fetcher may talk to for this source (the feed host plus known redirect targets).
    allowed_hosts: frozenset[str]
    # Article links must be on one of these domains (the host itself or a subdomain).
    link_domains: frozenset[str]
    # Used when the classifier finds nothing more specific.
    default_category: NewsCategory = NewsCategory.GENERAL
    # Cap on entries kept per refresh (feeds with huge history).
    max_items: int = 40
    allow_images: bool = False
    # Extra hints the classifier trusts for this source.
    notes: str = ""
    extra: dict[str, str] = field(default_factory=dict)


NVD_ENDPOINT = "https://services.nvd.nist.gov/rest/json/cves/2.0"

_ALL_SOURCES: tuple[NewsSource, ...] = (
    NewsSource(
        id="cisa",
        name="CISA Alerts & Advisories",
        homepage_url="https://www.cisa.gov/news-events/cybersecurity-advisories",
        kind=SourceKind.RSS,
        feed_url="https://www.cisa.gov/cybersecurity-advisories/all.xml",
        allowed_hosts=frozenset({"www.cisa.gov", "cisa.gov"}),
        link_domains=frozenset({"cisa.gov"}),
        default_category=NewsCategory.VULNERABILITIES,
        notes="US government source; every entry is an official alert, advisory or bulletin.",
    ),
    NewsSource(
        id="nvd",
        name="NIST National Vulnerability Database",
        homepage_url="https://nvd.nist.gov/",
        kind=SourceKind.NVD_API,
        feed_url=NVD_ENDPOINT,
        allowed_hosts=frozenset({"services.nvd.nist.gov"}),
        link_domains=frozenset({"nvd.nist.gov"}),
        default_category=NewsCategory.VULNERABILITIES,
        max_items=40,
        notes="Critical-severity CVEs published in the last 7 days.",
    ),
    NewsSource(
        id="ncsc-uk",
        name="UK NCSC",
        homepage_url="https://www.ncsc.gov.uk/",
        kind=SourceKind.RSS,
        feed_url="https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml",
        allowed_hosts=frozenset({"www.ncsc.gov.uk", "ncsc.gov.uk"}),
        link_domains=frozenset({"ncsc.gov.uk"}),
        max_items=30,
    ),
    NewsSource(
        id="krebs",
        name="Krebs on Security",
        homepage_url="https://krebsonsecurity.com/",
        kind=SourceKind.RSS,
        feed_url="https://krebsonsecurity.com/feed/",
        allowed_hosts=frozenset({"krebsonsecurity.com", "www.krebsonsecurity.com"}),
        link_domains=frozenset({"krebsonsecurity.com"}),
        max_items=25,
    ),
    NewsSource(
        id="bleepingcomputer",
        name="BleepingComputer",
        homepage_url="https://www.bleepingcomputer.com/",
        kind=SourceKind.RSS,
        feed_url="https://www.bleepingcomputer.com/feed/",
        allowed_hosts=frozenset({"www.bleepingcomputer.com", "bleepingcomputer.com"}),
        link_domains=frozenset({"bleepingcomputer.com"}),
    ),
    NewsSource(
        id="securityweek",
        name="SecurityWeek",
        homepage_url="https://www.securityweek.com/",
        kind=SourceKind.RSS,
        feed_url="https://www.securityweek.com/feed/",
        allowed_hosts=frozenset({"www.securityweek.com", "securityweek.com"}),
        link_domains=frozenset({"securityweek.com"}),
    ),
    NewsSource(
        id="schneier",
        name="Schneier on Security",
        homepage_url="https://www.schneier.com/",
        kind=SourceKind.ATOM,
        feed_url="https://www.schneier.com/blog/atom.xml",
        allowed_hosts=frozenset({"www.schneier.com", "schneier.com"}),
        link_domains=frozenset({"schneier.com"}),
        default_category=NewsCategory.TOOLS_RESEARCH,
        max_items=25,
    ),
    NewsSource(
        id="project-zero",
        name="Google Project Zero",
        homepage_url="https://projectzero.google/",
        kind=SourceKind.ATOM,
        feed_url="https://projectzero.google/feed.xml",
        allowed_hosts=frozenset({"projectzero.google"}),
        link_domains=frozenset({"projectzero.google"}),
        default_category=NewsCategory.TOOLS_RESEARCH,
        max_items=20,
    ),
)


def all_sources() -> tuple[NewsSource, ...]:
    return _ALL_SOURCES


def enabled_sources() -> tuple[NewsSource, ...]:
    disabled = settings.news_disabled_sources_set
    return tuple(s for s in _ALL_SOURCES if s.id not in disabled)


def get_source(source_id: str) -> NewsSource | None:
    return next((s for s in _ALL_SOURCES if s.id == source_id), None)
