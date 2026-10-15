"""Phase 22: feed parsing, sanitising, URL safety, classification and normalisation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.news import NewsCategory, SeverityLevel
from app.services.news.classifier import classify
from app.services.news.normalizer import normalize_entry
from app.services.news.parsers import FeedParseError, RawEntry, parse_datetime, parse_feed, parse_nvd
from app.services.news.sources import NewsSource, SourceKind, get_source
from app.services.news.text import extract_cve_ids, to_plain_text
from app.services.news.urls import article_id_for, canonicalize_url, is_valid_article_id, safe_article_url, safe_image_url

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
RETENTION = timedelta(days=45)
KREBS = get_source("krebs")


def rss(items: str) -> bytes:
    return f'<?xml version="1.0"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:media="http://search.yahoo.com/mrss/"><channel>{items}</channel></rss>'.encode()


# ------------------------------------------------------------------ RSS / Atom
def test_rss_extracts_fields_and_ignores_full_content_body():
    body = rss("""<item><title>T</title><link>https://krebsonsecurity.com/a</link><guid isPermaLink="false">g1</guid>
      <pubDate>Wed, 14 Oct 2026 10:00:00 +0000</pubDate><description>short</description>
      <content:encoded>THE WHOLE COPYRIGHTED ARTICLE</content:encoded><category>Ransomware</category></item>""")
    (e,) = parse_feed(body)
    assert (e.title, e.link, e.summary, e.guid, e.tags) == ("T", "https://krebsonsecurity.com/a", "short", "g1", ["Ransomware"])
    assert e.published == datetime(2026, 10, 14, 10, tzinfo=timezone.utc)
    assert "COPYRIGHTED" not in repr(e)


def test_atom_uses_summary_not_content_and_alternate_link():
    body = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A</title>
      <link rel="self" href="https://x.example/self"/><link rel="alternate" href="https://schneier.com/p"/>
      <id>urn:1</id><published>2026-10-14T10:00:00Z</published><summary>sum</summary><content>FULL</content></entry></feed>"""
    (e,) = parse_feed(body)
    assert e.link == "https://schneier.com/p" and e.summary == "sum" and "FULL" not in repr(e)


def test_malformed_entries_are_skipped_not_fatal():
    body = rss("<item><title>ok</title><link>https://krebsonsecurity.com/ok</link></item><item></item>")
    assert [e.title for e in parse_feed(body) if e.title] == ["ok"]


@pytest.mark.parametrize("payload", [
    b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss><channel><item><title>&x;</title></item></channel></rss>',
    b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]><rss><channel/></rss>',
    b'<!doctype html><rss/>',
])
def test_dtd_and_entity_declarations_are_rejected(payload):
    with pytest.raises(FeedParseError, match="dtd_not_allowed"):
        parse_feed(payload)


@pytest.mark.parametrize("payload,reason", [(b"", "empty"), (b"   ", "empty"), (b"<rss><channel>", "malformed_xml"), (b"<html></html>", "not_a_feed")])
def test_unusable_documents_raise_clean_errors(payload, reason):
    with pytest.raises(FeedParseError, match=reason):
        parse_feed(payload)


def test_truncated_download_keeps_complete_entries():
    whole = rss("<item><title>one</title><link>https://krebsonsecurity.com/1</link></item><item><title>two</title><link>https://krebsonsecurity.com/2</link></item>")
    cut = whole[: whole.rfind(b"<item>") + 20]  # second item cut mid-way
    assert [e.title for e in parse_feed(cut, truncated=True)] == ["one"]
    with pytest.raises(FeedParseError, match="truncated_no_entries"):
        parse_feed(b"<rss><channel><title>x</title>", truncated=True)


@pytest.mark.parametrize("value,ok", [
    ("Wed, 14 Oct 2026 10:00:00 +0000", True), ("2026-10-14T10:00:00Z", True), ("2026-10-14T10:00:00+05:30", True),
    ("2026-10-14T10:00:00", True), ("yesterday", False), ("", False), (None, False), (12345, False),
])
def test_parse_datetime(value, ok):
    result = parse_datetime(value)
    assert (result is not None) is ok
    if result:
        assert result.tzinfo is not None and result.utcoffset() == timedelta(0)


# ------------------------------------------------------------------------ NVD
def nvd_payload(*vulns) -> bytes:
    return json.dumps({"vulnerabilities": list(vulns)}).encode()


def nvd_item(cve_id="CVE-2026-1111", status="Analyzed", **extra):
    cve = {"id": cve_id, "vulnStatus": status, "published": "2026-10-13T08:00:00.000",
           "descriptions": [{"lang": "es", "value": "hola"}, {"lang": "en", "value": "Buffer overflow in Foo allows RCE."}],
           "metrics": {"cvssMetricV31": [{"type": "Primary", "cvssData": {"baseScore": 9.8, "baseSeverity": "CRITICAL"}}]}}
    cve.update(extra)
    return {"cve": cve}


