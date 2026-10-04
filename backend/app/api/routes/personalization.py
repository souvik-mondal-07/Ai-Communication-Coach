"""
Personalization routes (Step 16).

    GET /api/v1/personalization/profile
    GET /api/v1/personalization/recommendations
    GET /api/v1/personalization/weaknesses

Authenticated, read-only. The user always comes from the JWT; there is no
`user_id` parameter a client could use to read someone else's data.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db, get_personalization_service
from app.models.user import UserDocument
from app.services.personalization.personalization_service import PersonalizationService
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/personalization", tags=["personalization"])

_UNEXPECTED = {"message": "An unexpected error occurred.", "error_code": "INTERNAL_SERVER_ERROR"}


def _run(label: str, fn, db: Database, user: UserDocument):
    try:
        return fn(db, user=user)
    except Exception:
        logger.error("Personalization %s failed user_id=%s", label, user["_id"], exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)


@router.get("/profile")
def get_profile(
    current_user: UserDocument = Depends(get_current_user),
    db: Database = Depends(get_db),
    service: PersonalizationService = Depends(get_personalization_service),
) -> dict:
    data = _run("profile", service.get_profile, db, current_user)
    return success_response(message="Personalization profile loaded", data=data)


@router.get("/recommendations")
def get_recommendations(
    current_user: UserDocument = Depends(get_current_user),
    db: Database = Depends(get_db),
    service: PersonalizationService = Depends(get_personalization_service),
) -> dict:
    data = _run("recommendations", service.get_recommendations, db, current_user)
    return success_response(message="Recommendations loaded", data=data)


@router.get("/weaknesses")
def get_weaknesses(
    current_user: UserDocument = Depends(get_current_user),
    db: Database = Depends(get_db),
    service: PersonalizationService = Depends(get_personalization_service),
) -> dict:
    data = _run("weaknesses", service.get_weaknesses, db, current_user)
    return success_response(message="Weaknesses loaded", data=data)
