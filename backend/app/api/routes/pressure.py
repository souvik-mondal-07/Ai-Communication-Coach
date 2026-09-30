"""
Pressure & Nervousness Training routes (Step 10).

    GET  /api/v1/pressure/config
    POST /api/v1/pressure/sessions
    GET  /api/v1/pressure/sessions
    GET  /api/v1/pressure/sessions/{session_id}
    POST /api/v1/pressure/sessions/{session_id}/response
    POST /api/v1/pressure/sessions/{session_id}/complete
    POST /api/v1/pressure/sessions/{session_id}/self-report

All routes require authentication and only ever touch the caller's own
sessions (the user comes from the JWT -- never the request body). This is a
training system, not a diagnostic one: no response here ever states or
implies a mental-health conclusion about the user -- see
`app.services.pressure.evaluation_service`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db, get_pressure_service
from app.models.user import UserDocument
from app.schemas.pressure import (
    SelfReportRequest,
    StartPressureSessionRequest,
    SubmitPressureResponseRequest,
)
from app.services.ai.ai_service import AIServiceError
from app.services.interview.evaluation_service import InterviewEvaluationError
from app.services.interview.question_service import QuestionGenerationError
from app.services.pressure.pressure_config import public_levels
from app.services.pressure.pressure_service import (
    AnswerConflictError,
    PressureService,
    SessionForbiddenError,
    SessionNotActiveError,
    SessionNotFoundError,
)
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pressure", tags=["pressure"])

MAX_HISTORY_LIMIT = 50

_SESSION_NOT_FOUND = {"message": "Pressure training session not found.", "error_code": "SESSION_NOT_FOUND"}
_SESSION_FORBIDDEN = {
    "message": "You don't have access to this pressure training session.",
    "error_code": "SESSION_FORBIDDEN",
}
_SESSION_NOT_ACTIVE = {
    "message": "This pressure training session is no longer active.",
    "error_code": "SESSION_NOT_ACTIVE",
}
_ANSWER_CONFLICT = {
    "message": "This response was already being processed. Please refresh and try again.",
    "error_code": "ANSWER_CONFLICT",
}
_AI_UNAVAILABLE = {
    "message": "The trainer is temporarily unavailable. Your answer wasn't lost -- please try again.",
    "error_code": "AI_SERVICE_UNAVAILABLE",
}
_UNEXPECTED = {"message": "An unexpected error occurred.", "error_code": "INTERNAL_SERVER_ERROR"}

# Anything from the AI layer becomes a clean 503 -- never a stack trace or model output.
_AI_ERRORS = (AIServiceError, QuestionGenerationError, InterviewEvaluationError)


@router.get("/config")
def get_config(_: UserDocument = Depends(get_current_user)) -> dict:
    """Pressure-level descriptions for the setup screen (no internal probabilities)."""
    return success_response(message="Pressure levels", data={"levels": public_levels()})


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def start_session(
    payload: StartPressureSessionRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PressureService = Depends(get_pressure_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.start_session(
            db,
            user_id=user_id,
            pressure_level=payload.pressure_level,
            mode=payload.mode,
            interview_type=payload.interview_type,
            difficulty=payload.difficulty,
            question_count=payload.question_count,
            input_mode=payload.input_mode,
        )
    except _AI_ERRORS:
        logger.error("Pressure session start failed user_id=%s", user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AI_UNAVAILABLE)
    except Exception:
        logger.error("Unexpected error starting pressure session user_id=%s", user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    logger.info(
        "Pressure session started user_id=%s level=%d mode=%s questions=%d",
        user_id, payload.pressure_level, payload.mode, payload.question_count,
    )
    return success_response(message="Pressure training session started", data=result)


@router.get("/sessions")
def list_sessions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=MAX_HISTORY_LIMIT),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PressureService = Depends(get_pressure_service),
) -> dict:
    result = service.list_sessions(db, user_id=str(current_user["_id"]), page=page, limit=limit)
    return success_response(message="Pressure training history", data=result)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PressureService = Depends(get_pressure_service),
) -> dict:
    try:
        result = service.get_session(db, user_id=str(current_user["_id"]), session_id=session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    return success_response(message="Pressure training session", data=result)


@router.post("/sessions/{session_id}/response")
async def submit_response(
    session_id: str,
    payload: SubmitPressureResponseRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PressureService = Depends(get_pressure_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.submit_response(
            db,
            user_id=user_id,
            session_id=session_id,
            answer=payload.answer,
            input_type=payload.input_type,
            audio_metadata=payload.audio_metadata.model_dump() if payload.audio_metadata else None,
            transcript_edited=payload.transcript_edited,
            response_duration_seconds=payload.response_duration_seconds,
            timed_out=payload.timed_out,
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    except SessionNotActiveError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_SESSION_NOT_ACTIVE)
    except AnswerConflictError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_ANSWER_CONFLICT)
    except _AI_ERRORS:
        # Nothing was saved, so the user can resubmit the same answer.
        logger.error("Pressure response failed user_id=%s session_id=%s", user_id, session_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AI_UNAVAILABLE)
    except Exception:
        logger.error(
            "Unexpected error submitting pressure response user_id=%s session_id=%s",
            user_id, session_id, exc_info=True,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    # Metadata only -- never the answer text.
    logger.info(
        "Pressure response submitted user_id=%s session_id=%s complete=%s",
        user_id, session_id, result["session_complete"],
    )
    return success_response(message="Response recorded", data=result)


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PressureService = Depends(get_pressure_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.complete_session(db, user_id=user_id, session_id=session_id)
        session = service.get_session(db, user_id=user_id, session_id=session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    except _AI_ERRORS:
        logger.error("Pressure completion failed user_id=%s session_id=%s", user_id, session_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AI_UNAVAILABLE)
    except Exception:
        logger.error(
            "Unexpected error completing pressure session user_id=%s session_id=%s",
            user_id, session_id, exc_info=True,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    logger.info("Pressure session ended user_id=%s session_id=%s status=%s", user_id, session_id, result["status"])
    return success_response(message="Pressure training session ended", data={**result, "session": session})


@router.post("/sessions/{session_id}/self-report")
def submit_self_report(
    session_id: str,
    payload: SelfReportRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PressureService = Depends(get_pressure_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = service.submit_self_report(
            db, user_id=user_id, session_id=session_id, difficulty=payload.difficulty, note=payload.note
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    return success_response(message="Self-report saved", data=result)
