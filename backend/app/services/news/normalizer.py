"""Raw entries -> validated, normalised article documents. Anything not verifiable is dropped or left empty."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.news import NewsCategory
from app.services.news.classifier import classify
from app.services.news.parsers import RawEntry
from app.services.news.sources import NewsSource, SourceKind
from app.services.news.text import extract_cve_ids, to_plain_text
from app.services.news.urls import article_id_for, safe_article_url, safe_image_url

MAX_TITLE = 220
MAX_SUMMARY = 320
MAX_FUTURE_SKEW = timedelta(hours=1)


def _headline(entry: RawEntry, source: NewsSource) -> str | None:
    if source.kind is SourceKind.NVD_API:
        desc = to_plain_text(entry.summary, limit=140)
        return f"{entry.title}: {desc}" if desc and entry.title else entry.title
    return to_plain_text(entry.title, limit=MAX_TITLE)


def normalize_entry(entry: RawEntry, source: NewsSource, *, now: datetime, retention: timedelta) -> dict | None:
    """Return a storable article dict, or None if the entry is unusable (missing/unsafe/too old)."""
    title = _headline(entry, source)
    url = safe_article_url(entry.link, source)
    if not title or not url:
        return None

    published = entry.published
    if published is not None and published > now + MAX_FUTURE_SKEW:
        published = None  # a date in the future is not a trustworthy publication time
    if published is not None and published < now - retention:
        return None

    summary = to_plain_text(entry.summary, limit=MAX_SUMMARY)
    if summary and summary.lower() == title.lower():
        summary = None
    tags = [t for t in (to_plain_text(t, limit=60) for t in entry.tags[:20]) if t]
    # Only ids that literally appear in the source's own text (or came from NVD itself).
    cve_ids = entry.cve_ids or extract_cve_ids(title, summary, *tags)

    category = (
        NewsCategory.VULNERABILITIES if source.kind is SourceKind.NVD_API
        else classify(title, summary, tags, source.default_category)
    )
    image = safe_image_url(entry.image) if source.allow_images else None

    return {
        "article_id": article_id_for(url),
        "title": title,
        "summary": summary,
        "url": url,
        "source_id": source.id,
        "source_name": source.name,
        "category": category.value,
        "published_at": published.astimezone(timezone.utc).replace(tzinfo=None) if published else None,
        "image_url": image,
        "cve_ids": cve_ids,
        "severity": entry.severity.model_dump(mode="json") if entry.severity else None,
    }
