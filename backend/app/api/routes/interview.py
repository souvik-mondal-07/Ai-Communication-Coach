"""
Cybersecurity interview simulator routes (Step 9).

    POST /api/v1/interview/sessions
    GET  /api/v1/interview/sessions
    GET  /api/v1/interview/sessions/{session_id}
    POST /api/v1/interview/sessions/{session_id}/answer
    POST /api/v1/interview/sessions/{session_id}/complete

All routes require authentication and only ever touch the caller's own
interviews (the user comes from the JWT — never from the request body). AI is
used only through InterviewService -> QuestionService / EvaluationService ->
the existing AIService; nothing here calls Gemini directly, and no internal
prompts, model output, or stack traces are ever returned.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db, get_interview_service
from app.models.user import UserDocument
from app.schemas.interview import StartInterviewRequest, SubmitAnswerRequest
from app.services.ai.ai_service import AIServiceError
from app.services.interview.evaluation_service import InterviewEvaluationError
from app.services.interview.interview_service import (
    AnswerConflictError,
    InterviewService,
    SessionForbiddenError,
    SessionNotActiveError,
    SessionNotFoundError,
)
from app.services.interview.question_service import QuestionGenerationError
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/interview", tags=["interview"])

MAX_HISTORY_LIMIT = 50

_SESSION_NOT_FOUND = {"message": "Interview session not found.", "error_code": "SESSION_NOT_FOUND"}
_SESSION_FORBIDDEN = {
    "message": "You don't have access to this interview session.",
    "error_code": "SESSION_FORBIDDEN",
}
_SESSION_NOT_ACTIVE = {
    "message": "This interview is no longer active.",
    "error_code": "SESSION_NOT_ACTIVE",
}
_ANSWER_CONFLICT = {
    "message": "This answer was already being processed. Please refresh and try again.",
    "error_code": "ANSWER_CONFLICT",
}
_AI_UNAVAILABLE = {
    "message": "The interviewer is temporarily unavailable. Your answer wasn't lost — please try again.",
    "error_code": "AI_SERVICE_UNAVAILABLE",
}
_UNEXPECTED = {"message": "An unexpected error occurred.", "error_code": "INTERNAL_SERVER_ERROR"}

# Anything from the AI layer becomes a clean 503 — never a stack trace or model output.
_AI_ERRORS = (AIServiceError, QuestionGenerationError, InterviewEvaluationError)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def start_session(
    payload: StartInterviewRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.start_session(
            db,
            user_id=user_id,
            interview_type=payload.interview_type,
            difficulty=payload.difficulty,
            question_count=payload.question_count,
            mode=payload.mode,
            reveal_feedback=payload.reveal_feedback,
        )
    except _AI_ERRORS:
        logger.error("Interview start failed user_id=%s", user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AI_UNAVAILABLE)
    except Exception:
        logger.error("Unexpected error starting interview user_id=%s", user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    logger.info(
        "Interview started user_id=%s type=%s difficulty=%s questions=%d",
        user_id, payload.interview_type, payload.difficulty, payload.question_count,
    )
    return success_response(message="Interview started", data=result)


@router.get("/sessions")
def list_sessions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=MAX_HISTORY_LIMIT),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> dict:
    result = service.list_sessions(db, user_id=str(current_user["_id"]), page=page, limit=limit)
    return success_response(message="Interview history", data=result)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> dict:
    try:
        result = service.get_session(db, user_id=str(current_user["_id"]), session_id=session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    return success_response(message="Interview session", data=result)


@router.post("/sessions/{session_id}/answer")
async def submit_answer(
    session_id: str,
    payload: SubmitAnswerRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.submit_answer(
            db,
            user_id=user_id,
            session_id=session_id,
            answer=payload.answer,
            input_type=payload.input_type,
            audio_metadata=payload.audio_metadata.model_dump() if payload.audio_metadata else None,
            transcript_edited=payload.transcript_edited,
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
        logger.error("Interview answer failed user_id=%s session_id=%s", user_id, session_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AI_UNAVAILABLE)
    except Exception:
        logger.error(
            "Unexpected error submitting interview answer user_id=%s session_id=%s",
            user_id, session_id, exc_info=True,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    # Metadata only — never the answer text.
    logger.info(
        "Interview answer submitted user_id=%s session_id=%s complete=%s",
        user_id, session_id, result["interview_complete"],
    )
    return success_response(message="Answer evaluated", data=result)


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
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
        logger.error("Interview completion failed user_id=%s session_id=%s", user_id, session_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AI_UNAVAILABLE)
    except Exception:
        logger.error(
            "Unexpected error completing interview user_id=%s session_id=%s",
            user_id, session_id, exc_info=True,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    logger.info("Interview ended user_id=%s session_id=%s status=%s", user_id, session_id, result["status"])
    return success_response(message="Interview ended", data={**result, "session": session})
