"""
Profile & account management routes (Step 14).

    GET   /api/v1/users/me
    PATCH /api/v1/users/me
    GET   /api/v1/users/me/preferences
    PATCH /api/v1/users/me/preferences
    POST  /api/v1/users/me/change-password

Every route resolves the user from the JWT through `get_current_user`. No route
accepts a user id: the document that is read or written is always the one
belonging to the authenticated caller, so one user cannot touch another's data.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db
from app.core.security import verify_password
from app.models.user import UserDocument
from app.schemas.auth import PASSWORD_MIN_LENGTH
from app.schemas.user import (
    ChangePasswordRequest,
    UserPreferencesUpdate,
    UserProfileUpdate,
)
from app.services.auth import auth_service, profile_service
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def _bad_request(message: str, error_code: str) -> HTTPException:
    # 400, never 401: the frontend treats any 401 as an expired session and signs the user out.
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"message": message, "error_code": error_code},
    )


def _apply_update(db: Database, user: UserDocument, fields: dict) -> UserDocument:
    if not fields:  # nothing sent — nothing to write
        return user
    updated = auth_service.update_user_fields(db, user["_id"], fields)
    if updated is None:  # deleted between auth and write
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Account not found.", "error_code": "NOT_FOUND"},
        )
    return updated


@router.get("/me")
def get_profile(current_user: UserDocument = Depends(get_current_user)) -> dict:
    profile = profile_service.to_profile_response(current_user)
    return success_response(message="Profile loaded", data={"user": profile.model_dump(mode="json")})


@router.patch("/me")
def update_profile(
    payload: UserProfileUpdate,
    current_user: UserDocument = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    updated = _apply_update(db, current_user, profile_service.build_profile_update(payload))
    profile = profile_service.to_profile_response(updated)
    return success_response(message="Profile updated", data={"user": profile.model_dump(mode="json")})


@router.get("/me/preferences")
def get_preferences(current_user: UserDocument = Depends(get_current_user)) -> dict:
    preferences = profile_service.to_profile_response(current_user).preferences
    return success_response(message="Preferences loaded", data={"preferences": preferences.model_dump(mode="json")})


@router.patch("/me/preferences")
def update_preferences(
    payload: UserPreferencesUpdate,
    current_user: UserDocument = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    updated = _apply_update(db, current_user, profile_service.build_preferences_update(payload))
    preferences = profile_service.to_profile_response(updated).preferences
    return success_response(message="Preferences updated", data={"preferences": preferences.model_dump(mode="json")})


@router.post("/me/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: UserDocument = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    # Cheap input checks first, then the (slow) Argon2 verification.
    if payload.new_password != payload.confirm_new_password:
        raise _bad_request("New passwords do not match.", "PASSWORD_MISMATCH")
    if len(payload.new_password) < PASSWORD_MIN_LENGTH:
        raise _bad_request(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters.", "PASSWORD_TOO_SHORT"
        )

    if not verify_password(payload.current_password, current_user["password_hash"]):
        raise _bad_request("Current password is incorrect.", "INVALID_CURRENT_PASSWORD")

    if payload.new_password == payload.current_password:
        raise _bad_request(
            "New password must be different from the current password.", "PASSWORD_UNCHANGED"
        )

    auth_service.update_password(db, current_user["_id"], payload.new_password)
    # Log the event only — never the passwords or the hash.
    logger.info("Password changed for user: %s", str(current_user["_id"]))
    return success_response(message="Password changed successfully")
