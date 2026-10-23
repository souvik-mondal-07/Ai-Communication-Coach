"""
DSA Interview Practice routes (Phase 24).

    GET  /api/v1/dsa/syllabus                              topic hierarchy + real question counts + execution capability
    GET  /api/v1/dsa/questions                             answer-free question listing (filters, pagination)
    POST /api/v1/dsa/sessions                              start a practice / mock session
    GET  /api/v1/dsa/sessions                              the caller's session history
    GET  /api/v1/dsa/sessions/{id}                         resume a session (auto-submits when time is up)
    PUT  /api/v1/dsa/sessions/{id}/answers/{qid}           save / change one answer (option or code), or mark for review
    POST /api/v1/dsa/sessions/{id}/submit                  finalise (idempotent)
    GET  /api/v1/dsa/sessions/{id}/result                  score, explanations, traces, reference solutions, topic breakdown
    PUT  /api/v1/dsa/sessions/{id}/self-assessment/{qid}   record your own verdict on a coding answer (never scored)
    GET  /api/v1/dsa/progress                              the caller's analytics
    GET  /api/v1/dsa/recommendations                       weak-topic recommendations

There is deliberately NO "run my code" endpoint: submitted code is never executed by this application.
Every route requires authentication; the user is always taken from the token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import rate_limited
from app.schemas.dsa import AnswerRequest, Difficulty, QFormat, SelfAssessmentRequest, SessionCreateRequest
from app.services.dsa import analytics, bank, sessions
from app.utils.helpers import success_response

router = APIRouter(prefix="/dsa", tags=["dsa"])

_ID = r"^[a-z0-9][a-z0-9-]{0,59}$"
_SESSION_ID = r"^[a-f0-9]{24}$"
_QUESTION_ID = r"^dsa-[a-f0-9]{10}$"
MAX_LIMIT = 50


@router.get("/syllabus")
def get_syllabus(db: Database = Depends(get_db), _user=Depends(get_current_user)) -> dict:
    return success_response("DSA syllabus retrieved.", bank.syllabus_payload(db))


@router.get("/questions")
def list_questions(
    topic_id: str | None = Query(default=None, pattern=_ID),
    subtopic_id: str | None = Query(default=None, pattern=_ID),
    difficulty: Difficulty | None = None,
    format: QFormat | None = None,  # noqa: A002 - public query parameter name
    page: int = Query(default=1, ge=1, le=1000),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    db: Database = Depends(get_db),
    _user=Depends(get_current_user),
) -> dict:
    data = bank.list_public_questions(db, topic_id=topic_id, subtopic_id=subtopic_id, difficulty=difficulty, fmt=format, page=page, limit=limit)
    return success_response("Questions retrieved.", data)


@router.post("/sessions", status_code=201, dependencies=[Depends(rate_limited("dsa-create", 15, 60))])
def create_session(body: SessionCreateRequest, db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice session started.", sessions.create_session(db, str(user["_id"]), body))


@router.get("/sessions")
def list_sessions(page: int = Query(default=1, ge=1, le=1000), limit: int = Query(default=10, ge=1, le=MAX_LIMIT), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice history retrieved.", sessions.list_history(db, str(user["_id"]), page, limit))


@router.get("/sessions/{session_id}")
def get_session(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice session retrieved.", sessions.get_session(db, str(user["_id"]), session_id))


@router.put("/sessions/{session_id}/answers/{question_id}", dependencies=[Depends(rate_limited("dsa-answer", 300, 60))])
def save_answer(body: AnswerRequest, session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID),
                db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Answer saved.", sessions.save_answer(db, str(user["_id"]), session_id, question_id, body))


@router.post("/sessions/{session_id}/submit", dependencies=[Depends(rate_limited("dsa-submit", 30, 60))])
def submit_session(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice session submitted.", sessions.finalize(db, str(user["_id"]), session_id))


@router.get("/sessions/{session_id}/result")
def get_result(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Result retrieved.", sessions.get_result(db, str(user["_id"]), session_id))


@router.put("/sessions/{session_id}/self-assessment/{question_id}", dependencies=[Depends(rate_limited("dsa-assess", 60, 60))])
def self_assess(body: SelfAssessmentRequest, session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID),
                db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Self-assessment saved.", sessions.set_self_assessment(db, str(user["_id"]), session_id, question_id, body.verdict))


@router.get("/progress")
def get_progress(db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("DSA progress retrieved.", analytics.progress_summary(db, str(user["_id"])))


@router.get("/recommendations")
def get_recommendations(db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Recommendations retrieved.", analytics.recommendations(db, str(user["_id"])))
