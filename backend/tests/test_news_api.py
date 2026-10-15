"""Phase 22: public news API, cache/refresh behaviour and failure handling."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.routing import APIRoute

from app.core.config import settings
from app.core.dependencies import get_current_user, get_news_service
from app.db.collections import Collections
from app.main import app
from app.services.news.fetcher import FetchError, FetchResult
from app.services.news.news_service import META_ID, NewsService

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)


def item(title, path, hours_ago=1, desc="Excerpt", cat=None, domain="krebsonsecurity.com"):
    pub = (NOW - timedelta(hours=hours_ago)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    tag = f"<category>{cat}</category>" if cat else ""
    return f"<item><title>{title}</title><link>https://{domain}/{path}</link><pubDate>{pub}</pubDate><description>{desc}</description>{tag}</item>"


def feed(*items):
    return ('<?xml version="1.0"?><rss version="2.0"><channel>' + "".join(items) + "</channel></rss>").encode()


def nvd_body(*ids):
    vulns = [{"cve": {"id": i, "vulnStatus": "Analyzed", "published": (NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000"),
                      "descriptions": [{"lang": "en", "value": f"Flaw in {i}"}],
                      "metrics": {"cvssMetricV31": [{"type": "Primary", "cvssData": {"baseScore": 9.8, "baseSeverity": "CRITICAL"}}]}}} for i in ids]
    return json.dumps({"vulnerabilities": vulns}).encode()


class Feeds:
    """A fake network: source id -> bytes, or an Exception to raise. Records every call."""

    def __init__(self, mapping):
        self.mapping, self.calls = dict(mapping), []

    def __call__(self, source, url=None, **kw):
        self.calls.append((source.id, url))
        value = self.mapping.get(source.id, FetchError("timeout"))
        if isinstance(value, Exception):
            raise value
        return FetchResult(value, False)


def make_service(mapping, now=NOW):
    clock = {"now": now}
    feeds = Feeds(mapping)
    svc = NewsService(fetcher=feeds, clock=lambda: clock["now"])
    svc.clock_ref, svc.feeds = clock, feeds  # test handles
    return svc


@pytest.fixture()
def news(fake_db):
    """Service with a few healthy sources; every other source times out."""
    svc = make_service({
        "krebs": feed(
            item("Ransomware crew hits city", "a", 2, cat="Ransomware"),
            item("Retailer data breach exposes customers", "b", 5),
            item("New phishing kit analysed", "c", 9, desc="Findings about CVE-2026-4242"),
        ),
        "bleepingcomputer": feed(item("Prompt injection hijacks AI agents", "p", 1, domain="www.bleepingcomputer.com")),
        "nvd": nvd_body("CVE-2026-7001", "CVE-2026-7002"),
    })
    svc.refresh(fake_db, force=True)
    app.dependency_overrides[get_news_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_news_service, None)


def get(client, path="/api/v1/news", **params):
    return client.get(path, params=params)


def data(resp):
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ------------------------------------------------------------- public access
def test_news_is_public_without_any_credentials(client, news):
    resp = get(client)
    assert resp.status_code == 200 and resp.json()["success"] is True
    assert data(resp)["total"] == 6


@pytest.mark.parametrize("path", ["/api/v1/news", "/api/v1/news/categories", "/api/v1/news/sources"])
def test_all_news_endpoints_are_public_even_with_a_garbage_token(client, news, path):
    assert client.get(path).status_code == 200
    assert client.get(path, headers={"Authorization": "Bearer not-a-real-jwt"}).status_code == 200  # a stale token must not matter


def test_news_routes_do_not_depend_on_authentication():
    news_routes = [r for r in app.routes if isinstance(r, APIRoute) and r.path.startswith("/api/v1/news")]
    assert len(news_routes) == 3
    for route in news_routes:
        calls = {d.call for d in route.dependant.dependencies}
        assert get_current_user not in calls and route.methods == {"GET"}  # public and read-only


@pytest.mark.parametrize("path", ["/api/v1/users/me", "/api/v1/auth/me", "/api/v1/notifications", "/api/v1/history", "/api/v1/history/summary", "/api/v1/users/me/preferences"])
def test_private_routes_still_require_authentication(client, news, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_news_cannot_be_written_to(client, news):
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/api/v1/news").status_code in (404, 405)


def test_response_exposes_no_account_data_or_secrets(client, news, monkeypatch):
    monkeypatch.setattr(settings, "nvd_api_key", "TOPSECRETKEY123")
    blob = json.dumps([get(client).json(), get(client, path="/api/v1/news/sources").json()]).lower()
    for needle in ("topsecretkey123", "password", "email", "token", "jwt", "gemini", "mongodb://"):
        assert needle not in blob


# ------------------------------------------------------------------- listing
def test_list_shape_sorting_and_publication_vs_retrieval_times(client, news):
    d = data(get(client))
    items = d["items"]
    dated = [i["published_at"] for i in items if i["published_at"]]
    assert dated == sorted(dated, reverse=True)
    first = items[0]
    assert {"id", "title", "summary", "url", "source_id", "source_name", "category", "published_at", "first_seen_at", "image_url", "cve_ids", "severity"} <= first.keys()
    assert first["first_seen_at"].startswith("2026-10-15T12:00")  # retrieval time kept separate
    assert first["published_at"] != first["first_seen_at"]


def test_missing_fields_are_honest_not_invented(client, fake_db):
    svc = make_service({"krebs": feed("<item><title>Bare headline</title><link>https://krebsonsecurity.com/bare</link></item>")})
    svc.refresh(fake_db, force=True)
    app.dependency_overrides[get_news_service] = lambda: svc
    try:
        (it,) = data(get(client))["items"]
    finally:
        app.dependency_overrides.pop(get_news_service, None)
    assert it["published_at"] is None and it["summary"] is None and it["image_url"] is None and it["severity"] is None and it["cve_ids"] == []


def test_severity_and_cve_only_where_verifiable(client, news):
    items = {i["title"].split(":")[0]: i for i in data(get(client, limit=50))["items"]}
    nvd = items["CVE-2026-7001"]
    assert nvd["severity"] == {"level": "critical", "score": 9.8, "scheme": "CVSS v3.1", "assigned_by": "NVD"} and nvd["cve_ids"] == ["CVE-2026-7001"]
    phishing = next(i for i in items.values() if "phishing" in i["title"])
    assert phishing["cve_ids"] == ["CVE-2026-4242"] and phishing["severity"] is None
    assert next(i for i in items.values() if "Ransomware" in i["title"])["severity"] is None


def test_filters_category_source_severity_and_search(client, news):
    assert {i["category"] for i in data(get(client, category="malware"))["items"]} == {"malware"}
    assert [i["source_id"] for i in data(get(client, source="bleepingcomputer"))["items"]] == ["bleepingcomputer"]
    crit = data(get(client, severity="critical"))
    assert crit["total"] == 2 and all(i["source_id"] == "nvd" for i in crit["items"])
    assert data(get(client, q="phishing"))["total"] == 1
    assert data(get(client, q="PHISHING kit"))["total"] == 1  # case-insensitive, all words must match
    assert data(get(client, q="phishing ransomware"))["total"] == 0
    assert data(get(client, q="CVE-2026-4242"))["total"] == 1  # CVE ids are searchable
    assert data(get(client, q="no-such-thing-xyz"))["items"] == []


def test_search_text_is_never_interpreted_as_a_pattern(client, news):
    for evil in (".*", "(a+)+$", "[", "\\", "a{1,", "$where", "(?i)", "' OR 1=1 --"):
        resp = get(client, q=evil)
        assert resp.status_code == 200 and data(resp)["total"] == 0


def test_pagination_bounds_and_has_more(client, news):
    p1 = data(get(client, limit=4, page=1))
    p2 = data(get(client, limit=4, page=2))
    p3 = data(get(client, limit=4, page=3))
    assert (len(p1["items"]), p1["has_more"], len(p2["items"]), p2["has_more"], p3["items"]) == (4, True, 2, False, [])
    assert {i["id"] for i in p1["items"]}.isdisjoint({i["id"] for i in p2["items"]}) and p1["total"] == 6


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 51}, {"limit": -1}, {"limit": "abc"}, {"page": 0}, {"page": 1001}, {"page": "x"},
    {"category": "nonsense"}, {"severity": "extreme"}, {"q": "x" * 101}, {"source": "Not Valid!"}, {"source": "../etc"}, {"source": "unknown-source"},
])
def test_invalid_query_parameters_are_rejected_cleanly(client, news, params):
    resp = get(client, **params)
    assert resp.status_code == 422 and resp.json() == {"success": False, "message": resp.json()["message"], "error_code": "VALIDATION_ERROR"}


def test_page_size_is_capped_at_50(client, news):
    assert data(get(client, limit=50))["limit"] == 50


# ---------------------------------------------------------------- categories
def test_categories_list_all_with_counts(client, news):
    d = data(get(client, "/api/v1/news/categories"))
    by_id = {c["id"]: c for c in d["categories"]}
    assert set(by_id) >= {"vulnerabilities", "breaches", "malware", "ai-security", "appsec", "cloud-network", "bug-bounty", "tools-research", "careers"}
    assert by_id["vulnerabilities"]["count"] == 3 and by_id["careers"]["count"] == 0  # 2 NVD CVEs + the phishing-kit item whose excerpt cites a CVE;  # empty categories are shown honestly
    assert d["total"] == sum(c["count"] for c in d["categories"]) == 6


def test_sources_endpoint_reports_status_without_internals(client, news):
    sources = {s["id"]: s for s in data(get(client, "/api/v1/news/sources"))["sources"]}
    assert sources["krebs"]["status"] == "ok" and sources["krebs"]["article_count"] == 3
    assert sources["cisa"]["status"] == "failed" and sources["cisa"]["last_error"] == "timeout"
    assert not any("feed_url" in s or "allowed_hosts" in s for s in sources.values())


# --------------------------------------------------------- dedupe & hygiene
def test_duplicates_across_refreshes_and_within_a_feed_collapse(fake_db):
    dup = item("Same story", "dup", 1)
    svc = make_service({"krebs": feed(dup, dup, item("Same story (tracking)", "dup?utm_source=x", 1))})
    svc.refresh(fake_db, force=True)
    svc.refresh(fake_db, force=True)
    assert fake_db[Collections.NEWS_ARTICLES].count_documents({}) == 1


def test_hostile_and_off_domain_entries_never_reach_the_cache(fake_db):
    body = feed(
        item("Good", "ok", 1),
        item("Phish", "x", 1, domain="evil.example.com"),
        "<item><title>js</title><link>javascript:alert(1)</link></item>",
        item("<![CDATA[<script>alert(1)</script>Scripted]]>", "s", 1, desc="<![CDATA[<img src=x onerror=alert(1)>text]]>"),
    )
    svc = make_service({"krebs": body})
    svc.refresh(fake_db, force=True)
    docs = list(fake_db[Collections.NEWS_ARTICLES].find({}))
    assert sorted(d["title"] for d in docs) == ["Good", "Scripted"]
    assert all("<" not in d["title"] and "<" not in (d["summary"] or "") for d in docs)


# ------------------------------------------------- failures, cache, freshness
def test_one_failing_source_does_not_block_others(fake_db):
    svc = make_service({"krebs": FetchError("http_503"), "bleepingcomputer": feed(item("Works", "w", 1, domain="www.bleepingcomputer.com"))})
    report = svc.refresh(fake_db, force=True)
    assert report["krebs"] == "http_503" and report["bleepingcomputer"] == "ok"
    assert fake_db[Collections.NEWS_ARTICLES].count_documents({}) == 1


def test_malformed_feed_and_adapter_bug_are_isolated(fake_db):
    class Boom(Feeds):
        def __call__(self, source, url=None, **kw):
            if source.id == "schneier":
                raise RuntimeError("adapter bug with secret detail")
            return super().__call__(source, url, **kw)
    svc = NewsService(fetcher=Boom({"krebs": b"<rss><channel><item>", "bleepingcomputer": feed(item("Fine", "f", 1, domain="www.bleepingcomputer.com"))}), clock=lambda: NOW)
    report = svc.refresh(fake_db, force=True)
    assert report["krebs"] == "malformed_xml" and report["schneier"] == "unexpected_error" and report["bleepingcomputer"] == "ok"
    assert "secret" not in json.dumps(fake_db[Collections.NEWS_SOURCE_STATE].find_one({"_id": "schneier"}), default=str)


def test_nvd_partial_failure_keeps_the_successful_half(fake_db):
    calls = []
    def fetch(source, url=None, **kw):
        calls.append(url)
        if "cvssV4Severity" in (url or ""):
            raise FetchError("http_400")
        return FetchResult(nvd_body("CVE-2026-8001"), False)
    svc = NewsService(fetcher=fetch, sources=lambda: tuple(s for s in __import__("app.services.news.sources", fromlist=["x"]).all_sources() if s.id == "nvd"), clock=lambda: NOW)
    assert svc.refresh(fake_db, force=True)["nvd"] == "ok" and len(calls) == 2
    assert fake_db[Collections.NEWS_ARTICLES].count_documents({}) == 1
    assert all(u.startswith("https://services.nvd.nist.gov/rest/json/cves/2.0?") and "noRejected" in u and "CRITICAL" in u for u in calls)


def test_failed_refresh_falls_back_to_cache_with_honest_warning(client, news, fake_db):
    news.feeds.mapping = {}  # every source now times out
    news.clock_ref["now"] = NOW + timedelta(hours=3)
    news.refresh(fake_db, force=True)
    d = data(get(client))
    assert d["total"] == 6  # cached articles still served
    f = d["freshness"]
    assert f["state"] == "degraded" and "cached" in f["message"] and f["last_successful_refresh_at"].startswith("2026-10-15T12:00")
    assert f["sources_ok"] == 0 and f["sources_failed"] == 8


def test_freshness_states(client, fake_db, news):
    assert data(get(client))["freshness"]["state"] == "fresh"
    assert data(get(client))["freshness"]["message"].startswith("5 of 8")  # partial outage is disclosed
    news.feeds.mapping = {}  # sources go down; the stale request's background refresh will fail
    news.clock_ref["now"] = NOW + timedelta(minutes=settings.news_refresh_interval_minutes + 5)
    assert data(get(client))["freshness"]["state"] == "stale"
    news.clock_ref["now"] = NOW + timedelta(minutes=settings.news_refresh_interval_minutes * 2 + 5)
    assert data(get(client))["freshness"]["state"] == "degraded"


def test_empty_cache_reports_empty_not_an_error(client, fake_db):
    svc = make_service({})
    app.dependency_overrides[get_news_service] = lambda: svc
    try:
        d = data(get(client))
    finally:
        app.dependency_overrides.pop(get_news_service, None)
    assert d["items"] == [] and d["total"] == 0 and d["freshness"]["state"] == "empty" and d["freshness"]["last_successful_refresh_at"] is None


def test_database_outage_is_a_clean_503(client):
    from app.core.dependencies import get_db
    from fastapi import HTTPException
    def down():
        raise HTTPException(503, detail={"message": "Database is currently unavailable.", "error_code": "SERVICE_UNAVAILABLE"})
    app.dependency_overrides[get_db] = down
    try:
        resp = client.get("/api/v1/news")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 503 and resp.json()["error_code"] == "SERVICE_UNAVAILABLE"


# ---------------------------------------------- background refresh behaviour
def test_requests_never_wait_for_external_sources(client, fake_db):
    """A request on a cold cache returns immediately from the cache; the refresh runs afterwards."""
    svc = make_service({"krebs": feed(item("Late arrival", "late", 1))})
    app.dependency_overrides[get_news_service] = lambda: svc
    try:
        first = client.get("/api/v1/news")
        assert first.status_code == 200
        assert first.json()["data"]["items"] == []  # response was built before any fetch happened
        assert svc.feeds.calls  # ...and the refresh was scheduled for after the response
        assert data(client.get("/api/v1/news"))["total"] == 1
    finally:
        app.dependency_overrides.pop(get_news_service, None)


def test_fresh_cache_does_not_trigger_external_requests(client, news):
    news.feeds.calls.clear()
    for _ in range(5):
        get(client)
        get(client, "/api/v1/news/categories")
    assert news.feeds.calls == []  # traffic alone cannot drive outbound requests


def test_failing_sources_back_off_instead_of_being_hammered(fake_db):
    svc = make_service({})
    svc.refresh(fake_db, force=False)
    n = len(svc.feeds.calls)
    svc.refresh(fake_db, force=False)
    assert len(svc.feeds.calls) == n  # inside the cooldown
    svc.clock_ref["now"] = NOW + timedelta(seconds=61)
    svc.refresh(fake_db, force=False)
    assert len(svc.feeds.calls) == 2 * n  # first retry after ~60s
    svc.clock_ref["now"] = NOW + timedelta(seconds=61 + 61)
    svc.refresh(fake_db, force=False)
    assert len(svc.feeds.calls) == 2 * n  # second failure doubles the wait


def test_refresh_lease_prevents_concurrent_refreshes(fake_db):
    svc = make_service({"krebs": feed(item("One", "1", 1))})
    svc.ensure_indexes(fake_db)
    fake_db[Collections.NEWS_SOURCE_STATE].insert_one({"_id": META_ID, "lease_until": (NOW + timedelta(seconds=60)).replace(tzinfo=None)})
    assert svc.refresh(fake_db, force=True) == {} and svc.feeds.calls == []
    assert svc.freshness(fake_db).refreshing is True
    svc.clock_ref["now"] = NOW + timedelta(seconds=120)  # lease expired
    assert svc.refresh(fake_db, force=True)["krebs"] == "ok"
    assert svc.freshness(fake_db).refreshing is False  # released afterwards


def test_disabled_sources_are_neither_fetched_nor_shown(client, fake_db, monkeypatch):
    monkeypatch.setattr(settings, "news_disabled_sources", "krebs, nvd")
    from app.services.news.sources import enabled_sources
    feeds = Feeds({"krebs": feed(item("Hidden", "h", 1))})
    svc = NewsService(fetcher=feeds, sources=enabled_sources, clock=lambda: NOW)
    svc.refresh(fake_db, force=True)
    assert feeds.calls and all(sid not in ("krebs", "nvd") for sid, _ in feeds.calls)
    fake_db[Collections.NEWS_ARTICLES].insert_one({"article_id": "a" * 24, "title": "Old cached", "url": "https://krebsonsecurity.com/o", "source_id": "krebs",
        "source_name": "Krebs", "category": "general", "published_at": None, "first_seen_at": NOW.replace(tzinfo=None), "expires_at": (NOW + timedelta(days=1)).replace(tzinfo=None)})
    assert svc.list_articles(fake_db).total == 0  # disabling a source also hides its cached rows


def test_retention_index_and_expired_rows(fake_db, client):
    indexes = fake_db[Collections.NEWS_ARTICLES].index_information()
    assert any(v.get("expireAfterSeconds") == 0 and v["key"] == [("expires_at", 1)] for v in indexes.values())
    assert any(v.get("unique") and v["key"] == [("article_id", 1)] for v in indexes.values())
    fake_db[Collections.NEWS_ARTICLES].insert_one({"article_id": "b" * 24, "title": "Expired", "url": "https://krebsonsecurity.com/e", "source_id": "krebs",
        "source_name": "Krebs", "category": "general", "published_at": None, "first_seen_at": NOW.replace(tzinfo=None), "expires_at": (NOW - timedelta(days=1)).replace(tzinfo=None)})
    svc = make_service({})
    assert svc.list_articles(fake_db).total == 0  # not shown even before Mongo's TTL monitor deletes it


def test_news_disabled_flag_stops_scheduling_refreshes(client, fake_db, monkeypatch):
    monkeypatch.setattr(settings, "news_enabled", False)
    svc = make_service({"krebs": feed(item("x", "x", 1))})
    app.dependency_overrides[get_news_service] = lambda: svc
    try:
        assert client.get("/api/v1/news").status_code == 200
    finally:
        app.dependency_overrides.pop(get_news_service, None)
    assert svc.feeds.calls == []


def test_conditional_get_not_modified_extends_retention_without_losing_articles(fake_db):
    class Etag(Feeds):
        def __call__(self, source, url=None, **kw):
            self.calls.append((source.id, kw.get("etag")))
            if source.id == "krebs" and kw.get("etag"):
                return FetchResult(b"", False, kw["etag"], None, not_modified=True)
            return FetchResult(feed(item("Kept", "k", 1)), False, '"v1"', None) if source.id == "krebs" else (_ for _ in ()).throw(FetchError("timeout"))
    svc = NewsService(fetcher=Etag({}), clock=lambda: NOW)
    svc.refresh(fake_db, force=True)
    svc.clock_ref = None
    svc._clock = lambda: NOW + timedelta(days=10)
    assert svc.refresh(fake_db, force=True)["krebs"] == "ok"
    assert ("krebs", '"v1"') in svc._fetch.calls
    doc = fake_db[Collections.NEWS_ARTICLES].find_one({"title": "Kept"})
    assert doc["expires_at"] > (NOW + timedelta(days=50)).replace(tzinfo=None)
