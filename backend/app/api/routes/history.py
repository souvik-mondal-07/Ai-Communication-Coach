"""
History & Activity Center routes (Step 15).

    GET /api/v1/history                      paginated, filterable activity list
    GET /api/v1/history/summary              all-time counts per activity type
    GET /api/v1/history/{type}/{id}          one activity's detail

Thin by design: all querying/normalizing lives in `HistoryService`. Every route
identifies the user from the JWT only -- there is intentionally no `user_id`
parameter anywhere.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db, get_history_service
from app.models.user import UserDocument
from app.schemas.history import ActivityType, HistoryDetailResponse
from app.services.history.history_service import (
    MAX_LIMIT,
    ActivityNotFoundError,
    HistoryService,
    InvalidDateRangeError,
    PageOutOfRangeError,
    SortOrder,
)
from app.utils.helpers import success_response

router = APIRouter(prefix="/history", tags=["history"])


def _error(code: int, message: str, error_code: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"message": message, "error_code": error_code})


@router.get("")
def list_history(
    type: ActivityType | None = Query(default=None, description="Filter to one activity type."),
    search: str | None = Query(default=None, max_length=100),
    start_date: datetime | None = Query(default=None, description="Inclusive, ISO 8601."),
    end_date: datetime | None = Query(default=None, description="Inclusive, ISO 8601."),
    sort: SortOrder = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service),
) -> dict:
    try:
        result = service.list_activities(
            db,
            user_id=str(current_user["_id"]),
            activity_type=type,
            search=search,
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=limit,
            sort=sort,
        )
    except InvalidDateRangeError:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "The start date must be before the end date.",
            "INVALID_DATE_RANGE",
        )
    except PageOutOfRangeError:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "That page is too far back. Use search or a date filter to narrow your history.",
            "PAGE_OUT_OF_RANGE",
        )
    return success_response(message="History retrieved", data=result.model_dump(mode="json"))


@router.get("/summary")
def history_summary(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service),
) -> dict:
    result = service.get_summary(db, user_id=str(current_user["_id"]))
    return success_response(message="History summary retrieved", data=result.model_dump(mode="json"))


@router.get("/{activity_type}/{activity_id}")
def get_activity(
    activity_type: ActivityType,
    activity_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service),
) -> dict:
    try:
        activity, detail = service.get_detail(
            db,
            user_id=str(current_user["_id"]),
            activity_type=activity_type,
            activity_id=activity_id,
        )
    except ActivityNotFoundError:
        raise _error(status.HTTP_404_NOT_FOUND, "Activity not found.", "ACTIVITY_NOT_FOUND")
    payload = HistoryDetailResponse(activity=activity, detail=detail)
    return success_response(message="Activity retrieved", data=payload.model_dump(mode="json"))
