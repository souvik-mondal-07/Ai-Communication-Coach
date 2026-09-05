"""
Authentication routes.

    POST /api/v1/auth/register
    POST /api/v1/auth/login
    GET  /api/v1/auth/me
    POST /api/v1/auth/logout
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db
from app.core.security import create_access_token
from app.models.user import UserDocument
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth import auth_service
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_ALREADY_EXISTS = {
    "message": "An account with this email already exists",
    "error_code": "EMAIL_ALREADY_EXISTS",
}

_INVALID_CREDENTIALS = {
    "message": "Invalid email or password",
    "error_code": "INVALID_CREDENTIALS",
}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Database = Depends(get_db)) -> dict:
    # Fast, common-case check. The unique index on `email` (see
    # auth_service.ensure_indexes) is what actually prevents a race between
    # two concurrent registrations — this is just a friendlier first check.
    if auth_service.get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_EMAIL_ALREADY_EXISTS)

    try:
        user = auth_service.create_user(
            db, name=payload.name, email=payload.email, password=payload.password
        )
    except auth_service.EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_EMAIL_ALREADY_EXISTS) from exc

    public_user = auth_service.to_public_user(user)
    logger.info("New user registered: %s", public_user["id"])

    return success_response(message="Registration successful", data={"user": public_user})


@router.post("/login")
def login(payload: LoginRequest, db: Database = Depends(get_db)) -> dict:
    user = auth_service.authenticate_user(db, email=payload.email, password=payload.password)
    if user is None:
        # Deliberately identical error whether the email doesn't exist, the
        # password is wrong, or the account is inactive.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)

    access_token = create_access_token(subject=str(user["_id"]))
    logger.info("User logged in: %s", str(user["_id"]))

    return success_response(
        message="Login successful",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": auth_service.to_public_user(user),
        },
    )


@router.get("/me")
def get_me(current_user: UserDocument = Depends(get_current_user)) -> dict:
    return success_response(
        message="Authenticated user",
        data={"user": auth_service.to_public_user(current_user)},
    )


@router.post("/logout")
def logout(current_user: UserDocument = Depends(get_current_user)) -> dict:
    # Access tokens are stateless JWTs in this step, so there is nothing to
    # revoke server-side yet — the client discards the token. A revocation
    # store (denylist) or refresh-token flow can be layered in later without
    # changing this endpoint's shape.
    logger.info("User logged out: %s", str(current_user["_id"]))
    return success_response(message="Logged out successfully. Discard the client-side token.")
