"""
Public cybersecurity news routes (Phase 22).

    GET /api/v1/news              articles (search, category, source, severity, pagination)
    GET /api/v1/news/categories   categories with article counts
    GET /api/v1/news/sources      the configured sources and their last-refresh status

These are deliberately PUBLIC and read-only: no ``get_current_user`` dependency, no account data,
and no parameter that can name a URL. They read the MongoDB cache only; if it is stale, a
background refresh is scheduled after the response is sent, so a slow external site never
delays a visitor.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from pymongo.database import Database

from app.core.config import settings
from app.core.dependencies import get_db, get_news_service
from app.schemas.news import NewsCategory, SeverityLevel
from app.services.news.news_service import NewsService
from app.services.news.sources import all_sources
from app.utils.helpers import success_response

router = APIRouter(prefix="/news", tags=["news"])

MAX_LIMIT = 50
_CACHE_HEADER = "public, max-age=30"


def _schedule_refresh(tasks: BackgroundTasks, service: NewsService, db: Database) -> None:
    if settings.news_enabled:
        tasks.add_task(service.refresh_if_due, db)  # runs after the response; never awaited by the visitor


@router.get("")
def list_news(
    response: Response,
    background_tasks: BackgroundTasks,
    q: str | None = Query(default=None, max_length=100, description="Words to match in headline, excerpt or CVE id."),
    category: NewsCategory | None = None,
    source: str | None = Query(default=None, pattern=r"^[a-z0-9-]{1,40}$"),
    severity: SeverityLevel | None = None,
    page: int = Query(default=1, ge=1, le=1000),
    limit: int = Query(default=12, ge=1, le=MAX_LIMIT),
    db: Database = Depends(get_db),
    service: NewsService = Depends(get_news_service),
) -> dict:
    if source and source not in {s.id for s in all_sources()}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Unknown news source.", "error_code": "VALIDATION_ERROR"},
        )
    result = service.list_articles(
        db, q=(q or "").strip() or None, category=category, source=source,
        severity=severity.value if severity else None, page=page, limit=limit,
    )
    _schedule_refresh(background_tasks, service, db)
    response.headers["Cache-Control"] = _CACHE_HEADER
    return success_response("News retrieved.", result.model_dump(mode="json"))


@router.get("/categories")
def list_categories(
    response: Response,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db),
    service: NewsService = Depends(get_news_service),
) -> dict:
    result = service.categories(db)
    _schedule_refresh(background_tasks, service, db)
    response.headers["Cache-Control"] = _CACHE_HEADER
    return success_response("News categories retrieved.", result.model_dump(mode="json"))


@router.get("/sources")
def list_sources(
    response: Response,
    db: Database = Depends(get_db),
    service: NewsService = Depends(get_news_service),
) -> dict:
    sources = service.sources(db)
    response.headers["Cache-Control"] = _CACHE_HEADER
    return success_response("News sources retrieved.", {"sources": [s.model_dump(mode="json") for s in sources]})
