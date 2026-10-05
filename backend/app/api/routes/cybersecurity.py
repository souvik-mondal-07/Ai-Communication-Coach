"""
Cybersecurity learning & practice routes.

    GET  /api/v1/cybersecurity/topics
    GET  /api/v1/cybersecurity/topics/{slug}
    POST /api/v1/cybersecurity/practice/start                       (Step 5: one topic)
    GET  /api/v1/cybersecurity/practice/config                      (Step 17: modes, categories, limits)
    POST /api/v1/cybersecurity/practice/sessions                    (Step 17: advanced session)
    GET  /api/v1/cybersecurity/practice/{session_id}                (Step 17: state / resume / summary)
    POST /api/v1/cybersecurity/practice/{session_id}/hint           (Step 17: progressive hints)
    POST /api/v1/cybersecurity/practice/{session_id}/next           (Step 17: next question)
    POST /api/v1/cybersecurity/practice/{session_id}/answer         (extended for Step 17 sessions)
    POST /api/v1/cybersecurity/practice/{session_id}/complete       (extended for Step 17 sessions)
    GET  /api/v1/cybersecurity/practice/history
    GET  /api/v1/cybersecurity/progress

All routes require authentication (consistent with the rest of the app).
AI is only used for question generation and short-answer evaluation, both
delegated to PracticeService — never called directly from this file.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.core.dependencies import (
    get_current_user,
    get_db,
    get_learning_service,
    get_practice_service,
)
from app.models.user import UserDocument
from app.schemas.cybersecurity import (
    AnswerSubmitRequest,
    HintRequest,
    PracticeSessionCreate,
    PracticeStartRequest,
)
from app.services.cybersecurity.learning_service import LearningService
from app.services.cybersecurity.practice_service import (
    AnswerAlreadySubmittedError,
    AnswerEvaluationError,
    HintLimitError,
    InvalidPracticeConfigError,
    PracticeGenerationError,
    PracticeService,
    QuestionNotFoundError,
    QuestionNotReadyError,
    SessionClosedError,
    SessionForbiddenError,
    SessionNotFoundError,
    TopicNotFoundError,
)
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/cybersecurity", tags=["cybersecurity"])

MAX_HISTORY_LIMIT = 50

_TOPIC_NOT_FOUND = {"message": "Topic not found.", "error_code": "TOPIC_NOT_FOUND"}
_SESSION_NOT_FOUND = {"message": "Practice session not found.", "error_code": "SESSION_NOT_FOUND"}
_SESSION_FORBIDDEN = {
    "message": "You don't have access to this practice session.",
    "error_code": "SESSION_FORBIDDEN",
}
_QUESTION_NOT_FOUND = {"message": "Question not found in this session.", "error_code": "QUESTION_NOT_FOUND"}
_GENERATION_FAILED = {
    "message": "Unable to generate practice questions. Please try again.",
    "error_code": "AI_SERVICE_UNAVAILABLE",
}
_EVALUATION_FAILED = {
    "message": "Unable to evaluate your answer. Please try again.",
    "error_code": "AI_SERVICE_UNAVAILABLE",
}
_UNEXPECTED = {"message": "An unexpected error occurred.", "error_code": "INTERNAL_SERVER_ERROR"}
_ALREADY_ANSWERED = {
    "message": "This question has already been answered.",
    "error_code": "ANSWER_ALREADY_SUBMITTED",
}
_SESSION_CLOSED = {"message": "This practice session is already complete.", "error_code": "SESSION_CLOSED"}
_SESSION_EXPIRED = {"message": "Time is up. Your answers were saved.", "error_code": "SESSION_EXPIRED"}


# --- Topics --------------------------------------------------------------


@router.get("/topics")
def list_topics(
    category: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> dict:
    topics = service.list_topics(db, category=category, difficulty=difficulty)
    return success_response(message="Topics retrieved", data={"topics": topics})


@router.get("/topics/{slug}")
def get_topic(
    slug: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> dict:
    topic = service.get_topic_by_slug(db, slug)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_TOPIC_NOT_FOUND)
    return success_response(message="Topic retrieved", data={"topic": topic})


# --- Practice --------------------------------------------------------------


@router.post("/practice/start")
async def start_practice(
    payload: PracticeStartRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PracticeService = Depends(get_practice_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.start_session(
            db,
            user_id=user_id,
            topic_slug=payload.topic_slug,
            difficulty=payload.difficulty,
            question_count=payload.question_count,
        )
    except TopicNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_TOPIC_NOT_FOUND)
    except PracticeGenerationError:
        logger.error("Practice question generation failed user_id=%s", user_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_GENERATION_FAILED)
    except Exception:
        logger.error("Unexpected error starting practice user_id=%s", user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    logger.info(
        "Practice session started user_id=%s topic=%s questions=%d",
        user_id, payload.topic_slug, len(result["questions"]),
    )
    return success_response(message="Practice session started", data=result)


@router.post("/practice/{session_id}/answer")
async def submit_answer(
    session_id: str,
    payload: AnswerSubmitRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PracticeService = Depends(get_practice_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.submit_answer(
            db,
            user_id=user_id,
            session_id=session_id,
            question_id=payload.question_id,
            answer=payload.answer,
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    except QuestionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_QUESTION_NOT_FOUND)
    except AnswerAlreadySubmittedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_ALREADY_ANSWERED)
    except SessionClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_SESSION_EXPIRED if exc.expired else _SESSION_CLOSED,
        )
    except AnswerEvaluationError:
        logger.error("Answer evaluation failed user_id=%s session_id=%s", user_id, session_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_EVALUATION_FAILED)
    except Exception:
        logger.error("Unexpected error submitting answer user_id=%s", user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    return success_response(message="Answer submitted", data=result.to_public_dict())


@router.post("/practice/{session_id}/complete")
def complete_practice(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PracticeService = Depends(get_practice_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = service.complete_session(db, user_id=user_id, session_id=session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)

    logger.info(
        "Practice session completed user_id=%s session_id=%s score=%d",
        user_id, session_id, result["score"],
    )
    return success_response(message="Practice session completed", data=result)


@router.get("/practice/history")
def get_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=MAX_HISTORY_LIMIT),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PracticeService = Depends(get_practice_service),
) -> dict:
    result = service.get_history(db, user_id=str(current_user["_id"]), page=page, limit=limit)
    return success_response(message="Practice history retrieved", data=result)


@router.get("/progress")
def get_progress(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PracticeService = Depends(get_practice_service),
) -> dict:
    result = service.get_progress(db, user_id=str(current_user["_id"]))
    return success_response(message="Progress retrieved", data=result)


# --- Step 17: advanced practice engine ---------------------------------------------


def _conflict(message: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail={"message": message, "error_code": code}
    )


@router.get("/practice/config")
def get_practice_config(
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PracticeService = Depends(get_practice_service),
) -> dict:
    """What the practice page can offer. Reads the topic catalogue only -- never calls the AI."""
    return success_response(message="Practice configuration retrieved", data=service.get_config(db))


@router.post("/practice/sessions")
async def start_advanced_practice(
    payload: PracticeSessionCreate,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PracticeService = Depends(get_practice_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.start_advanced_session(
            db,
            user_id=user_id,
            mode=payload.mode,
            category=payload.category,
            topic_slug=payload.topic_slug,
            difficulty=payload.difficulty,
            question_type=payload.question_type,
            question_count=payload.question_count,
            time_limit_minutes=payload.time_limit_minutes,
        )
    except InvalidPracticeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "error_code": "INVALID_PRACTICE_CONFIG"},
        )
    except PracticeGenerationError:
        logger.error("Advanced practice generation failed user_id=%s", user_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_GENERATION_FAILED)
    except Exception:
        logger.error("Unexpected error starting advanced practice user_id=%s", user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    logger.info(
        "Advanced practice started user_id=%s mode=%s categories=%s questions=%d",
        user_id, payload.mode, result.get("categories"), result["question_count"],
    )
    return success_response(message="Practice session started", data=result)


@router.get("/practice/{session_id}")
def get_practice_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PracticeService = Depends(get_practice_service),
) -> dict:
    """Current state of one of the caller's sessions (resume after refresh, or the final summary)."""
    try:
        result = service.get_session(db, user_id=str(current_user["_id"]), session_id=session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    return success_response(message="Practice session retrieved", data=result)


@router.post("/practice/{session_id}/hint")
def request_practice_hint(
    session_id: str,
    payload: HintRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PracticeService = Depends(get_practice_service),
) -> dict:
    try:
        result = service.request_hint(
            db,
            user_id=str(current_user["_id"]),
            session_id=session_id,
            question_id=payload.question_id,
            reveal=payload.reveal,
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    except QuestionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_QUESTION_NOT_FOUND)
    except AnswerAlreadySubmittedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_ALREADY_ANSWERED)
    except SessionClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_SESSION_EXPIRED if exc.expired else _SESSION_CLOSED,
        )
    except HintLimitError as exc:
        raise _conflict(str(exc), exc.code)
    return success_response(message="Hint retrieved", data=result)


@router.post("/practice/{session_id}/next")
async def next_practice_question(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: PracticeService = Depends(get_practice_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.next_question(db, user_id=user_id, session_id=session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    except SessionClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_SESSION_EXPIRED if exc.expired else _SESSION_CLOSED,
        )
    except QuestionNotReadyError as exc:
        raise _conflict(str(exc), exc.code)
    except PracticeGenerationError:
        logger.error("Next-question generation failed user_id=%s session_id=%s", user_id, session_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_GENERATION_FAILED)
    except Exception:
        logger.error("Unexpected error loading next question user_id=%s", user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)
    return success_response(message="Next question ready", data=result)
