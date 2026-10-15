"""
Response/query schemas for the public cybersecurity news feed (Phase 22).

Nothing here describes user data: the news endpoints are public and read-only. Optional
fields are ``None`` when the source did not supply them -- they are never filled with a
guess.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class NewsCategory(StrEnum):
    VULNERABILITIES = "vulnerabilities"
    BREACHES = "breaches"
    MALWARE = "malware"
    AI_SECURITY = "ai-security"
    APPSEC = "appsec"
    CLOUD_NETWORK = "cloud-network"
    BUG_BOUNTY = "bug-bounty"
    TOOLS_RESEARCH = "tools-research"
    CAREERS = "careers"
    GENERAL = "general"


# Display metadata. Order matters: it is the order of the category navigation.
CATEGORY_INFO: dict[NewsCategory, tuple[str, str]] = {
    NewsCategory.VULNERABILITIES: ("Vulnerabilities & CVEs", "Newly disclosed flaws, patches and advisories."),
    NewsCategory.BREACHES: ("Breaches & incidents", "Data breaches, leaks and reported attacks."),
    NewsCategory.MALWARE: ("Malware & ransomware", "Malware families, ransomware and threat actors."),
    NewsCategory.AI_SECURITY: ("AI security", "Security of AI systems, and AI used in attacks."),
    NewsCategory.APPSEC: ("Application & web security", "Web, API and software supply-chain security."),
    NewsCategory.CLOUD_NETWORK: ("Cloud & network security", "Cloud, identity, network and infrastructure security."),
    NewsCategory.BUG_BOUNTY: ("Bug bounty & ethical hacking", "Responsible disclosure, bounties and pentesting."),
    NewsCategory.TOOLS_RESEARCH: ("Security tools & research", "Open-source tools, papers and research write-ups."),
    NewsCategory.CAREERS: ("Careers & skills", "Hiring, workforce and training news."),
    NewsCategory.GENERAL: ("General security news", "Everything else from the configured sources."),
}


class SeverityLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ArticleSeverity(BaseModel):
    """A severity that a source actually published (today: NVD CVSS only)."""

    level: SeverityLevel
    score: float | None = Field(default=None, ge=0, le=10)
    scheme: str = Field(description="Scoring scheme as published, e.g. 'CVSS v3.1'.")
    assigned_by: str = Field(description="Who published the score, e.g. 'NVD'.")


class NewsArticle(BaseModel):
    id: str = Field(description="Stable id derived from the canonical article URL.")
    title: str
    summary: str | None = Field(default=None, description="The source's own excerpt, as plain text.")
    url: str = Field(description="Original article URL (always on the source's own domain).")
    source_id: str
    source_name: str
    category: NewsCategory
    published_at: datetime | None = Field(default=None, description="When the source says it was published.")
    first_seen_at: datetime = Field(description="When this service first retrieved it. Not a publication date.")
    image_url: str | None = None
    cve_ids: list[str] = Field(default_factory=list)
    severity: ArticleSeverity | None = None


class SourceStatus(StrEnum):
    OK = "ok"
    FAILED = "failed"
    PENDING = "pending"  # never attempted yet
    DISABLED = "disabled"


class SourceInfo(BaseModel):
    id: str
    name: str
    homepage_url: str
    kind: str = Field(description="How it is fetched: 'rss', 'atom' or 'nvd-api'.")
    status: SourceStatus
    last_success_at: datetime | None = None
    last_error: str | None = Field(default=None, description="Coarse reason code only, e.g. 'timeout'.")
    article_count: int = 0


class FreshnessState(StrEnum):
    FRESH = "fresh"
    STALE = "stale"  # cache older than the refresh interval (refresh may be running)
    DEGRADED = "degraded"  # recent refresh failed for some or all sources
    EMPTY = "empty"  # nothing cached yet


class Freshness(BaseModel):
    state: FreshnessState
    last_successful_refresh_at: datetime | None = None
    last_attempt_at: datetime | None = None
    refreshing: bool = False
    refresh_interval_minutes: int
    sources_ok: int = 0
    sources_failed: int = 0
    message: str | None = None


class NewsListResponse(BaseModel):
    items: list[NewsArticle]
    total: int
    page: int
    limit: int
    has_more: bool
    freshness: Freshness


class CategoryCount(BaseModel):
    id: NewsCategory
    label: str
    description: str
    count: int


class CategoriesResponse(BaseModel):
    categories: list[CategoryCount]
    total: int
