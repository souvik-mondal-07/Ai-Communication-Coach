"""
Feed parsing: RSS 2.0, Atom 1.0 and the NVD CVE API 2.0 JSON.

Parsers only *extract* fields. They never raise on one bad entry (that entry is skipped) and
they deliberately ignore full-article body fields (``content:encoded``, Atom ``content``): the
service republishes headline + the source's own short excerpt + a link, never the article.

XML safety: feeds do not need a DTD, so any document containing a DOCTYPE or ENTITY declaration
is rejected before parsing. That removes XXE and entity-expansion attacks by construction
without adding a dependency. Size is bounded by the fetcher.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from app.schemas.news import ArticleSeverity, SeverityLevel


class FeedParseError(Exception):
    pass


@dataclass
class RawEntry:
    title: str | None
    link: str | None
    summary: str | None = None
    published: datetime | None = None
    tags: list[str] = field(default_factory=list)
    image: str | None = None
    guid: str | None = None
    cve_ids: list[str] = field(default_factory=list)  # only the NVD parser fills this directly
    severity: ArticleSeverity | None = None


def _local(tag: object) -> str:
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def parse_datetime(value: object) -> datetime | None:
    """RFC 822 or ISO 8601 -> aware UTC datetime, else None (never a guess)."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    parsed: datetime | None = None
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


_DOCTYPE_RE = re.compile(rb"<!\s*(doctype|entity)", re.IGNORECASE)


def _repair_truncated(body: bytes) -> bytes:
    """A download cut at the size cap: keep every complete entry and close the document."""
    lowered = body.lower()
    is_atom = b"<feed" in lowered[:2000]
    marker = b"</entry>" if is_atom else b"</item>"
    idx = lowered.rfind(marker)
    if idx == -1:
        raise FeedParseError("truncated_no_entries")
    return body[: idx + len(marker)] + (b"</feed>" if is_atom else b"</channel></rss>")


def parse_feed(body: bytes, *, truncated: bool = False) -> list[RawEntry]:
    if not body or not body.strip():
        raise FeedParseError("empty")
    if _DOCTYPE_RE.search(body):
        raise FeedParseError("dtd_not_allowed")
    if truncated:
        body = _repair_truncated(body)
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise FeedParseError("malformed_xml") from exc
    kind = _local(root.tag)
    if kind == "feed":
        return [e for e in (_atom_entry(el) for el in root if _local(el.tag) == "entry") if e]
    if kind in ("rss", "rdf"):
        items = [el for el in root.iter() if _local(el.tag) == "item"]
        return [e for e in (_rss_item(el) for el in items) if e]
    raise FeedParseError("not_a_feed")


def _text(el: ET.Element | None) -> str | None:
    return el.text.strip() if el is not None and el.text and el.text.strip() else None


def _children(el: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in el if _local(c.tag) == name]


def _rss_item(el: ET.Element) -> RawEntry | None:
    try:
        first = lambda n: next(iter(_children(el, n)), None)  # noqa: E731
        link = _text(first("link"))
        guid_el = first("guid")
        guid = _text(guid_el)
        if not link and guid and guid_el is not None and guid_el.get("ispermalink", "true").lower() != "false":
            link = guid
        image = None
        for c in el:
            name = _local(c.tag)
            if name in ("thumbnail", "content") and c.get("url") and (c.get("medium", "image") == "image"):
                image = image or c.get("url")
            elif name == "enclosure" and (c.get("type") or "").startswith("image/"):
                image = image or c.get("url")
        return RawEntry(
            title=_text(first("title")),
            link=link,
            summary=_text(first("description")),  # NOT content:encoded
            published=parse_datetime(_text(first("pubdate")) or _text(first("date"))),
            tags=[t for t in (_text(c) for c in _children(el, "category")) if t],
            image=image,
            guid=guid,
        )
    except Exception:  # noqa: BLE001 - one malformed entry must not sink the feed
        return None


def _atom_entry(el: ET.Element) -> RawEntry | None:
    try:
        link = None
        for c in _children(el, "link"):
            if c.get("rel", "alternate") == "alternate" and c.get("href"):
                link = c.get("href")
                break
        first = lambda n: next(iter(_children(el, n)), None)  # noqa: E731
        title_el = first("title")
        title = "".join(title_el.itertext()).strip() if title_el is not None else None
        summary_el = first("summary")  # NOT <content>
        summary = "".join(summary_el.itertext()).strip() if summary_el is not None else None
        image = None
        for c in el:
            if _local(c.tag) in ("thumbnail", "content") and c.get("url") and c.get("medium", "image") == "image":
                image = c.get("url")
        return RawEntry(
            title=title or None,
            link=link,
            summary=summary or None,
            published=parse_datetime(_text(first("published")) or _text(first("updated"))),
            tags=[c.get("term") for c in _children(el, "category") if c.get("term")],
            image=image,
            guid=_text(first("id")),
        )
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------- NVD
_SEVERITIES = {"LOW": SeverityLevel.LOW, "MEDIUM": SeverityLevel.MEDIUM, "HIGH": SeverityLevel.HIGH, "CRITICAL": SeverityLevel.CRITICAL}
_CVE_ID_RE = re.compile(r"^CVE-\d{4}-\d{4,7}$")
_METRIC_KEYS = (("cvssMetricV40", "CVSS v4.0"), ("cvssMetricV31", "CVSS v3.1"), ("cvssMetricV30", "CVSS v3.0"))


def _nvd_severity(metrics: object) -> ArticleSeverity | None:
    if not isinstance(metrics, dict):
        return None
    for key, scheme in _METRIC_KEYS:
        entries = metrics.get(key)
        if not isinstance(entries, list) or not entries:
            continue
        ordered = sorted((e for e in entries if isinstance(e, dict)), key=lambda e: e.get("type") != "Primary")
        for entry in ordered:
            data = entry.get("cvssData") or {}
            level = _SEVERITIES.get(str(data.get("baseSeverity") or entry.get("baseSeverity") or "").upper())
            score = data.get("baseScore")
            if level is None:
                continue
            valid = isinstance(score, (int, float)) and not isinstance(score, bool) and 0 <= score <= 10
            return ArticleSeverity(level=level, score=float(score) if valid else None, scheme=scheme, assigned_by="NVD")
    return None


def parse_nvd(body: bytes) -> list[RawEntry]:
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise FeedParseError("malformed_json") from exc
    vulns = payload.get("vulnerabilities") if isinstance(payload, dict) else None
    if not isinstance(vulns, list):
        raise FeedParseError("unexpected_shape")
    entries: list[RawEntry] = []
    for item in vulns:
        try:
            cve = item["cve"]
            cve_id = str(cve["id"]).upper()
            if not _CVE_ID_RE.match(cve_id) or str(cve.get("vulnStatus", "")).lower().startswith("reject"):
                continue
            desc = next((d.get("value") for d in cve.get("descriptions", []) if d.get("lang") == "en"), None)
            entries.append(RawEntry(
                title=cve_id,  # normalizer builds the headline from id + description
                link=f"https://nvd.nist.gov/vuln/detail/{cve_id}",  # built by us from a validated id
                summary=desc,
                published=parse_datetime(cve.get("published")),
                guid=cve_id,
                cve_ids=[cve_id],
                severity=_nvd_severity(cve.get("metrics")),
            ))
        except (KeyError, TypeError, AttributeError):
            continue
    return entries
