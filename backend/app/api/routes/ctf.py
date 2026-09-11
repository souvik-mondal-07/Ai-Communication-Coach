"""
CTF & Practical Lab Mentor routes.

    POST /api/v1/ctf/sessions
    GET  /api/v1/ctf/sessions
    GET  /api/v1/ctf/sessions/{session_id}
    POST /api/v1/ctf/sessions/{session_id}/chat
    GET  /api/v1/ctf/sessions/{session_id}/hint
    POST /api/v1/ctf/sessions/{session_id}/complete

An AI-guidance system only: it never scans, attacks, or accesses anything
itself. All routes require authentication and enforce that a session only
ever belongs to its creator. AI calls are delegated entirely to CtfService,
which uses the existing AIService — never a second Gemini client.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.core.dependencies import get_ctf_service, get_current_user, get_db
from app.models.user import UserDocument
from app.schemas.ctf import CompleteSessionRequest, CreateSessionRequest, CtfChatRequest
from app.services.cybersecurity.ctf_service import (
    CtfService,
    HintLockedError,
    SessionForbiddenError,
    SessionNotFoundError,
)
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ctf", tags=["ctf"])

MAX_HISTORY_LIMIT = 50
_VALID_HINT_LEVELS = {"hint_1", "hint_2", "hint_3", "solution"}

_SESSION_NOT_FOUND = {"message": "CTF session not found.", "error_code": "SESSION_NOT_FOUND"}
_SESSION_FORBIDDEN = {
    "message": "You don't have access to this CTF session.",
    "error_code": "SESSION_FORBIDDEN",
}
_HINT_LOCKED = {
    "message": "Request the previous hint level first, or pass force=true to skip ahead.",
    "error_code": "HINT_LOCKED",
}
_AI_UNAVAILABLE = {
    "message": "AI service is temporarily unavailable.",
    "error_code": "AI_SERVICE_UNAVAILABLE",
}
_UNEXPECTED = {"message": "An unexpected error occurred.", "error_code": "INTERNAL_SERVER_ERROR"}


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: CreateSessionRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CtfService = Depends(get_ctf_service),
) -> dict:
    user_id = str(current_user["_id"])
    result = service.create_session(db, user_id=user_id, payload=payload)
    logger.info("CTF session created user_id=%s category=%s", user_id, payload.category)
    return success_response(message="Challenge session created", data=result)


@router.get("/sessions")
def list_sessions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=MAX_HISTORY_LIMIT),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CtfService = Depends(get_ctf_service),
) -> dict:
    result = service.list_sessions(db, user_id=str(current_user["_id"]), page=page, limit=limit)
    return success_response(message="CTF sessions retrieved", data=result)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CtfService = Depends(get_ctf_service),
) -> dict:
    try:
        result = service.get_session(db, user_id=str(current_user["_id"]), session_id=session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    return success_response(message="CTF session retrieved", data=result)


@router.post("/sessions/{session_id}/chat")
async def chat(
    session_id: str,
    payload: CtfChatRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CtfService = Depends(get_ctf_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        response_text = await service.chat(
            db, user_id=user_id, session_id=session_id, message=payload.message
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    except Exception:
        logger.error("CTF chat failed user_id=%s session_id=%s", user_id, session_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AI_UNAVAILABLE)

    return success_response(message="Mentor response generated", data={"response": response_text})


@router.get("/sessions/{session_id}/hint")
async def get_hint(
    session_id: str,
    level: str = Query(..., description="hint_1 | hint_2 | hint_3 | solution"),
    force: bool = Query(default=False),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CtfService = Depends(get_ctf_service),
) -> dict:
    if level not in _VALID_HINT_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "level must be one of hint_1, hint_2, hint_3, solution.",
                "error_code": "VALIDATION_ERROR",
            },
        )

    user_id = str(current_user["_id"])
    try:
        result = await service.get_hint(
            db, user_id=user_id, session_id=session_id, level=level, force=force
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    except HintLockedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_HINT_LOCKED)
    except Exception:
        logger.error("CTF hint generation failed user_id=%s session_id=%s", user_id, session_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AI_UNAVAILABLE)

    return success_response(message="Hint retrieved", data=result)


@router.post("/sessions/{session_id}/complete")
def complete_session(
    session_id: str,
    payload: CompleteSessionRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CtfService = Depends(get_ctf_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = service.complete_session(
            db, user_id=user_id, session_id=session_id, flag=payload.flag
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)

    logger.info("CTF session completed user_id=%s session_id=%s", user_id, session_id)
    return success_response(message="Challenge marked complete", data=result)
