"""
Progress & Personal AI Profile routes (Step 11).

    GET  /api/v1/progress/overview
    GET  /api/v1/progress/skills
    GET  /api/v1/progress/trends
    GET  /api/v1/progress/weaknesses
    GET  /api/v1/progress/recommendations
    POST /api/v1/progress/recommendations/{recommendation_id}/complete
    POST /api/v1/progress/recalculate
    GET  /api/v1/progress/activity
    GET  /api/v1/progress/profile

Every route requires authentication and only ever reads/writes the caller's
own data: the user always comes from the JWT (`current_user["_id"]`), never
from a query parameter or request body -- there is no `user_id` a client can
pass to see someone else's progress (spec section 27).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db, get_progress_service
from app.models.user import UserDocument
from app.schemas.progress import ALLOWED_TREND_PERIODS
from app.services.progress.progress_service import (
    ProgressService,
    RecommendationForbiddenError,
    RecommendationNotFoundError,
)
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/progress", tags=["progress"])

_RECOMMENDATION_NOT_FOUND = {
    "message": "Recommendation not found.",
    "error_code": "RECOMMENDATION_NOT_FOUND",
}
_RECOMMENDATION_FORBIDDEN = {
    "message": "You don't have access to this recommendation.",
    "error_code": "RECOMMENDATION_FORBIDDEN",
}
_UNEXPECTED = {"message": "An unexpected error occurred.", "error_code": "INTERNAL_SERVER_ERROR"}


def _serialize_dates(value):
    """Recursively convert datetimes to ISO strings so the JSON response is well-formed."""
    from datetime import datetime

    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize_dates(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_dates(v) for v in value]
    return value


@router.get("/overview")
def get_overview(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> dict:
    result = service.get_overview(db, user_id=str(current_user["_id"]))
    return success_response(message="Progress overview", data=_serialize_dates(result))


@router.get("/skills")
def get_skills(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> dict:
    result = service.get_skills(db, user_id=str(current_user["_id"]))
    return success_response(message="Skill breakdown", data=_serialize_dates(result))


@router.get("/trends")
def get_trends(
    period: str = Query(default="30d"),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> dict:
    if period not in ALLOWED_TREND_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"period must be one of: {', '.join(ALLOWED_TREND_PERIODS)}",
                "error_code": "VALIDATION_ERROR",
            },
        )
    result = service.get_trends(db, user_id=str(current_user["_id"]), period=period)
    return success_response(message="Progress trends", data=_serialize_dates(result))


@router.get("/weaknesses")
def get_weaknesses(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> dict:
    result = service.get_weaknesses(db, user_id=str(current_user["_id"]))
    return success_response(message="Detected weaknesses", data=_serialize_dates(result))


@router.get("/recommendations")
def get_recommendations(
    active_only: bool = Query(default=True),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> dict:
    result = service.get_recommendations(db, user_id=str(current_user["_id"]), active_only=active_only)
    return success_response(message="Recommendations", data=_serialize_dates(result))


@router.post("/recommendations/{recommendation_id}/complete")
def complete_recommendation(
    recommendation_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = service.complete_recommendation(db, user_id=user_id, recommendation_id=recommendation_id)
    except RecommendationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_RECOMMENDATION_NOT_FOUND)
    except RecommendationForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_RECOMMENDATION_FORBIDDEN)
    return success_response(message="Recommendation marked complete", data=_serialize_dates(result))


@router.post("/recalculate")
async def recalculate(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.recalculate(db, user_id=user_id)
    except Exception:
        logger.error("Progress recalculation failed user_id=%s", user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    logger.info("Progress recalculated user_id=%s", user_id)
    return success_response(message="Progress recalculated", data=result)


@router.get("/activity")
def get_activity(
    limit: int = Query(default=15, ge=1, le=50),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> dict:
    result = service.get_activity(db, user_id=str(current_user["_id"]), limit=limit)
    return success_response(message="Recent activity", data=_serialize_dates(result))


@router.get("/profile")
def get_profile(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> dict:
    result = service.get_profile(db, user_id=str(current_user["_id"]))
    return success_response(message="Personal AI profile", data=_serialize_dates(result))
