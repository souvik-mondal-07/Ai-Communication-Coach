"""
Python Interview Practice routes (Phase 26).

    GET  /api/v1/python-practice/runner                              code-runner status, isolation layers and limits (honest: says when execution is unavailable)
    GET  /api/v1/python-practice/syllabus                            units, topics and real question counts
    GET  /api/v1/python-practice/coverage                            coverage report: per-topic counts, formats, verification, gaps
    GET  /api/v1/python-practice/questions                           answer-free question listing (filters, pagination)
    POST /api/v1/python-practice/sessions                            start a practice / mock session
    GET  /api/v1/python-practice/sessions                            the caller's session history
    GET  /api/v1/python-practice/sessions/{id}                       resume a session (auto-submits when time is up)
    PUT  /api/v1/python-practice/sessions/{id}/answers/{qid}         save an option / draft answer, or mark for review
    POST /api/v1/python-practice/sessions/{id}/questions/{qid}/run     trial-run code on the VISIBLE example tests (rate limited)
    POST /api/v1/python-practice/sessions/{id}/questions/{qid}/check   grade a short or code answer now (practice sessions only; rate limited)
    POST /api/v1/python-practice/sessions/{id}/questions/{qid}/reveal  give up on a coding exercise and show the reference solution
    POST /api/v1/python-practice/sessions/{id}/questions/{qid}/hint    reveal the next hint
    POST /api/v1/python-practice/sessions/{id}/submit                finalise (idempotent)
    GET  /api/v1/python-practice/sessions/{id}/result                score, explanations, reference solutions, mistakes, topic breakdown
    GET  /api/v1/python-practice/progress                            the caller's analytics
    GET  /api/v1/python-practice/recommendations                     weak-topic recommendations

Submitted code is only ever executed by the isolated runner (app/services/python_practice/sandbox), never in this process.
Every route requires authentication; the user is always taken from the token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from pymongo.database import Database

from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import rate_limited
from app.schemas.python_practice import AnswerRequest, CheckRequest, Difficulty, Interaction, QFormat, RunRequest, SessionCreateRequest
from app.services.python_practice import analytics, bank, sessions
from app.services.python_practice.sandbox import runner
from app.utils.helpers import success_response

router = APIRouter(prefix="/python-practice", tags=["python-practice"])

_ID = r"^[a-z0-9][a-z0-9-]{0,59}$"
_SESSION_ID = r"^[a-f0-9]{24}$"
_QUESTION_ID = r"^pyq-[a-f0-9]{10}$"
MAX_LIMIT = 50


@router.get("/runner")
def get_runner(_user=Depends(get_current_user)) -> dict:
    return success_response("Code runner status retrieved.", runner.capabilities())


@router.get("/syllabus")
def get_syllabus(db: Database = Depends(get_db), _user=Depends(get_current_user)) -> dict:
    return success_response("Python syllabus retrieved.", bank.syllabus_payload(db))


@router.get("/coverage")
def get_coverage(db: Database = Depends(get_db), _user=Depends(get_current_user)) -> dict:
    return success_response("Syllabus coverage retrieved.", bank.coverage_report(db))


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
    return success_response("Questions retrieved.", bank.list_public_questions(db, unit_id=unit_id, topic_id=topic_id, difficulty=difficulty, fmt=format, interaction=interaction, page=page, limit=limit))


@router.post("/sessions", status_code=201, dependencies=[Depends(rate_limited("py-create", 15, 60))])
def create_session(body: SessionCreateRequest, db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Practice session started.", sessions.create_session(db, str(user["_id"]), body))


@router.get("/sessions")
def list_sessions(page: int = Query(default=1, ge=1, le=1000), limit: int = Query(default=10, ge=1, le=MAX_LIMIT), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Session history retrieved.", sessions.list_history(db, str(user["_id"]), page, limit))


@router.get("/sessions/{session_id}")
def get_session(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Session retrieved.", sessions.get_session(db, str(user["_id"]), session_id))


@router.put("/sessions/{session_id}/answers/{question_id}", dependencies=[Depends(rate_limited("py-answer", 300, 60))])
def save_answer(body: AnswerRequest, session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Answer saved.", sessions.save_answer(db, str(user["_id"]), session_id, question_id, body))


@router.post("/sessions/{session_id}/questions/{question_id}/run", dependencies=[Depends(rate_limited("py-run", 20, 60))])
def run_code(body: RunRequest, session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Code ran on the example tests.", sessions.run_code(db, str(user["_id"]), session_id, question_id, body))


@router.post("/sessions/{session_id}/questions/{question_id}/check", dependencies=[Depends(rate_limited("py-check", 15, 60))])
def check_answer(body: CheckRequest, session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Answer checked.", sessions.check_answer(db, str(user["_id"]), session_id, question_id, body))


@router.post("/sessions/{session_id}/questions/{question_id}/reveal", dependencies=[Depends(rate_limited("py-reveal", 30, 60))])
def reveal_solution(session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Reference solution revealed.", sessions.reveal_solution(db, str(user["_id"]), session_id, question_id))


@router.post("/sessions/{session_id}/questions/{question_id}/hint", dependencies=[Depends(rate_limited("py-hint", 60, 60))])
def next_hint(session_id: str = Path(pattern=_SESSION_ID), question_id: str = Path(pattern=_QUESTION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Hint retrieved.", sessions.next_hint(db, str(user["_id"]), session_id, question_id))


@router.post("/sessions/{session_id}/submit", dependencies=[Depends(rate_limited("py-submit", 30, 60))])
def submit_session(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Session submitted.", sessions.finalize(db, str(user["_id"]), session_id))


@router.get("/sessions/{session_id}/result")
def get_result(session_id: str = Path(pattern=_SESSION_ID), db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Result retrieved.", sessions.get_result(db, str(user["_id"]), session_id))


@router.get("/progress")
def get_progress(db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Progress retrieved.", analytics.progress_summary(db, str(user["_id"])))


@router.get("/recommendations")
def get_recommendations(db: Database = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return success_response("Recommendations retrieved.", analytics.recommendations(db, str(user["_id"])))