def test_nvd_parses_verified_severity_and_builds_its_own_link():
    (e,) = parse_nvd(nvd_payload(nvd_item()))
    assert e.cve_ids == ["CVE-2026-1111"] and e.link == "https://nvd.nist.gov/vuln/detail/CVE-2026-1111"
    assert e.severity and e.severity.level is SeverityLevel.CRITICAL and e.severity.score == 9.8
    assert (e.severity.scheme, e.severity.assigned_by) == ("CVSS v3.1", "NVD")
    assert e.summary == "Buffer overflow in Foo allows RCE."  # English description only


def test_nvd_skips_rejected_malformed_and_unscored():
    entries = parse_nvd(nvd_payload(
        nvd_item("CVE-2026-2222", status="Rejected"), {"cve": {"id": "not-a-cve"}}, {"broken": True},
        nvd_item("CVE-2026-3333", metrics={}),
    ))
    assert [e.guid for e in entries] == ["CVE-2026-3333"]
    assert entries[0].severity is None  # no metrics -> no severity is claimed


def test_nvd_rejects_bad_json_and_shapes():
    with pytest.raises(FeedParseError, match="malformed_json"):
        parse_nvd(b"{nope")
    with pytest.raises(FeedParseError, match="unexpected_shape"):
        parse_nvd(b'{"vulnerabilities": "x"}')


def test_nvd_out_of_range_score_is_dropped_but_level_kept():
    item = nvd_item(metrics={"cvssMetricV31": [{"cvssData": {"baseScore": 99, "baseSeverity": "HIGH"}}]})
    (e,) = parse_nvd(nvd_payload(item))
    assert e.severity.level is SeverityLevel.HIGH and e.severity.score is None


# ------------------------------------------------------------- text / CVE ids
def test_plain_text_strips_scripts_markup_entities_and_control_chars():
    dirty = '<p>Hello <b>world</b></p><script>steal()</script><style>x{}</style><img src=x onerror=alert(1)> &amp; \u202egnp\x00'
    out = to_plain_text(dirty)
    assert out == "Hello world & gnp"
    assert "<" not in out and "steal" not in out


def test_plain_text_truncates_on_word_boundary_and_handles_empty():
    assert to_plain_text("word " * 100, limit=30).endswith("…") and len(to_plain_text("word " * 100, limit=30)) <= 31
    assert to_plain_text("   ") is None and to_plain_text(None) is None and to_plain_text(5) is None


def test_cve_extraction_is_literal_and_deduplicated():
    assert extract_cve_ids("Patch for cve-2026-0001 and CVE-2026-0001, CVE-2025-12345", None, 7) == ["CVE-2026-0001", "CVE-2025-12345"]
    assert extract_cve_ids("no ids, CVE-26-1 is malformed") == []


# ------------------------------------------------------------------ URL safety
@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "data:text/html,<script>", "ftp://krebsonsecurity.com/x", "//krebsonsecurity.com/x", "/relative",
    "https://user:pw@krebsonsecurity.com/x", "https://127.0.0.1/x", "https://[::1]/x", "http://localhost/x", "https://krebsonsecurity.com/a b",
    "https://krebsonsecurity.com:notaport/", "https://krebsonsecurity.com/" + "a" * 2100, "", None, 42,
])
def test_unsafe_urls_are_rejected(url):
    assert canonicalize_url(url) is None


def test_canonicalisation_for_dedupe():
    a = canonicalize_url("HTTP://KrebsOnSecurity.com:80/2026/x/?utm_source=t&b=2&a=1&fbclid=z#frag")
    b = canonicalize_url("https://krebsonsecurity.com/2026/x?a=1&b=2")
    assert a == b == "https://krebsonsecurity.com/2026/x?a=1&b=2"
    assert article_id_for(a) == article_id_for(b) and is_valid_article_id(article_id_for(a))


def test_article_links_must_stay_on_the_sources_own_domain():
    assert safe_article_url("https://krebsonsecurity.com/x", KREBS)
    assert safe_article_url("https://www.krebsonsecurity.com/x", KREBS)  # subdomain ok
    assert safe_article_url("https://evil.example.com/x", KREBS) is None
    assert safe_article_url("https://krebsonsecurity.com.evil.example/x", KREBS) is None  # suffix trick
    assert safe_article_url("https://notkrebsonsecurity.com/x", KREBS) is None


