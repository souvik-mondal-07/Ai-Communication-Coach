"""
Python practice sessions: creation, answer saving, running and checking code, hints, finalisation, results (Phase 26).

Trust model
  * The user id always comes from the authenticated token.
  * The browser sends only a displayed option position, short text or SOURCE CODE. Correctness is decided here: MCQs by the stored key,
    short answers by deterministic parsing, code by running it in the isolated runner and comparing its raw outputs with expected values
    that never leave this process. A client-supplied score, test result, correctness flag or completion status is never read.
  * Answer keys, explanations, reference solutions and expected values are returned only (a) as `feedback` after an answer is locked in an
    immediate-feedback session, (b) after an explicit reveal (coding questions: only after at least one submission or every hint),
    or (c) in the result once the session is completed. Timed mocks reveal nothing, allow no submission checks and no hints before submit;
    they do allow trial runs on the visible example tests (as a real interview would).
  * Hidden tests report pass/fail only. Their inputs, expected values, output and error text are never returned.
  * Finalisation claims the session with one atomic conditional update (in_progress -> completed); the result is stored once and attempts
    are written once (unique index), so retries, double clicks and auto-submit races cannot double-count.
  * A coding answer whose reference solution was revealed before it was solved scores 0. Code is only ever executed by the isolated runner.
"""

from __future__ import annotations

import logging
import math
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database
from pymongo.errors import BulkWriteError

from app.db.collections import Collections
from app.schemas.python_practice import AnswerRequest, CheckRequest, RunRequest, SessionCreateRequest
from app.services.python_practice import analytics, compare, grader
from app.services.python_practice.bank import MODE_FILTERS, to_public
from app.services.python_practice.errors import conflict, invalid, not_found
from app.services.python_practice.sandbox import runner
from app.services.python_practice.syllabus import TOPIC_BY_ID, UNIT_BY_ID, topic_title

logger = logging.getLogger(__name__)

_rng = secrets.SystemRandom()  # tests replace this with a seeded random.Random

EXPIRY_GRACE_SECONDS = 3
MAX_OPEN_SESSIONS = 25
MAX_CANDIDATES = 5000
REVISION_ACCURACY_BELOW = 70.0
MAX_TIMER_MINUTES = 180
CODE_MODES = ("coding", "debug", "complete")
SCORING_POLICY = (
    "Each correct answer scores 1 mark; incorrect and unanswered score 0 (no negative marking). Accuracy = correct ÷ questions in the session. "
    "Code is graded by running it against the problem's tests (visible and hidden) in an isolated runner: a coding question is correct only when "
    "every test passes. If you reveal a reference solution before solving it, that question scores 0. Time taken is measured by the server from "
    "session start to submission (capped at the time limit for timed tests)."
)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise not_found() from exc


def _runner_ok() -> bool:
    return bool(runner.capabilities()["available"])


# --- Question selection ---------------------------------------------------------------------------------------------------------


