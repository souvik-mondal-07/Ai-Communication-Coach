"""
Public cybersecurity news: MongoDB-backed cache, refresh, and queries.

Request path vs refresh path
----------------------------
* Public requests only ever read the MongoDB cache, so the page never waits on an external site.
* When the cache is older than the refresh interval, a request schedules a *background* refresh
  (stale-while-revalidate). No scheduler or worker dependency is needed; a short MongoDB lease
  stops several workers/requests from refreshing at once, and per-source cooldowns (with
  back-off after failures) stop traffic from driving external requests.
* One failing source is recorded and skipped; the others still load.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlencode

from pymongo import ASCENDING, DESCENDING, UpdateOne
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.db.collections import Collections
from app.schemas.news import (
    CATEGORY_INFO,
    ArticleSeverity,
    CategoriesResponse,
    CategoryCount,
    Freshness,
    FreshnessState,
    NewsArticle,
    NewsCategory,
    NewsListResponse,
    SourceInfo,
    SourceStatus,
)
from app.services.news.fetcher import FetchError, FetchResult, fetch_source_bytes
from app.services.news.normalizer import normalize_entry
from app.services.news.parsers import FeedParseError, RawEntry, parse_feed, parse_nvd
from app.services.news.sources import NewsSource, SourceKind, enabled_sources
from app.utils.logger import get_logger

logger = get_logger(__name__)

META_ID = "__refresh__"
LEASE_SECONDS = 150
MIN_RETRY_SECONDS = 60
NVD_WINDOW_DAYS = 7
MAX_QUERY_TERMS = 5

Fetcher = Callable[..., FetchResult]


def _naive(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def _aware(dt: datetime | None) -> datetime | None:
    return None if dt is None else (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc))


def _now() -> datetime:
    return datetime.now(timezone.utc)


class NewsService:
    def __init__(
        self,
        fetcher: Fetcher = fetch_source_bytes,
        sources: Callable[[], tuple[NewsSource, ...]] = enabled_sources,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._fetch = fetcher
        self._sources = sources
        self._clock = clock

    # ------------------------------------------------------------------ setup
    def ensure_indexes(self, db: Database) -> None:
        articles = db[Collections.NEWS_ARTICLES]
        articles.create_index("article_id", unique=True)
        articles.create_index([("published_at", DESCENDING), ("first_seen_at", DESCENDING)])
        articles.create_index([("category", ASCENDING), ("published_at", DESCENDING)])
        articles.create_index([("source_id", ASCENDING), ("published_at", DESCENDING)])
        articles.create_index("expires_at", expireAfterSeconds=0)  # retention: Mongo deletes expired rows

    # ---------------------------------------------------------------- refresh
    def _due(self, state: dict | None, interval: timedelta, now: datetime) -> bool:
        if not state or not state.get("last_attempt_at"):
            return True
        failures = int(state.get("consecutive_failures", 0))
        wait = interval if failures == 0 else min(interval, timedelta(seconds=MIN_RETRY_SECONDS * 2 ** (failures - 1)))
        return _aware(state["last_attempt_at"]) + wait <= now  # type: ignore[operator]

    def due_sources(self, db: Database, now: datetime | None = None) -> list[NewsSource]:
        now = now or self._clock()
        interval = timedelta(minutes=settings.news_refresh_interval_minutes)
        states = {s["_id"]: s for s in db[Collections.NEWS_SOURCE_STATE].find({"_id": {"$ne": META_ID}})}
        return [s for s in self._sources() if self._due(states.get(s.id), interval, now)]

    def _acquire_lease(self, db: Database, now: datetime) -> bool:
        meta = db[Collections.NEWS_SOURCE_STATE]
        try:
            meta.update_one({"_id": META_ID}, {"$setOnInsert": {"lease_until": None}}, upsert=True)
            claimed = meta.find_one_and_update(
                {"_id": META_ID, "$or": [{"lease_until": None}, {"lease_until": {"$lt": _naive(now)}}]},
                {"$set": {"lease_until": _naive(now) + timedelta(seconds=LEASE_SECONDS), "last_attempt_at": _naive(now)}},
            )
            return claimed is not None
        except PyMongoError:
            logger.warning("News refresh lease unavailable", exc_info=True)
            return False

    def _release_lease(self, db: Database) -> None:
        try:
            db[Collections.NEWS_SOURCE_STATE].update_one({"_id": META_ID}, {"$set": {"lease_until": None}})
        except PyMongoError:
            logger.warning("Could not release news refresh lease", exc_info=True)

    def refresh_if_due(self, db: Database) -> dict[str, str]:
        """Background entry point: refresh only the sources whose cooldown has passed."""
        return self.refresh(db, force=False)

    def refresh(self, db: Database, *, force: bool = False) -> dict[str, str]:
        """
        Refresh sources. Returns {source_id: "ok" | "skipped" | <error code>}.
        Never raises: a refresh problem must not break a request or the process.
        """
        report: dict[str, str] = {}
        try:
            now = self._clock()
            targets = list(self._sources()) if force else self.due_sources(db, now)
            if not targets or not self._acquire_lease(db, now):
                return report
            try:
                with ThreadPoolExecutor(max_workers=4, thread_name_prefix="news-refresh") as pool:
                    futures = {pool.submit(self._refresh_source, db, s, now): s for s in targets}
                    for future in as_completed(futures):
                        report[futures[future].id] = future.result()
            finally:
                self._release_lease(db)
        except Exception:  # noqa: BLE001 - background work must never propagate
            logger.warning("News refresh aborted unexpectedly", exc_info=True)
        return report

    def _refresh_source(self, db: Database, source: NewsSource, now: datetime) -> str:
        states = db[Collections.NEWS_SOURCE_STATE]
        prior = states.find_one({"_id": source.id}) or {}
        failures = int(prior.get("consecutive_failures", 0))
        try:
            entries, validators, not_modified = self._download(source, prior, now)
            articles = self._to_articles(source, entries, now)
            expires = _naive(now) + timedelta(days=settings.news_retention_days)
            if not_modified:
                db[Collections.NEWS_ARTICLES].update_many({"source_id": source.id}, {"$set": {"expires_at": expires}})
            elif articles:
                self._upsert(db, articles, now, expires)
            update = {
                "last_attempt_at": _naive(now), "last_success_at": _naive(now), "last_error": None,
                "consecutive_failures": 0, **validators,
            }
            states.update_one({"_id": source.id}, {"$set": update}, upsert=True)
            logger.info("News source %s refreshed: %d usable entries", source.id, len(articles))
            return "ok"
        except (FetchError, FeedParseError) as exc:
            code = exc.code if isinstance(exc, FetchError) else str(exc)
            logger.warning("News source %s failed: %s", source.id, code)
        except Exception:  # noqa: BLE001 - isolate any adapter bug to this one source
            code = "unexpected_error"
            logger.warning("News source %s failed unexpectedly", source.id, exc_info=True)
        try:
            states.update_one(
                {"_id": source.id},
                {"$set": {"last_attempt_at": _naive(now), "last_error": code, "consecutive_failures": failures + 1}},
                upsert=True,
            )
        except PyMongoError:
            logger.warning("Could not record failure for %s", source.id, exc_info=True)
        return code

    def _download(self, source: NewsSource, prior: dict, now: datetime) -> tuple[list[RawEntry], dict, bool]:
        if source.kind is SourceKind.NVD_API:
            return self._download_nvd(source, now), {}, False
        result = self._fetch(source, etag=prior.get("etag"), last_modified=prior.get("last_modified"))
        validators = {"etag": result.etag, "last_modified": result.last_modified}
        if result.not_modified:
            return [], {}, True
        return parse_feed(result.body, truncated=result.truncated), validators, False

    def _download_nvd(self, source: NewsSource, now: datetime) -> list[RawEntry]:
        """Critical-severity CVEs from the last week; CVSS v3 and v4 are separate filters, so two requests."""
        fmt = "%Y-%m-%dT%H:%M:%S.000"
        window = {"pubStartDate": (_naive(now) - timedelta(days=NVD_WINDOW_DAYS)).strftime(fmt), "pubEndDate": _naive(now).strftime(fmt)}
        merged: dict[str, RawEntry] = {}
        errors: list[Exception] = []
        for severity_param in ("cvssV3Severity", "cvssV4Severity"):
            query = urlencode({**window, severity_param: "CRITICAL", "resultsPerPage": source.max_items}) + "&noRejected"
            try:
                result = self._fetch(source, f"{source.feed_url}?{query}")
                for entry in parse_nvd(result.body):
                    merged.setdefault(entry.guid or "", entry)
            except (FetchError, FeedParseError) as exc:
                errors.append(exc)
        if len(errors) == 2:
            raise errors[0]  # both failed: surface the first reason
        return list(merged.values())

    def _to_articles(self, source: NewsSource, entries: list[RawEntry], now: datetime) -> list[dict]:
        retention = timedelta(days=settings.news_retention_days)
        seen: dict[str, dict] = {}
        for entry in entries:
            doc = normalize_entry(entry, source, now=now, retention=retention)
            if doc:
                seen.setdefault(doc["article_id"], doc)  # duplicate URLs inside one feed collapse here
        ordered = sorted(seen.values(), key=lambda d: d["published_at"] or datetime.min, reverse=True)
        return ordered[: source.max_items]

    def _upsert(self, db: Database, articles: list[dict], now: datetime, expires: datetime) -> None:
        ops = []
        for doc in articles:
            insert_only = {k: doc[k] for k in ("source_id", "source_name")}
            insert_only["first_seen_at"] = _naive(now)
            fields = {k: v for k, v in doc.items() if k not in insert_only and k != "article_id"}
            fields.update(last_seen_at=_naive(now), expires_at=expires)
            ops.append(UpdateOne({"article_id": doc["article_id"]}, {"$set": fields, "$setOnInsert": insert_only}, upsert=True))
        if ops:
            db[Collections.NEWS_ARTICLES].bulk_write(ops, ordered=False)

    # ---------------------------------------------------------------- queries
    def _enabled_ids(self) -> list[str]:
        return [s.id for s in self._sources()]

    def _filter(self, *, q: str | None, category: NewsCategory | None, source: str | None, severity: str | None, now: datetime) -> dict:
        clauses: list[dict] = [
            {"source_id": {"$in": self._enabled_ids()}},
            {"expires_at": {"$gt": _naive(now)}},
        ]
        if category:
            clauses.append({"category": category.value})
        if source:
            clauses.append({"source_id": source})
        if severity:
            clauses.append({"severity.level": severity})
        for term in (q or "").split()[:MAX_QUERY_TERMS]:
            rx = {"$regex": re.escape(term[:50]), "$options": "i"}  # escaped: user text is never a pattern
            clauses.append({"$or": [{"title": rx}, {"summary": rx}, {"cve_ids": rx}]})
        return {"$and": clauses}

    def list_articles(
        self, db: Database, *, q: str | None = None, category: NewsCategory | None = None,
        source: str | None = None, severity: str | None = None, page: int = 1, limit: int = 12,
    ) -> NewsListResponse:
        now = self._clock()
        flt = self._filter(q=q, category=category, source=source, severity=severity, now=now)
        coll = db[Collections.NEWS_ARTICLES]
        total = coll.count_documents(flt)
        rows = (
            coll.find(flt).sort([("published_at", DESCENDING), ("first_seen_at", DESCENDING), ("article_id", ASCENDING)])
            .skip((page - 1) * limit).limit(limit)
        )
        return NewsListResponse(
            items=[self._to_model(r) for r in rows], total=total, page=page, limit=limit,
            has_more=page * limit < total, freshness=self.freshness(db),
        )

    @staticmethod
    def _to_model(row: dict) -> NewsArticle:
        return NewsArticle(
            id=row["article_id"], title=row["title"], summary=row.get("summary"), url=row["url"],
            source_id=row["source_id"], source_name=row["source_name"], category=NewsCategory(row["category"]),
            published_at=_aware(row.get("published_at")), first_seen_at=_aware(row["first_seen_at"]),  # type: ignore[arg-type]
            image_url=row.get("image_url"), cve_ids=row.get("cve_ids") or [],
            severity=ArticleSeverity(**row["severity"]) if row.get("severity") else None,
        )

    def categories(self, db: Database) -> CategoriesResponse:
        now = self._clock()
        base = {"source_id": {"$in": self._enabled_ids()}, "expires_at": {"$gt": _naive(now)}}
        counts = {
            r["_id"]: r["n"]
            for r in db[Collections.NEWS_ARTICLES].aggregate([{"$match": base}, {"$group": {"_id": "$category", "n": {"$sum": 1}}}])
        }
        cats = [
            CategoryCount(id=cat, label=label, description=desc, count=int(counts.get(cat.value, 0)))
            for cat, (label, desc) in CATEGORY_INFO.items()
        ]
        return CategoriesResponse(categories=cats, total=sum(c.count for c in cats))

    def sources(self, db: Database) -> list[SourceInfo]:
        states = {s["_id"]: s for s in db[Collections.NEWS_SOURCE_STATE].find({"_id": {"$ne": META_ID}})}
        counts = {
            r["_id"]: r["n"]
            for r in db[Collections.NEWS_ARTICLES].aggregate([{"$group": {"_id": "$source_id", "n": {"$sum": 1}}}])
        }
        out = []
        for src in self._sources():
            st = states.get(src.id) or {}
            if not st.get("last_attempt_at"):
                status = SourceStatus.PENDING
            else:
                status = SourceStatus.FAILED if st.get("last_error") else SourceStatus.OK
            out.append(SourceInfo(
                id=src.id, name=src.name, homepage_url=src.homepage_url, kind=src.kind.value, status=status,
                last_success_at=_aware(st.get("last_success_at")), last_error=st.get("last_error"),
                article_count=int(counts.get(src.id, 0)),
            ))
        return out

    def freshness(self, db: Database) -> Freshness:
        now = self._clock()
        interval = settings.news_refresh_interval_minutes
        infos = self.sources(db)
        meta = db[Collections.NEWS_SOURCE_STATE].find_one({"_id": META_ID}) or {}
        lease = meta.get("lease_until")
        refreshing = bool(lease and _aware(lease) > now)  # type: ignore[operator]
        successes = [i.last_success_at for i in infos if i.last_success_at]
        last_ok = max(successes) if successes else None
        attempts = [s.get("last_attempt_at") for s in db[Collections.NEWS_SOURCE_STATE].find({"_id": {"$ne": META_ID}}) if s.get("last_attempt_at")]
        last_attempt = _aware(max(attempts)) if attempts else None
        ok = sum(1 for i in infos if i.status is SourceStatus.OK)
        failed = sum(1 for i in infos if i.status is SourceStatus.FAILED)
        has_articles = db[Collections.NEWS_ARTICLES].count_documents({"source_id": {"$in": [i.id for i in infos]}, "expires_at": {"$gt": _naive(now)}}, limit=1) > 0

        message: str | None = None
        if not has_articles:
            state = FreshnessState.EMPTY
            message = "Fetching the latest articles — this can take a moment." if refreshing else (
                "No articles are cached yet." if ok + failed == 0 else "No articles could be retrieved from the news sources right now."
            )
        elif last_ok is None or now - last_ok > timedelta(minutes=interval * 2):
            state = FreshnessState.DEGRADED
            message = "Live refresh is failing, so these are cached articles and may be out of date."
        elif now - last_ok > timedelta(minutes=interval):
            state = FreshnessState.STALE
            message = "Refreshing in the background; these articles may be slightly out of date."
        else:
            state = FreshnessState.FRESH
            if failed:
                message = f"{failed} of {len(infos)} sources could not be reached on the latest refresh."
        return Freshness(
            state=state, last_successful_refresh_at=last_ok, last_attempt_at=last_attempt, refreshing=refreshing,
            refresh_interval_minutes=interval, sources_ok=ok, sources_failed=failed, message=message,
        )


news_service = NewsService()