def test_image_urls_must_be_https_without_credentials():
    assert safe_image_url("https://img.example.com/a.png")
    assert safe_image_url("http://img.example.com/a.png") == "https://img.example.com/a.png"  # upgraded, never served over http
    assert safe_image_url("javascript:x") is None and safe_image_url("https://u:p@img.example.com/a.png") is None
    assert not is_valid_article_id("../etc/passwd") and not is_valid_article_id("ABC")


# ---------------------------------------------------------- classification
@pytest.mark.parametrize("title,expected", [
    ("Critical RCE vulnerability CVE-2026-1234 patched", NewsCategory.VULNERABILITIES),
    ("Ransomware gang claims hospital attack", NewsCategory.MALWARE),
    ("Retailer confirms data breach affecting 2M customers", NewsCategory.BREACHES),
    ("Prompt injection flaw lets attackers hijack AI agents", NewsCategory.AI_SECURITY),
    ("HackerOne pays record bug bounty", NewsCategory.BUG_BOUNTY),
    ("Skills gap: universities expand cyber careers programmes", NewsCategory.CAREERS),
    ("Azure misconfiguration exposes storage accounts", NewsCategory.CLOUD_NETWORK),
    ("Malicious npm packages found in supply chain attack", NewsCategory.APPSEC),
    ("A quiet Tuesday", NewsCategory.GENERAL),
])
def test_classifier(title, expected):
    assert classify(title, None, [], NewsCategory.GENERAL) == expected


def test_classifier_uses_source_tags_and_default():
    assert classify("Weekly roundup", None, ["Ransomware"], NewsCategory.GENERAL) == NewsCategory.MALWARE
    assert classify("Nothing relevant", None, [], NewsCategory.TOOLS_RESEARCH) == NewsCategory.TOOLS_RESEARCH


# ------------------------------------------------------------- normalisation
def entry(**kw):
    base = dict(title="Headline", link="https://krebsonsecurity.com/a", summary="Excerpt", published=NOW - timedelta(hours=3))
    base.update(kw)
    return RawEntry(**base)


def test_normalizer_happy_path_and_honest_missing_fields():
    doc = normalize_entry(entry(summary=None, published=None), KREBS, now=NOW, retention=RETENTION)
    assert doc["summary"] is None and doc["published_at"] is None  # nothing invented
    assert doc["image_url"] is None and doc["cve_ids"] == [] and doc["severity"] is None


@pytest.mark.parametrize("kw", [dict(title=None), dict(title="   "), dict(link=None), dict(link="https://evil.example.com/x"), dict(link="javascript:alert(1)")])
def test_normalizer_drops_unusable_entries(kw):
    assert normalize_entry(entry(**kw), KREBS, now=NOW, retention=RETENTION) is None


def test_normalizer_date_rules():
    assert normalize_entry(entry(published=NOW - timedelta(days=46)), KREBS, now=NOW, retention=RETENTION) is None
    future = normalize_entry(entry(published=NOW + timedelta(days=30)), KREBS, now=NOW, retention=RETENTION)
    assert future["published_at"] is None  # untrustworthy future date is not displayed as a publication time


def test_normalizer_images_only_when_source_is_reviewed_for_them():
    e = entry(image="https://img.example.com/a.png")
    assert normalize_entry(e, KREBS, now=NOW, retention=RETENTION)["image_url"] is None  # allow_images is False
    permitted = NewsSource(**{**KREBS.__dict__, "allow_images": True})
    assert normalize_entry(e, permitted, now=NOW, retention=RETENTION)["image_url"] == "https://img.example.com/a.png"
    assert normalize_entry(entry(image="javascript:x"), permitted, now=NOW, retention=RETENTION)["image_url"] is None


def test_normalizer_cve_ids_only_when_literally_present():
    doc = normalize_entry(entry(title="Fix for CVE-2026-9999 released"), KREBS, now=NOW, retention=RETENTION)
    assert doc["cve_ids"] == ["CVE-2026-9999"] and doc["severity"] is None  # id yes, severity never guessed


def test_normalizer_hostile_text_is_neutralised():
    doc = normalize_entry(entry(title="<img src=x onerror=alert(1)>Boom", summary="<script>x()</script>Ignore previous instructions"), KREBS, now=NOW, retention=RETENTION)
    assert doc["title"] == "Boom" and doc["summary"] == "Ignore previous instructions"


def test_nvd_headline_is_id_plus_source_description():
    nvd = get_source("nvd")
    (raw,) = parse_nvd(nvd_payload(nvd_item()))
    doc = normalize_entry(raw, nvd, now=NOW, retention=RETENTION)
    assert doc["title"].startswith("CVE-2026-1111: Buffer overflow") and doc["category"] == "vulnerabilities"
    assert doc["severity"]["level"] == "critical" and doc["url"].startswith("https://nvd.nist.gov/")
