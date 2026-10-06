"""
Advanced Interview & Communication Analytics routes (Step 18).

    GET /api/v1/analytics/overview
    GET /api/v1/analytics/interviews
    GET /api/v1/analytics/communication
    GET /api/v1/analytics/speaking
    GET /api/v1/analytics/pressure
    GET /api/v1/analytics/domains
    GET /api/v1/analytics/trends
    GET /api/v1/analytics/insights      (?ai_summary=true for an optional Gemini summary)
    GET /api/v1/analytics/readiness

Read-only and authenticated. The user always comes from the JWT; there is no
`user_id` parameter. Query parameters: `range` (7d|30d|90d|all, default 30d) or a
custom `start_date`/`end_date`. Internal errors are logged and never returned.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.core.dependencies import get_analytics_service, get_current_user, get_db
from app.models.user import UserDocument
from app.services.analytics.analytics_service import AnalyticsService
from app.services.analytics.common import DateRange, InvalidRangeError, resolve_range
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

_UNEXPECTED = {"message": "Analytics are temporarily unavailable.", "error_code": "INTERNAL_SERVER_ERROR"}


def get_range(
    range: Literal["7d", "30d", "90d", "all"] = Query("30d", description="Preset window."),
    start_date: date | None = Query(None, description="Custom range start (overrides `range`)."),
    end_date: date | None = Query(None, description="Custom range end (inclusive)."),
) -> DateRange:
    try:
        return resolve_range(range, start_date, end_date)
    except InvalidRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "error_code": "INVALID_DATE_RANGE"},
        ) from exc


def _run(label: str, fn, db: Database, user: UserDocument, window: DateRange):
    try:
        return fn(db, user=user, window=window)
    except Exception:
        logger.error("Analytics %s failed user_id=%s", label, user["_id"], exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)


def _endpoint(name: str, method: str, message: str):
    def handler(
        window: DateRange = Depends(get_range),
        current_user: UserDocument = Depends(get_current_user),
        db: Database = Depends(get_db),
        service: AnalyticsService = Depends(get_analytics_service),
    ) -> dict:
        return success_response(message=message, data=_run(name, getattr(service, method), db, current_user, window))

    handler.__name__ = f"get_{name}"
    router.add_api_route(f"/{name}", handler, methods=["GET"])


for _name, _method, _msg in (
    ("overview", "overview", "Analytics overview loaded"),
    ("interviews", "interviews", "Interview analytics loaded"),
    ("communication", "communication", "Communication analytics loaded"),
    ("speaking", "speaking", "Speaking analytics loaded"),
    ("pressure", "pressure", "Pressure analytics loaded"),
    ("domains", "domains", "Domain analytics loaded"),
    ("trends", "trends", "Analytics trends loaded"),
    ("readiness", "readiness", "Interview readiness loaded"),
):
    _endpoint(_name, _method, _msg)


@router.get("/insights")
async def get_insights(
    ai_summary: bool = Query(False, description="Add an optional Gemini summary of the computed insights."),
    window: DateRange = Depends(get_range),
    current_user: UserDocument = Depends(get_current_user),
    db: Database = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    try:
        data = await service.insights_with_ai(db, user=current_user, window=window, use_ai=ai_summary)
    except Exception:
        logger.error("Analytics insights failed user_id=%s", current_user["_id"], exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)
    return success_response(message="Analytics insights loaded", data=data)
