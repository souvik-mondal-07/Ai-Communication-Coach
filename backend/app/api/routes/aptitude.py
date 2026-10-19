"""
General Aptitude & Logical Reasoning practice routes (Phase 23).

    GET  /api/v1/aptitude/syllabus                         topic hierarchy + real question counts
    GET  /api/v1/aptitude/questions                        answer-free question listing (filters, pagination)
    POST /api/v1/aptitude/sessions                         start a practice / mock session
    GET  /api/v1/aptitude/sessions                         the caller's session history
    GET  /api/v1/aptitude/sessions/{id}                    resume a session (auto-submits when time is up)
    PUT  /api/v1/aptitude/sessions/{id}/answers/{qid}      save / change one answer, or mark for review
    POST /api/v1/aptitude/sessions/{id}/submit             finalise (idempotent)
    GET  /api/v1/aptitude/sessions/{id}/result             score, explanations, topic breakdown
    GET  /api/v1/aptitude/progress                         the caller's analytics
    GET  /api/v1/aptitude/recommendations                  weak-topic recommendations

Every route requires authentication. The user is always taken from the token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import rate_limited
from app.schemas.aptitude import AnswerRequest, Difficulty, QuestionType, SessionCreateRequest
from app.services.aptitude import analytics, bank, sessions
from app.utils.helpers import success_response

router = APIRouter(prefix="/aptitude", tags=["aptitude"])

_ID = r"^[a-z0-9][a-z0-9-]{0,59}$"
_SESSION_ID = r"^[a-f0-9]{24}$"
_QUESTION_ID = r"^apt-[a-f0-9]{10}$"
MAX_LIMIT = 50


@router.get("/syllabus")
def get_syllabus(db: Database = Depends(get_db), _user=Depends(get_current_user)) -> dict:
    return success_response("Aptitude syllabus retrieved.", bank.syllabus_payload(db))


@router.get("/questions")
def list_questions(
    topic_id: str | None = Query(default=None, pattern=_ID),
    subtopic_id: str | None = Query(default=None, pattern=_ID),
    difficulty: Difficulty | None = None,
    question_type: QuestionType | None = None,
    page: int = Query(default=1, ge=1, le=1000),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    db: Database = Depends(get_db),
    _user=Depends(get_current_user),
) -> dict:
    data = bank.list_public_questions(db, topic_id=topic_id, subtopic_id=subtopic_id, difficulty=difficulty, question_type=question_type, page=page, limit=limit)
    return success_response("Questions retrieved.", data)


@router.post("/sessions", status_code=201, dependencies=[Depends(rate_limited("apt-create", 15, 60))])
def create_session(body: SessionCreateRequest, db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice session started.", sessions.create_session(db, str(user["_id"]), body))


@router.get("/sessions")
def list_sessions(page: int = Query(default=1, ge=1, le=1000), limit: int = Query(default=10, ge=1, le=MAX_LIMIT), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice history retrieved.", sessions.list_history(db, str(user["_id"]), page, limit))


@router.get("/sessions/{session_id}")
def get_session(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice session retrieved.", sessions.get_session(db, str(user["_id"]), session_id))


@router.put("/sessions/{session_id}/answers/{question_id}", dependencies=[Depends(rate_limited("apt-answer", 300, 60))])
def save_answer(body: AnswerRequest, session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID),
                db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Answer saved.", sessions.save_answer(db, str(user["_id"]), session_id, question_id, body))


@router.post("/sessions/{session_id}/submit", dependencies=[Depends(rate_limited("apt-submit", 30, 60))])
def submit_session(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice session submitted.", sessions.finalize(db, str(user["_id"]), session_id))


@router.get("/sessions/{session_id}/result")
def get_result(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Result retrieved.", sessions.get_result(db, str(user["_id"]), session_id))


@router.get("/progress")
def get_progress(db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Aptitude progress retrieved.", analytics.progress_summary(db, str(user["_id"])))


@router.get("/recommendations")
def get_recommendations(db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Recommendations retrieved.", analytics.recommendations(db, str(user["_id"])))
