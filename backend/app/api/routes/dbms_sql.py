"""
DBMS & SQL Interview Lab routes (Phase 25).

    GET  /api/v1/dbms-sql/syllabus                              units, topics, real question counts, SQL engine capabilities
    GET  /api/v1/dbms-sql/coverage                              coverage report: per-topic counts, formats, verification, gaps
    GET  /api/v1/dbms-sql/datasets/{id}                         table schemas + sample rows of a practice dataset (reference data, no answers)
    GET  /api/v1/dbms-sql/questions                             answer-free question listing (filters, pagination)
    POST /api/v1/dbms-sql/sandbox/run                           run ONE read-only SELECT on a fresh copy of the practice data (rate limited)
    POST /api/v1/dbms-sql/sessions                              start a practice / mock session
    GET  /api/v1/dbms-sql/sessions                              the caller's session history
    GET  /api/v1/dbms-sql/sessions/{id}                         resume a session (auto-submits when time is up)
    PUT  /api/v1/dbms-sql/sessions/{id}/answers/{qid}           save an option / draft answer, or mark for review
    POST /api/v1/dbms-sql/sessions/{id}/questions/{qid}/check   grade a short or SQL answer now (practice sessions only; rate limited)
    POST /api/v1/dbms-sql/sessions/{id}/questions/{qid}/reveal  give up on a SQL exercise and show the reference solution
    POST /api/v1/dbms-sql/sessions/{id}/questions/{qid}/hint    reveal the next hint
    POST /api/v1/dbms-sql/sessions/{id}/submit                  finalise (idempotent)
    GET  /api/v1/dbms-sql/sessions/{id}/result                  score, explanations, reference solutions, mistakes, topic breakdown
    GET  /api/v1/dbms-sql/progress                              the caller's analytics
    GET  /api/v1/dbms-sql/recommendations                       weak-topic recommendations

User SQL is only ever executed by the isolated sandbox (see app/services/dbms_sql/sandbox.py), never against MongoDB.
Every route requires authentication; the user is always taken from the token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import rate_limited
from app.schemas.dbms_sql import AnswerRequest, CheckRequest, Difficulty, Interaction, QFormat, SandboxRunRequest, SessionCreateRequest
from app.services.dbms_sql import analytics, bank, datasets, sandbox, sessions
from app.services.dbms_sql.errors import not_found
from app.utils.helpers import success_response

router = APIRouter(prefix="/dbms-sql", tags=["dbms-sql"])

_ID = r"^[a-z0-9][a-z0-9-]{0,59}$"
_SESSION_ID = r"^[a-f0-9]{24}$"
_QUESTION_ID = r"^dbq-[a-f0-9]{10}$"
MAX_LIMIT = 50


@router.get("/syllabus")
def get_syllabus(db: Database = Depends(get_db), _user=Depends(get_current_user)) -> dict:
    return success_response("DBMS & SQL syllabus retrieved.", bank.syllabus_payload(db))


@router.get("/coverage")
def get_coverage(db: Database = Depends(get_db), _user=Depends(get_current_user)) -> dict:
    return success_response("Syllabus coverage retrieved.", bank.coverage_report(db))


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str = Path(pattern=_ID), _user=Depends(get_current_user)) -> dict:
    try:
        data = datasets.describe(dataset_id)
    except KeyError:
        raise not_found("Dataset not found.") from None
    return success_response("Dataset retrieved.", data)


@router.get("/questions")
def list_questions(
    unit_id: str | None = Query(default=None, pattern=_ID),
    topic_id: str | None = Query(default=None, pattern=_ID),
    difficulty: Difficulty | None = None,
    format: QFormat | None = None,  # noqa: A002 - public query parameter name
    interaction: Interaction | None = None,
    page: int = Query(default=1, ge=1, le=1000),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    db: Database = Depends(get_db),
    _user=Depends(get_current_user),
) -> dict:
    data = bank.list_public_questions(db, unit_id=unit_id, topic_id=topic_id, difficulty=difficulty, fmt=format, interaction=interaction, page=page, limit=limit)
    return success_response("Questions retrieved.", data)


@router.post("/sandbox/run", dependencies=[Depends(rate_limited("dbms-sandbox", 30, 60))])
def run_sandbox(body: SandboxRunRequest, _user=Depends(get_current_user)) -> dict:
    """A failed or rejected query is a normal, successful response with ok=false and a safe message, not an HTTP error."""
    return success_response("Query executed.", sandbox.run_query(body.sql, body.dataset_id).to_dict())


@router.post("/sessions", status_code=201, dependencies=[Depends(rate_limited("dbms-create", 15, 60))])
def create_session(body: SessionCreateRequest, db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice session started.", sessions.create_session(db, str(user["_id"]), body))


@router.get("/sessions")
def list_sessions(page: int = Query(default=1, ge=1, le=1000), limit: int = Query(default=10, ge=1, le=MAX_LIMIT), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice history retrieved.", sessions.list_history(db, str(user["_id"]), page, limit))


@router.get("/sessions/{session_id}")
def get_session(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice session retrieved.", sessions.get_session(db, str(user["_id"]), session_id))


@router.put("/sessions/{session_id}/answers/{question_id}", dependencies=[Depends(rate_limited("dbms-answer", 300, 60))])
def save_answer(body: AnswerRequest, session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID),
                db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Answer saved.", sessions.save_answer(db, str(user["_id"]), session_id, question_id, body))


@router.post("/sessions/{session_id}/questions/{question_id}/check", dependencies=[Depends(rate_limited("dbms-check", 20, 60))])
def check_answer(body: CheckRequest, session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID),
                 db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Answer checked.", sessions.check_answer(db, str(user["_id"]), session_id, question_id, body))


@router.post("/sessions/{session_id}/questions/{question_id}/reveal", dependencies=[Depends(rate_limited("dbms-reveal", 30, 60))])
def reveal_solution(session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Solution revealed.", sessions.reveal_solution(db, str(user["_id"]), session_id, question_id))


@router.post("/sessions/{session_id}/questions/{question_id}/hint", dependencies=[Depends(rate_limited("dbms-hint", 60, 60))])
def next_hint(session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Hint revealed.", sessions.next_hint(db, str(user["_id"]), session_id, question_id))


@router.post("/sessions/{session_id}/submit", dependencies=[Depends(rate_limited("dbms-submit", 30, 60))])
def submit_session(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice session submitted.", sessions.finalize(db, str(user["_id"]), session_id))


@router.get("/sessions/{session_id}/result")
def get_result(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Result retrieved.", sessions.get_result(db, str(user["_id"]), session_id))


@router.get("/progress")
def get_progress(db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("DBMS & SQL progress retrieved.", analytics.progress_summary(db, str(user["_id"])))


@router.get("/recommendations")
def get_recommendations(db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Recommendations retrieved.", analytics.recommendations(db, str(user["_id"])))