def _interleave_topics(rows: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = {}
    for row in rows:
        buckets.setdefault(row["topic_id"], []).append(row)
    for b in buckets.values():
        _rng.shuffle(b)
    order = list(buckets)
    _rng.shuffle(order)
    out: list[dict] = []
    while any(buckets.values()):
        for t in order:
            if buckets[t]:
                out.append(buckets[t].pop())
    return out


def _prefer_unseen(rows: list[dict], seen: set[str]) -> list[dict]:
    return [r for r in rows if r["question_id"] not in seen] + [r for r in rows if r["question_id"] in seen]


def _resolve_filters(req: SessionCreateRequest) -> tuple[list[str], list[str]]:
    for u in req.unit_ids:
        if u not in UNIT_BY_ID:
            raise invalid(f"Unknown unit '{u}'.", "UNKNOWN_UNIT")
    for t in req.topic_ids:
        if t not in TOPIC_BY_ID:
            raise invalid(f"Unknown topic '{t}'.", "UNKNOWN_TOPIC")
    return req.unit_ids, req.topic_ids


_PICK = {"_id": 0, "question_id": 1, "unit_id": 1, "topic_id": 1, "difficulty": 1, "interaction": 1, "format": 1, "est_time_seconds": 1}


def _select_questions(db: Database, user_id: str, req: SessionCreateRequest, unit_ids: list[str], topic_ids: list[str]) -> list[dict]:
    qcoll = db[Collections.PYTHON_QUESTIONS]
    attempts = analytics.load_attempts(db, user_id)
    seen = {a["question_id"] for a in attempts}
    clauses: list[dict[str, Any]] = [{"status": "active"}]
    if topic_ids:
        clauses.append({"topic_id": {"$in": topic_ids}})
    elif unit_ids:
        clauses.append({"unit_id": {"$in": unit_ids}})
    if req.difficulty:
        clauses.append({"difficulty": req.difficulty})
    if req.mode == "topic" and not topic_ids:
        raise invalid("Choose at least one topic for topic practice.", "TOPIC_REQUIRED")
    if req.mode in MODE_FILTERS:
        clauses.append(MODE_FILTERS[req.mode])
    caps = runner.capabilities()
    if not caps["available"]:
        if req.mode in CODE_MODES:
            raise conflict(f"Coding exercises need the code runner, which is unavailable: {caps['reason']}", "RUNNER_UNAVAILABLE")
        clauses.append({"interaction": {"$ne": "code"}})  # never hand out a question that cannot be graded

    if req.mode == "weak":
        if not attempts:
            raise conflict("There is no practice history yet, so no weak topics can be identified. Complete a few sessions first.", "NO_HISTORY")
        weak = analytics.weak_areas(attempts)
        wrong_ids = analytics.latest_incorrect_question_ids(attempts)
        if not weak and not wrong_ids:
            raise conflict("No weak topics or incorrect answers were found. Keep practising and check back.", "NO_WEAK_AREAS")
        ors = []
        if wrong_ids:
            ors.append({"question_id": {"$in": wrong_ids}})
        if weak:
            ors.append({"topic_id": {"$in": [w["topic_id"] for w in weak]}})
        clauses.append({"$or": ors})
        rows = list(qcoll.find({"$and": clauses}, _PICK).limit(MAX_CANDIDATES))
        wrong_set = set(wrong_ids)
        first = [r for r in rows if r["question_id"] in wrong_set]
        rest = [r for r in rows if r["question_id"] not in wrong_set]
        _rng.shuffle(first)
        return (first + _interleave_topics(_prefer_unseen(rest, seen)))[: req.question_count]

    rows = list(qcoll.find({"$and": clauses}, _PICK).limit(MAX_CANDIDATES))
    if not rows:
        raise conflict("No questions match these filters yet. Try another topic, difficulty or mode.", "NO_QUESTIONS")
    if req.mode != "topic" or len(topic_ids) > 1:
        unseen = [r for r in rows if r["question_id"] not in seen]
        pool = _interleave_topics(unseen) + _interleave_topics([r for r in rows if r["question_id"] in seen])
        return pool[: req.question_count]
    unseen = [r for r in rows if r["question_id"] not in seen]
    again = [r for r in rows if r["question_id"] in seen]
    _rng.shuffle(unseen)
    _rng.shuffle(again)
    return (unseen + again)[: req.question_count]


# --- Public shapes -----------------------------------------------------------------------------------------------------------------


def _remaining(session: dict, now: datetime) -> int | None:
    exp = _aware(session.get("expires_at"))
    return None if exp is None else max(0, math.ceil((exp - now).total_seconds()))


def _feedback(doc: dict, order: list[int], ans: dict) -> dict:
    """Answer-bearing feedback. Only ever built for a locked answer in an immediate-feedback session, or after a reveal."""
    if doc["interaction"] == "code":
        spec = doc["spec"]
        return {"kind": "code", "is_correct": bool(ans.get("solved")), "revealed": bool(ans.get("revealed")), "reference_source": spec["reference_source"],
                "time_complexity": spec["time_complexity"], "space_complexity": spec["space_complexity"], "explanation": doc["explanation"]}
    if doc["interaction"] == "short":
        return {"kind": "short", "is_correct": bool(ans.get("solved")), "answer": compare.canonical_short(doc["short"]), "explanation": doc["explanation"]}
    sel = ans.get("selected_orig")
    return {"kind": "mcq", "is_correct": sel == doc["correct_index"], "correct_index": order.index(doc["correct_index"]), "explanation": doc["explanation"]}


def _session_questions_payload(db: Database, session: dict) -> list[dict]:
    ids = [q["question_id"] for q in session["questions"]]
    docs = {d["question_id"]: d for d in db[Collections.PYTHON_QUESTIONS].find({"question_id": {"$in": ids}})}
    out = []
    for sq in session["questions"]:
        doc = docs.get(sq["question_id"])
        if doc is None:
            continue
        order = sq["option_order"]
        ans = session.get("answers", {}).get(sq["question_id"], {})
        sel = ans.get("selected_orig")
        item = to_public(doc, options_order=order if doc["interaction"] == "mcq" else None)
        hints = list(doc.get("hints") or [])
        used = int(ans.get("hints_used", 0))
        item.update({
            "selected_index": order.index(sel) if (sel is not None and order) else None, "text_answer": ans.get("text"), "code_answer": ans.get("code"),
            "marked_for_review": bool(ans.get("marked")), "locked": bool(ans.get("locked")), "checks": int(ans.get("checks", 0)), "runs": int(ans.get("runs", 0)),
            "hints_total": 0 if session["exam_mode"] else len(hints), "hints_used": 0 if session["exam_mode"] else used,
            "hints": [] if session["exam_mode"] else hints[:used], "last_check": ans.get("last_check"), "last_run": ans.get("last_run"), "feedback": None,
            "can_reveal": (not session["exam_mode"]) and doc["interaction"] == "code" and (int(ans.get("checks", 0)) >= 1 or (bool(hints) and used >= len(hints))),
        })
        if ans.get("locked") and session.get("immediate_feedback"):
            item["feedback"] = _feedback(doc, order, ans)
        out.append(item)
    return out


def _session_out(db: Database, session: dict) -> dict:
    now = _now()
    return {
        "session_id": str(session["_id"]), "mode": session["mode"], "status": session["status"], "difficulty": session.get("difficulty"),
        "question_count": len(session["questions"]), "requested_count": session["requested_count"], "unit_ids": session.get("unit_ids", []), "topic_ids": session.get("topic_ids", []),
        "immediate_feedback": session["immediate_feedback"], "exam_mode": session["exam_mode"], "started_at": _aware(session["started_at"]),
        "expires_at": _aware(session.get("expires_at")), "server_time": now,
        "remaining_seconds": _remaining(session, now) if session["status"] == "in_progress" else (0 if session.get("expires_at") else None),
        "timer_minutes": session.get("timer_minutes"), "questions": _session_questions_payload(db, session), "scoring_policy": SCORING_POLICY,
    }


# --- Lifecycle -----------------------------------------------------------------------------------------------------------------------


def create_session(db: Database, user_id: str, req: SessionCreateRequest) -> dict:
    sessions = db[Collections.PYTHON_SESSIONS]
    uid = ObjectId(user_id)
    _sweep_expired(db, uid)
    if sessions.count_documents({"user_id": uid, "status": "in_progress"}) >= MAX_OPEN_SESSIONS:
        raise conflict("You have too many unfinished practice sessions. Finish or submit some before starting another.", "TOO_MANY_OPEN_SESSIONS")
    unit_ids, topic_ids = _resolve_filters(req)
    exam_mode = req.mode == "timed_mock"
    if exam_mode and req.immediate_feedback:
        raise invalid("Timed mock interviews do not show answers during the test.", "FEEDBACK_NOT_ALLOWED")
    picked = _select_questions(db, user_id, req, unit_ids, topic_ids)
    if not picked:
        raise conflict("No questions are available for this selection yet.", "NO_QUESTIONS")
    timer = req.timer_minutes
    if exam_mode and timer is None:
        timer = min(MAX_TIMER_MINUTES, max(1, math.ceil(sum(int(r.get("est_time_seconds", 60)) for r in picked) / 60)))
    immediate = False if exam_mode else (req.immediate_feedback if req.immediate_feedback is not None else True)

    questions = []
    for row in picked:
        order = [0, 1, 2, 3] if row["interaction"] == "mcq" else []
        _rng.shuffle(order)
        questions.append({"question_id": row["question_id"], "unit_id": row["unit_id"], "topic_id": row["topic_id"], "difficulty": row["difficulty"],
                          "interaction": row["interaction"], "format": row["format"], "option_order": order})
    now = _now()
    doc = {
        "user_id": uid, "mode": req.mode, "difficulty": req.difficulty, "unit_ids": unit_ids or sorted({q["unit_id"] for q in questions}),
        "topic_ids": topic_ids or sorted({q["topic_id"] for q in questions}), "requested_count": req.question_count, "timer_minutes": timer,
        "immediate_feedback": immediate, "exam_mode": exam_mode, "status": "in_progress", "started_at": now,
        "expires_at": now + timedelta(minutes=timer) if timer else None, "finished_at": None, "auto_submitted": False,
        "questions": questions, "answers": {}, "schema_version": 1,
    }
    doc["_id"] = sessions.insert_one(doc).inserted_id
    return _session_out(db, doc)


def _load_owned(db: Database, user_id: str, session_id: str) -> dict:
    doc = db[Collections.PYTHON_SESSIONS].find_one({"_id": _oid(session_id), "user_id": ObjectId(user_id)})
    if doc is None:
        raise not_found()  # identical for "missing" and "someone else's": no existence leak
    return doc


def _is_expired(session: dict, now: datetime, grace: int = 0) -> bool:
    exp = _aware(session.get("expires_at"))
    return exp is not None and now > exp + timedelta(seconds=grace)


def _sweep_expired(db: Database, uid: ObjectId) -> None:
    now = _now()
    for s in db[Collections.PYTHON_SESSIONS].find({"user_id": uid, "status": "in_progress", "expires_at": {"$lt": now}}).limit(MAX_OPEN_SESSIONS):
        try:
            finalize(db, str(uid), str(s["_id"]), auto=True)
        except Exception:  # noqa: BLE001
            logger.warning("Could not auto-finalise expired Python session %s", s["_id"], exc_info=True)


def get_session(db: Database, user_id: str, session_id: str) -> dict:
    session = _load_owned(db, user_id, session_id)
    if session["status"] == "in_progress" and _is_expired(session, _now()):
        finalize(db, user_id, session_id, auto=True)
        session = _load_owned(db, user_id, session_id)
    return _session_out(db, session)


def _open_question(db: Database, user_id: str, session_id: str, question_id: str) -> tuple[dict, dict, dict, datetime]:
    session = _load_owned(db, user_id, session_id)
    now = _now()
    if session["status"] != "in_progress":
        raise conflict("This session has already been submitted.", "SESSION_COMPLETED")
    if _is_expired(session, now, EXPIRY_GRACE_SECONDS):
        finalize(db, user_id, session_id, auto=True)
        raise conflict("Time is up. The test was submitted automatically.", "SESSION_EXPIRED")
    sq = next((q for q in session["questions"] if q["question_id"] == question_id), None)
    if sq is None:
        raise invalid("That question is not part of this session.", "QUESTION_NOT_IN_SESSION")
    doc = db[Collections.PYTHON_QUESTIONS].find_one({"question_id": question_id})
    if doc is None:
        raise not_found("Question not found.")
    return session, sq, doc, now


def _elapsed(session: dict, now: datetime, reported: int) -> int:
    return min(max(0, reported), max(0, int((now - _aware(session["started_at"])).total_seconds())), 3600)


def _guarded_update(db: Database, session: dict, question_id: str, update: dict) -> None:
    res = db[Collections.PYTHON_SESSIONS].update_one(
        {"_id": session["_id"], "user_id": session["user_id"], "status": "in_progress", f"answers.{question_id}.locked": {"$ne": True}}, update)
    if res.matched_count == 0:
        raise conflict("This session was just submitted or the answer is already locked.", "SESSION_COMPLETED")


def save_answer(db: Database, user_id: str, session_id: str, question_id: str, req: AnswerRequest) -> dict:
    """Save a selection or a draft. MCQ selections lock immediately in immediate-feedback sessions; short and code drafts never lock."""
    session, sq, doc, now = _open_question(db, user_id, session_id, question_id)
    ans = session.get("answers", {}).get(question_id, {})
    if ans.get("locked"):
        raise conflict("This answer is locked because its feedback was already shown.", "ANSWER_LOCKED")
    kind = sq["interaction"]
    sent = {"mcq": req.selected_index is not None, "short": req.text is not None, "code": req.code is not None}
    if any(v for k, v in sent.items() if k != kind):
        raise invalid(f"This is a {kind} question: send the matching answer type only.", "WRONG_ANSWER_TYPE")
    prefix = f"answers.{question_id}"
    sets: dict[str, Any] = {f"{prefix}.marked": bool(req.marked_for_review), f"{prefix}.time_spent": _elapsed(session, now, req.time_spent_seconds), f"{prefix}.answered_at": now}
    locks = False
    selected_orig = None
    if kind == "mcq":
        selected_orig = sq["option_order"][req.selected_index] if req.selected_index is not None else None
        sets[f"{prefix}.selected_orig"] = selected_orig
        locks = bool(session["immediate_feedback"] and selected_orig is not None)
    elif kind == "short":
        sets[f"{prefix}.text"] = (req.text or "").strip() or None
    else:
        sets[f"{prefix}.code"] = req.code if (req.code or "").strip() else None
    sets[f"{prefix}.locked"] = locks
    _guarded_update(db, session, question_id, {"$set": sets})
    result: dict[str, Any] = {"question_id": question_id, "selected_index": req.selected_index, "marked_for_review": bool(req.marked_for_review), "locked": locks,
                              "feedback": None, "remaining_seconds": _remaining(session, now)}
    if locks:
        result["feedback"] = _feedback(doc, sq["option_order"], {"selected_orig": selected_orig})
    return result


def _code_question(sq: dict, doc: dict) -> dict:
    if sq["interaction"] != "code":
        raise invalid("Only coding exercises can be run.", "WRONG_ANSWER_TYPE")
    return doc["spec"]


def run_code(db: Database, user_id: str, session_id: str, question_id: str, req: RunRequest) -> dict:
    """Trial run on the VISIBLE example tests only. Allowed in every session type; never scores anything and never locks."""
    session, sq, doc, now = _open_question(db, user_id, session_id, question_id)
    spec = _code_question(sq, doc)
    ans = session.get("answers", {}).get(question_id, {})
    if ans.get("locked"):
        raise conflict("This answer is locked.", "ANSWER_LOCKED")
    result = grader.grade(spec, req.code, visible_only=True)
    if result.verdict == "runner_error" and not _runner_ok():
        raise conflict(result.message, "RUNNER_UNAVAILABLE")
    prefix = f"answers.{question_id}"
    last = {"verdict": result.verdict, "passed": result.passed, "total": result.total}
    _guarded_update(db, session, question_id, {"$set": {f"{prefix}.code": req.code, f"{prefix}.last_run": last, f"{prefix}.answered_at": now}, "$inc": {f"{prefix}.runs": 1}})
    return {"question_id": question_id, "kind": "run", "result": result.to_dict(), "remaining_seconds": _remaining(session, now)}


def check_answer(db: Database, user_id: str, session_id: str, question_id: str, req: CheckRequest) -> dict:
    """Grade a short or code answer now (practice sessions only). Correct answers lock; wrong code can be retried."""
    session, sq, doc, now = _open_question(db, user_id, session_id, question_id)
    if session["exam_mode"] or not session["immediate_feedback"]:
        raise conflict("Checking answers is not available in this session. Submit the session to see results.", "CHECK_NOT_ALLOWED")
    kind = sq["interaction"]
    if kind == "mcq":
        raise invalid("Multiple-choice answers are checked when you select an option.", "WRONG_ANSWER_TYPE")
    ans = session.get("answers", {}).get(question_id, {})
    if ans.get("locked"):
        raise conflict("This answer is already locked.", "ANSWER_LOCKED")
    prefix = f"answers.{question_id}"
    spent = _elapsed(session, now, req.time_spent_seconds)
    checks = int(ans.get("checks", 0)) + 1

    if kind == "short":
        given = (req.text or "").strip()
        if not given:
            raise invalid("Type an answer first.", "EMPTY_ANSWER")
        ok = compare.grade_short(doc["short"], given)
        _guarded_update(db, session, question_id, {"$set": {f"{prefix}.text": given, f"{prefix}.locked": True, f"{prefix}.solved": ok, f"{prefix}.time_spent": spent,
                                                           f"{prefix}.answered_at": now}, "$inc": {f"{prefix}.checks": 1}})
        return {"question_id": question_id, "kind": "short", "correct": ok, "locked": True, "checks": checks, "feedback": _feedback(doc, [], {"solved": ok}),
                "remaining_seconds": _remaining(session, now)}

    code = req.code or ""
    if not code.strip():
        raise invalid("Write your solution first.", "EMPTY_ANSWER")
    result = grader.grade(doc["spec"], code, visible_only=False)
    if result.verdict == "runner_error":
        raise conflict(result.message, "RUNNER_UNAVAILABLE")  # not the learner's fault: nothing is counted
    ok = result.accepted
    best = max(int(ans.get("best_passed", 0)), result.passed)
    last = {"verdict": result.verdict, "passed": result.passed, "total": result.total}
    update: dict[str, Any] = {"$set": {f"{prefix}.code": code, f"{prefix}.time_spent": spent, f"{prefix}.answered_at": now, f"{prefix}.last_check": last, f"{prefix}.best_passed": best,
                                       f"{prefix}.tests_total": result.total, f"{prefix}.locked": ok, f"{prefix}.solved": ok}, "$inc": {f"{prefix}.checks": 1}}
    _guarded_update(db, session, question_id, update)
    out: dict[str, Any] = {"question_id": question_id, "kind": "code", "correct": ok, "result": result.to_dict(), "locked": ok, "checks": checks, "feedback": None,
                           "can_reveal": checks >= 1, "remaining_seconds": _remaining(session, now)}
    if ok:
        out["feedback"] = _feedback(doc, [], {"solved": True})
    return out


def reveal_solution(db: Database, user_id: str, session_id: str, question_id: str) -> dict:
    """Give up on a coding exercise: lock it and show the reference solution. Scores 0 unless it was already solved."""
    session, sq, doc, now = _open_question(db, user_id, session_id, question_id)
    if session["exam_mode"] or not session["immediate_feedback"]:
        raise conflict("Solutions are not available in this session before you submit it.", "REVEAL_NOT_ALLOWED")
    if sq["interaction"] != "code":
        raise invalid("Only coding exercises have a reference solution to reveal.", "WRONG_ANSWER_TYPE")
    ans = session.get("answers", {}).get(question_id, {})
    hints = list(doc.get("hints") or [])
    if int(ans.get("checks", 0)) < 1 and not (hints and int(ans.get("hints_used", 0)) >= len(hints)):
        raise conflict("Try submitting a solution (or use every hint) before revealing the reference solution.", "REVEAL_TOO_EARLY")
    prefix = f"answers.{question_id}"
    _guarded_update(db, session, question_id, {"$set": {f"{prefix}.locked": True, f"{prefix}.revealed": True, f"{prefix}.answered_at": now}})
    return {"question_id": question_id, "locked": True, "feedback": _feedback(doc, [], {"revealed": True, "solved": False}), "remaining_seconds": _remaining(session, now)}


def next_hint(db: Database, user_id: str, session_id: str, question_id: str) -> dict:
    session, sq, doc, now = _open_question(db, user_id, session_id, question_id)
    if session["exam_mode"]:
        raise conflict("Hints are not available in timed mock interviews.", "HINT_NOT_ALLOWED")
    hints = list(doc.get("hints") or [])
    if not hints:
        raise conflict("This question has no hints.", "NO_HINTS")
    ans = session.get("answers", {}).get(question_id, {})
    if ans.get("locked"):
        raise conflict("This answer is locked, so hints are no longer needed.", "ANSWER_LOCKED")
    used = int(ans.get("hints_used", 0))
    if used >= len(hints):
        raise conflict("You have already seen every hint for this question.", "NO_MORE_HINTS")
    prefix = f"answers.{question_id}"
    res = db[Collections.PYTHON_SESSIONS].update_one(
        {"_id": session["_id"], "user_id": session["user_id"], "status": "in_progress", f"answers.{question_id}.locked": {"$ne": True},
         "$or": [{f"answers.{question_id}.hints_used": used}, {f"answers.{question_id}.hints_used": {"$exists": False}}] if used == 0 else [{f"answers.{question_id}.hints_used": used}]},
        {"$set": {f"{prefix}.hints_used": used + 1}})
    if res.matched_count == 0:
        raise conflict("That hint was already revealed. Refresh and try again.", "HINT_CONFLICT")
    return {"question_id": question_id, "hint": hints[used], "hint_number": used + 1, "hints_total": len(hints), "hints": hints[: used + 1]}


# --- Results -----------------------------------------------------------------------------------------------------------------------


def _compute_result(db: Database, session: dict) -> dict:
    ids = [q["question_id"] for q in session["questions"]]
    docs = {d["question_id"]: d for d in db[Collections.PYTHON_QUESTIONS].find({"question_id": {"$in": ids}})}
    items, per_topic = [], {}
    counts = {"correct": 0, "incorrect": 0, "unanswered": 0}
    for sq in session["questions"]:
        doc = docs.get(sq["question_id"])
        ans = session.get("answers", {}).get(sq["question_id"], {})
        sel, text, code = ans.get("selected_orig"), ans.get("text"), ans.get("code")
        extra: dict[str, Any] = {}
        outcome = "unanswered"
        passed, total = int(ans.get("best_passed", 0)), int(ans.get("tests_total", 0))
        if doc is not None:
            if sq["interaction"] == "mcq" and sel is not None:
                outcome = "correct" if sel == doc["correct_index"] else "incorrect"
            elif sq["interaction"] == "short" and text:
                outcome = "correct" if compare.grade_short(doc["short"], text) else "incorrect"
            elif sq["interaction"] == "code":
                if ans.get("revealed") and not ans.get("solved"):
                    outcome = "incorrect"
                    extra["note"] = "Reference solution revealed before it was solved."
                elif ans.get("solved"):
                    outcome = "correct"
                elif code and code.strip():
                    graded = grader.grade(doc["spec"], code, visible_only=False)
                    if graded.verdict == "runner_error":
                        extra["note"] = "This answer could not be graded because the code runner was unavailable."
                    else:
                        outcome = "correct" if graded.accepted else "incorrect"
                        passed, total = graded.passed, graded.total
                        extra["verdict"] = {"verdict": graded.verdict, "passed": graded.passed, "total": graded.total, "message": graded.message}
        counts[outcome] += 1
        items.append({"question_id": sq["question_id"], "unit_id": sq["unit_id"], "topic_id": sq["topic_id"], "difficulty": sq["difficulty"], "format": sq["format"],
                      "interaction": sq["interaction"], "outcome": outcome, "selected_orig": sel, "text": text, "code": code, "revealed": bool(ans.get("revealed")),
                      "checks": int(ans.get("checks", 0)), "runs": int(ans.get("runs", 0)), "hints_used": int(ans.get("hints_used", 0)), "marked": bool(ans.get("marked")),
                      "time_spent": int(ans.get("time_spent", 0)), "tests_passed": passed if sq["interaction"] == "code" else 0, "tests_total": total if sq["interaction"] == "code" else 0, **extra})
        t = per_topic.setdefault(sq["topic_id"], {"total": 0, "correct": 0, "incorrect": 0, "unanswered": 0})
        t["total"] += 1
        t[outcome] += 1
    total_q = len(session["questions"])
    started, finished = _aware(session["started_at"]), _aware(session["finished_at"])
    taken = max(0, int((finished - started).total_seconds()))
    if session.get("timer_minutes"):
        taken = min(taken, session["timer_minutes"] * 60)
    topic_perf = [{"topic_id": tid, "topic_title": topic_title(tid), "unit_id": next(q["unit_id"] for q in session["questions"] if q["topic_id"] == tid), **t,
                   "accuracy": round(100.0 * t["correct"] / t["total"], 1)} for tid, t in sorted(per_topic.items(), key=lambda kv: topic_title(kv[0]))]
    revision = [{"topic_id": tp["topic_id"], "topic_title": tp["topic_title"], "accuracy": tp["accuracy"]} for tp in sorted(topic_perf, key=lambda x: x["accuracy"]) if tp["accuracy"] < REVISION_ACCURACY_BELOW]
    return {
        "total_questions": total_q, "graded_questions": total_q, "correct": counts["correct"], "incorrect": counts["incorrect"], "unanswered": counts["unanswered"], "score": counts["correct"],
        "accuracy": round(100.0 * counts["correct"] / total_q, 1) if total_q else 0.0, "time_taken_seconds": taken, "average_seconds_per_question": round(taken / total_q, 1) if total_q else 0.0,
        "topic_performance": topic_perf, "revision_topics": revision, "items": items,
    }


def _write_attempts(db: Database, session: dict, result: dict) -> None:
    rows = [{
        "user_id": session["user_id"], "session_id": session["_id"], "question_id": i["question_id"], "unit_id": i["unit_id"], "topic_id": i["topic_id"], "difficulty": i["difficulty"],
        "format": i["format"], "interaction": i["interaction"], "outcome": i["outcome"], "time_spent_seconds": i["time_spent"], "mode": session["mode"], "hints_used": i["hints_used"],
        "code_checks": i["checks"] if i["interaction"] == "code" else 0, "code_runs": i["runs"] if i["interaction"] == "code" else 0, "tests_passed": i["tests_passed"],
        "tests_total": i["tests_total"], "revealed": i["revealed"], "created_at": _aware(session["finished_at"]),
    } for i in result["items"]]
    try:
        db[Collections.PYTHON_ATTEMPTS].insert_many(rows, ordered=False)
    except BulkWriteError as exc:
        if [e for e in exc.details.get("writeErrors", []) if e.get("code") != 11000]:
            raise


def _materialise(db: Database, session: dict) -> dict:
    result = session.get("result")
    if result is None:
        result = _compute_result(db, session)
        db[Collections.PYTHON_SESSIONS].update_one({"_id": session["_id"], "result": {"$exists": False}}, {"$set": {"result": result}})
        session = db[Collections.PYTHON_SESSIONS].find_one({"_id": session["_id"]}) or session
        result = session.get("result", result)
    _write_attempts(db, session, result)
    return result


def finalize(db: Database, user_id: str, session_id: str, auto: bool = False) -> dict:
    """Idempotent: the first caller completes the session; later callers get the same stored result."""
    sessions = db[Collections.PYTHON_SESSIONS]
    session = _load_owned(db, user_id, session_id)
    now = _now()
    if session["status"] == "in_progress":
        exp = _aware(session.get("expires_at"))
        expired = exp is not None and now >= exp
        finished = min(now, exp) if exp else now
        claimed = sessions.find_one_and_update(
            {"_id": session["_id"], "user_id": session["user_id"], "status": "in_progress"},
            {"$set": {"status": "completed", "finished_at": finished, "completed_at": finished, "updated_at": now, "auto_submitted": bool(auto or expired)}},
            return_document=True,
        )
        session = claimed if claimed is not None else _load_owned(db, user_id, session_id)
    _materialise(db, session)
    return get_result(db, user_id, session_id)


def get_result(db: Database, user_id: str, session_id: str) -> dict:
    session = _load_owned(db, user_id, session_id)
    if session["status"] != "completed":
        raise conflict("Results are available after the session is submitted.", "SESSION_NOT_FINISHED")
    result = session.get("result") or _materialise(db, session)
    ids = [i["question_id"] for i in result["items"]]
    docs = {d["question_id"]: d for d in db[Collections.PYTHON_QUESTIONS].find({"question_id": {"$in": ids}})}
    orders = {q["question_id"]: q["option_order"] for q in session["questions"]}
    questions = []
    for item in result["items"]:
        doc = docs.get(item["question_id"])
        if doc is None:
            continue
        order = orders[item["question_id"]]
        sel = item["selected_orig"]
        q: dict[str, Any] = {
            "question_id": doc["question_id"], "unit_id": doc["unit_id"], "topic_id": doc["topic_id"], "format": doc["format"], "interaction": doc["interaction"],
            "difficulty": doc["difficulty"], "title": doc.get("title"), "statement": doc["statement"], "code": doc.get("code"), "python_version": doc.get("python_version"),
            "options": [doc["options"][i] for i in order] if order else [], "selected_index": order.index(sel) if (sel is not None and order) else None,
            "correct_index": order.index(doc["correct_index"]) if order else None, "outcome": item["outcome"], "explanation": doc["explanation"],
            "marked_for_review": item["marked"], "time_spent_seconds": item["time_spent"], "hints_used": item["hints_used"], "text_answer": item.get("text"), "code_answer": item.get("code"),
            "code_checks": item["checks"], "tests_passed": item["tests_passed"], "tests_total": item["tests_total"], "revealed": item["revealed"], "note": item.get("note"),
            "verdict": item.get("verdict"), "correct_answer": None, "reference_source": None, "time_complexity": None, "space_complexity": None,
        }
        if doc["interaction"] == "short":
            q["correct_answer"] = compare.canonical_short(doc["short"])
        if doc["interaction"] == "code":
            q["reference_source"] = doc["spec"]["reference_source"]
            q["time_complexity"] = doc["spec"]["time_complexity"]
            q["space_complexity"] = doc["spec"]["space_complexity"]
        questions.append(q)
    return {
        "session_id": str(session["_id"]), "mode": session["mode"], "status": "completed", "total_questions": result["total_questions"], "correct": result["correct"],
        "incorrect": result["incorrect"], "unanswered": result["unanswered"], "score": result["score"], "accuracy": result["accuracy"], "time_taken_seconds": result["time_taken_seconds"],
        "average_seconds_per_question": result["average_seconds_per_question"], "auto_submitted": bool(session.get("auto_submitted")), "started_at": _aware(session["started_at"]),
        "finished_at": _aware(session["finished_at"]), "topic_performance": result["topic_performance"], "revision_topics": result["revision_topics"], "questions": questions,
        "scoring_policy": SCORING_POLICY,
    }


def list_history(db: Database, user_id: str, page: int, limit: int) -> dict:
    coll = db[Collections.PYTHON_SESSIONS]
    query = {"user_id": ObjectId(user_id)}
    total = coll.count_documents(query)
    rows = list(coll.find(query, {"mode": 1, "status": 1, "started_at": 1, "finished_at": 1, "result": 1, "questions": 1, "topic_ids": 1, "unit_ids": 1, "timer_minutes": 1})
                .sort("started_at", -1).skip((page - 1) * limit).limit(limit))
    items = []
    for s in rows:
        r = s.get("result")
        items.append({
            "session_id": str(s["_id"]), "mode": s["mode"], "status": s["status"], "started_at": _aware(s["started_at"]), "finished_at": _aware(s.get("finished_at")),
            "question_count": len(s["questions"]), "unit_ids": s.get("unit_ids", []), "topic_ids": s.get("topic_ids", []), "score": r["score"] if r else None,
            "accuracy": r["accuracy"] if r else None, "time_taken_seconds": r["time_taken_seconds"] if r else None, "timer_minutes": s.get("timer_minutes"),
        })
    return {"items": items, "page": page, "limit": limit, "total": total, "has_next": page * limit < total}
