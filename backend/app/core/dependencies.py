"""
Shared FastAPI dependencies.

`get_current_user` is the single reusable dependency for authenticated
routes — it reads the Authorization header, verifies the JWT, loads the
user from MongoDB, and confirms the account is active. Routes depend on it
instead of re-implementing any of that:

    current_user = Depends(get_current_user)
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.database import Database

from app.core.security import TokenError, decode_access_token
from app.db import mongodb
from app.models.user import UserDocument
from app.services.ai.ai_service import AIService, ai_service
from app.services.auth import auth_service
from app.services.cybersecurity.ctf_service import CtfService, ctf_service
from app.services.cybersecurity.learning_service import LearningService, learning_service
from app.services.cybersecurity.practice_service import PracticeService, practice_service
from app.services.mentor.mentor_service import MentorService, mentor_service

# auto_error=False so a missing header raises our own consistently-shaped
# 401 response instead of FastAPI's default one.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Database:
    """
    FastAPI dependency that returns the MongoDB database, or a clean 503
    error if the database isn't connected — never a raw connection traceback.
    """
    try:
        return mongodb.get_database()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Database is currently unavailable.",
                "error_code": "SERVICE_UNAVAILABLE",
            },
        ) from exc


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"message": message, "error_code": "UNAUTHORIZED"},
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Database = Depends(get_db),
) -> UserDocument:
    """
    Resolve the authenticated user from a Bearer JWT.

    Raises a 401 if the header is missing, the token is invalid/expired, the
    user no longer exists, or the account has been deactivated.
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Authentication credentials were not provided.")

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise _unauthorized(str(exc)) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Invalid token payload.")

    user = auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise _unauthorized("User no longer exists.")

    if not user.get("is_active", True):
        raise _unauthorized("This account has been deactivated.")

    return user


def get_ai_service() -> AIService:
    """
    FastAPI dependency for the AI service singleton.

    Routing this through a dependency (rather than importing `ai_service`
    directly) lets tests swap in a fake/mocked service via
    `app.dependency_overrides` without making real Gemini calls.
    """
    return ai_service


def get_mentor_service() -> MentorService:
    """
    FastAPI dependency for the mentor service singleton — same rationale as
    `get_ai_service`: lets tests override it with a fake in isolation.
    """
    return mentor_service


def get_learning_service() -> LearningService:
    """FastAPI dependency for the cybersecurity learning service singleton."""
    return learning_service


def get_practice_service() -> PracticeService:
    """
    FastAPI dependency for the cybersecurity practice service singleton —
    lets tests override it with a fake, same as `get_ai_service`/`get_mentor_service`.
    """
    return practice_service


def get_ctf_service() -> CtfService:
    """FastAPI dependency for the CTF & practical lab mentor service singleton."""
    return ctf_service
