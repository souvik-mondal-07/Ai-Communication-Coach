"""
Check every configured news source against its LIVE endpoint (needs internet; no database).

    cd backend
    python -m app.services.news.check_sources

Prints, per source: whether it was reachable, how many entries parsed, how many survived
normalisation (valid, on-domain, recent), and a sample headline. Use it after deploying, or
when a source seems quiet, to see exactly which stage failed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.services.news.fetcher import FetchError
from app.services.news.news_service import NewsService
from app.services.news.normalizer import normalize_entry
from app.services.news.parsers import FeedParseError
from app.services.news.sources import all_sources


def main() -> int:
    service = NewsService()
    now = datetime.now(timezone.utc)
    retention = timedelta(days=settings.news_retention_days)
    failures = 0
    for source in all_sources():
        try:
            if source.kind.value == "nvd-api":
                entries = service._download_nvd(source, now)  # noqa: SLF001 - diagnostic tool
            else:
                entries, _, _ = service._download(source, {}, now)  # noqa: SLF001
            docs = [d for d in (normalize_entry(e, source, now=now, retention=retention) for e in entries) if d]
            sample = docs[0]["title"][:70] if docs else "-"
            print(f"OK    {source.id:<17} parsed={len(entries):<3} usable={len(docs):<3} e.g. {sample}")
            failures += 0 if docs else 1
        except (FetchError, FeedParseError) as exc:
            failures += 1
            print(f"FAIL  {source.id:<17} {getattr(exc, 'code', exc)}")
    print(f"\n{len(all_sources()) - failures}/{len(all_sources())} sources returned usable articles.")
    return 1 if failures == len(all_sources()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
