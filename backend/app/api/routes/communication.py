"""
Communication coach routes.

    GET  /api/v1/communication/scenarios
    GET  /api/v1/communication/scenarios/{slug}
    POST /api/v1/communication/sessions
    POST /api/v1/communication/sessions/{session_id}/message
    POST /api/v1/communication/sessions/{session_id}/complete
    GET  /api/v1/communication/sessions/{session_id}
    GET  /api/v1/communication/sessions

All routes require authentication. AI is only used for roleplay chat and
conversation evaluation, both delegated to CommunicationService/
EvaluationService — never called directly from this file.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.core.dependencies import (
    get_communication_service,
    get_current_user,
    get_db,
    get_evaluation_service,
)
from app.models.user import UserDocument
from app.schemas.communication import SendMessageRequest, StartSessionRequest
from app.services.communication.communication_service import (
    CommunicationService,
    ScenarioNotFoundError,
    SessionCompletedError,
    SessionForbiddenError,
    SessionNotFoundError,
)
from app.services.communication.evaluation_service import EvaluationError, EvaluationService
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/communication", tags=["communication"])

MAX_HISTORY_LIMIT = 50

_SCENARIO_NOT_FOUND = {"message": "Scenario not found.", "error_code": "SCENARIO_NOT_FOUND"}
_SESSION_NOT_FOUND = {
    "message": "Communication session not found.",
    "error_code": "SESSION_NOT_FOUND",
}
_SESSION_FORBIDDEN = {
    "message": "You don't have access to this communication session.",
    "error_code": "SESSION_FORBIDDEN",
}
_SESSION_COMPLETED = {
    "message": "This session has already been completed.",
    "error_code": "SESSION_COMPLETED",
}
_AI_UNAVAILABLE = {
    "message": "AI service is temporarily unavailable.",
    "error_code": "AI_SERVICE_UNAVAILABLE",
}
_UNEXPECTED = {"message": "An unexpected error occurred.", "error_code": "INTERNAL_SERVER_ERROR"}


# --- Scenarios -----------------------------------------------------------


@router.get("/scenarios")
def list_scenarios(
    category: str | None = Query(default=None),
    mode: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CommunicationService = Depends(get_communication_service),
) -> dict:
    scenarios = service.list_scenarios(db, category=category, mode=mode, difficulty=difficulty)
    return success_response(message="Scenarios retrieved", data={"scenarios": scenarios})


@router.get("/scenarios/{slug}")
def get_scenario(
    slug: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CommunicationService = Depends(get_communication_service),
) -> dict:
    scenario = service.get_scenario_by_slug(db, slug)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SCENARIO_NOT_FOUND)
    return success_response(message="Scenario retrieved", data={"scenario": scenario})


# --- Sessions --------------------------------------------------------------


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def start_session(
    payload: StartSessionRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CommunicationService = Depends(get_communication_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = service.start_session(
            db, user_id=user_id, scenario_id=payload.scenario_id, difficulty=payload.difficulty
        )
    except ScenarioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SCENARIO_NOT_FOUND)

    logger.info("Communication session started user_id=%s scenario_id=%s", user_id, payload.scenario_id)
    return success_response(message="Practice session started", data=result)


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    payload: SendMessageRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CommunicationService = Depends(get_communication_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.send_message(
            db, user_id=user_id, session_id=session_id, message=payload.message
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    except SessionCompletedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_SESSION_COMPLETED)
    except Exception:
        logger.error(
            "Communication message failed user_id=%s session_id=%s", user_id, session_id, exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AI_UNAVAILABLE)

    return success_response(message="Reply generated", data=result)


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    comm_service: CommunicationService = Depends(get_communication_service),
    eval_service: EvaluationService = Depends(get_evaluation_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        session = comm_service.get_owned_session_for_completion(session_id=session_id, user_id=user_id, db=db)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)

    if session["status"] == "completed" and session.get("evaluation"):
        # Idempotent — return the already-computed evaluation.
        return success_response(
            message="Session already completed",
            data={"session_id": session_id, "evaluation": session["evaluation"]},
        )

    try:
        evaluation = await eval_service.evaluate_session(db, session=session)
    except EvaluationError:
        logger.error("Communication evaluation failed user_id=%s session_id=%s", user_id, session_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AI_UNAVAILABLE)
    except Exception:
        logger.error(
            "Unexpected error completing session user_id=%s session_id=%s",
            user_id, session_id, exc_info=True,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_UNEXPECTED)

    logger.info("Communication session completed user_id=%s session_id=%s", user_id, session_id)
    return success_response(
        message="Session completed", data={"session_id": session_id, "evaluation": evaluation}
    )


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CommunicationService = Depends(get_communication_service),
) -> dict:
    try:
        result = service.get_session(db, user_id=str(current_user["_id"]), session_id=session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SESSION_NOT_FOUND)
    except SessionForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SESSION_FORBIDDEN)
    return success_response(message="Session retrieved", data=result)


@router.get("/sessions")
def list_sessions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=MAX_HISTORY_LIMIT),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: CommunicationService = Depends(get_communication_service),
) -> dict:
    result = service.list_sessions(db, user_id=str(current_user["_id"]), page=page, limit=limit)
    return success_response(message="Session history retrieved", data=result)
