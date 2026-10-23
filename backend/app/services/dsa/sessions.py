"""
DSA practice sessions: creation, answer saving, finalisation, results, self-assessment.

Trust model (same as Phase 23, extended for code answers)
  * The user id always comes from the authenticated token.
  * The browser sends only a displayed option position (MCQ) or code text; the server maps/stores it.
    Correct answers, explanations, traces, complexity notes, reference solutions and hidden test cases are read
    from the bank and returned only (a) as `feedback` for an immediate-feedback practice answer after that answer is
    locked, or (b) in the result after the session is completed. Timed mocks reveal nothing before submission.
  * Score, accuracy and duration are computed here. Per-question time is client-reported and only clamped.
  * Finalisation claims the session with one atomic conditional update (in_progress -> completed): double clicks,
    retries and the auto-submit race cannot score or record a session twice.
  * SUBMITTED CODE IS NEVER EXECUTED. Code questions are stored, shown with the reference solution and test cases, and may be
    self-assessed by the user; they are reported as `ungraded` and excluded from accuracy and weak-topic maths.
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
from app.schemas.dsa import AnswerRequest, SessionCreateRequest
from app.services.dsa import analytics
from app.services.dsa.bank import to_public
from app.services.dsa.errors import conflict, invalid, not_found
from app.services.dsa.syllabus import SUBTOPIC_TITLES, SUBTOPIC_TO_TOPIC, TOPIC_BY_ID, topic_title

logger = logging.getLogger(__name__)

_rng = secrets.SystemRandom()  # tests replace this with a seeded random.Random

EXPIRY_GRACE_SECONDS = 3
MAX_OPEN_SESSIONS = 25
MAX_CANDIDATES = 5000
REVISION_ACCURACY_BELOW = 70.0
EXECUTION_NOTE = ("Your code was NOT run: this application does not execute submitted code. Compare it with the reference solution and the test "
                  "cases below (walk through each one by hand), then mark your own result.")
SCORING_POLICY = (
    "Each correct multiple-choice answer scores 1 mark; incorrect and unanswered score 0 (no negative marking). "
    "Accuracy = correct ÷ multiple-choice questions in the session. Coding exercises are NOT run automatically, so they are "
    "'ungraded': they do not affect your score or accuracy, and any pass/fail you record on them is self-reported. "
    "Time taken is measured by the server from session start to submission (capped at the time limit for timed tests)."
)
MODE_FORMATS: dict[str, list[str]] = {
    "interview": ["conceptual", "scenario", "complexity"],
    "tracing": ["trace", "output"],
    "complexity": ["complexity"],
    "coding": ["coding"],
}
DEFAULT_IMMEDIATE = ("topic", "interview", "tracing", "complexity", "coding", "weak")


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


# --- Question selection ---------------------------------------------------------------------------------


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
    for t in req.topic_ids:
        if t not in TOPIC_BY_ID:
            raise invalid(f"Unknown topic '{t}'.", "UNKNOWN_TOPIC")
    for s in req.subtopic_ids:
        if s not in SUBTOPIC_TO_TOPIC:
            raise invalid(f"Unknown subtopic '{s}'.", "UNKNOWN_SUBTOPIC")
        if req.topic_ids and SUBTOPIC_TO_TOPIC[s] not in req.topic_ids:
            raise invalid("A selected subtopic does not belong to the selected topics.", "SUBTOPIC_TOPIC_MISMATCH")
    return req.topic_ids, req.subtopic_ids


_PICK = {"_id": 0, "question_id": 1, "topic_id": 1, "subtopic_id": 1, "difficulty": 1, "interaction": 1}


def _select_questions(db: Database, user_id: str, req: SessionCreateRequest, topic_ids: list[str], subtopic_ids: list[str]) -> list[dict]:
    qcoll = db[Collections.DSA_QUESTIONS]
    attempts = analytics.load_attempts(db, user_id)
    seen = {a["question_id"] for a in attempts}
    query: dict[str, Any] = {"status": "active"}
    if subtopic_ids:
        query["subtopic_id"] = {"$in": subtopic_ids}
    elif topic_ids:
        query["topic_id"] = {"$in": topic_ids}
    if req.difficulty:
        query["difficulty"] = req.difficulty
    if req.mode == "topic" and not (topic_ids or subtopic_ids):
        raise invalid("Choose a topic or subtopic for topic practice.", "TOPIC_REQUIRED")
    if req.mode in MODE_FORMATS:
        query["format"] = {"$in": MODE_FORMATS[req.mode]}
    if req.mode != "coding":
        query["interaction"] = "mcq"  # scored modes only ever contain auto-gradable questions

    if req.mode == "weak":
        if not attempts:
            raise conflict("There is no practice history yet, so no weak topics can be identified. Complete a few sessions first.", "NO_HISTORY")
        weak = analytics.weak_areas(attempts)
        wrong_ids = analytics.latest_incorrect_question_ids(attempts)
        if not weak and not wrong_ids:
            raise conflict("No weak topics or incorrect answers were found. Keep practising and check back.", "NO_WEAK_AREAS")
        clauses = []
        if wrong_ids:
            clauses.append({"question_id": {"$in": wrong_ids}})
        if weak:
            clauses.append({"topic_id": {"$in": [w["topic_id"] for w in weak]}})
        query["$or"] = clauses
        rows = list(qcoll.find(query, _PICK).limit(MAX_CANDIDATES))
        wrong_set = set(wrong_ids)
        first = [r for r in rows if r["question_id"] in wrong_set]
        rest = [r for r in rows if r["question_id"] not in wrong_set]
        _rng.shuffle(first)
        return (first + _interleave_topics(_prefer_unseen(rest, seen)))[: req.question_count]

    rows = list(qcoll.find(query, _PICK).limit(MAX_CANDIDATES))
    if not rows:
        raise conflict("No questions match these filters yet. Try another topic, difficulty or mode.", "NO_QUESTIONS")
    if req.mode in ("timed_mock", "interview", "tracing", "complexity") and not subtopic_ids:
        unseen = [r for r in rows if r["question_id"] not in seen]
        pool = _interleave_topics(unseen) + _interleave_topics([r for r in rows if r["question_id"] in seen])
        return pool[: req.question_count]
    unseen = [r for r in rows if r["question_id"] not in seen]
    again = [r for r in rows if r["question_id"] in seen]
    _rng.shuffle(unseen)
    _rng.shuffle(again)
    return (unseen + again)[: req.question_count]


# --- Public shapes --------------------------------------------------------------------------------------


def _remaining(session: dict, now: datetime) -> int | None:
    exp = _aware(session.get("expires_at"))
    return None if exp is None else max(0, math.ceil((exp - now).total_seconds()))


def _all_tests(doc: dict) -> list[dict]:
    return [{"label": t["label"], "args": t["args"], "expected": t["expected"], "visible": t["visible"], "edge": t["edge"]} for t in doc["coding"]["test_cases"]]


def _feedback(doc: dict, order: list[int], selected_orig: int | None) -> dict:
    if doc["interaction"] == "code":
        return {"kind": "code", "explanation": doc["explanation"], "reference_solution": doc["coding"]["reference_solution"], "test_cases": _all_tests(doc),
                "complexity": doc.get("complexity"), "execution_note": EXECUTION_NOTE}
    return {"kind": "mcq", "is_correct": selected_orig == doc["correct_index"], "correct_index": order.index(doc["correct_index"]), "explanation": doc["explanation"],
            "complexity": doc.get("complexity"), "trace": doc.get("trace")}


def _session_questions_payload(db: Database, session: dict) -> list[dict]:
    ids = [q["question_id"] for q in session["questions"]]
    docs = {d["question_id"]: d for d in db[Collections.DSA_QUESTIONS].find({"question_id": {"$in": ids}})}
    out = []
    for sq in session["questions"]:
        doc = docs.get(sq["question_id"])
        if doc is None:
            continue
        order = sq["option_order"]
        ans = session.get("answers", {}).get(sq["question_id"], {})
        sel = ans.get("selected_orig")
        item = to_public(doc, options_order=order if doc["interaction"] == "mcq" else None)
        item.update({
            "selected_index": order.index(sel) if (sel is not None and order) else None, "code_answer": ans.get("code"),
            "marked_for_review": bool(ans.get("marked")), "locked": bool(ans.get("locked")),
            "hints": [] if session["exam_mode"] else list(doc.get("hints") or []), "feedback": None,
        })
        if ans.get("locked") and session.get("immediate_feedback"):
            item["feedback"] = _feedback(doc, order, sel)
        out.append(item)
    return out


def _session_out(db: Database, session: dict) -> dict:
    now = _now()
    return {
        "session_id": str(session["_id"]), "mode": session["mode"], "status": session["status"], "difficulty": session.get("difficulty"),
        "question_count": len(session["questions"]), "requested_count": session["requested_count"], "topic_ids": session.get("topic_ids", []),
        "immediate_feedback": session["immediate_feedback"], "exam_mode": session["exam_mode"], "started_at": _aware(session["started_at"]),
        "expires_at": _aware(session.get("expires_at")), "server_time": now,
        "remaining_seconds": _remaining(session, now) if session["status"] == "in_progress" else (0 if session.get("expires_at") else None),
        "timer_minutes": session.get("timer_minutes"), "questions": _session_questions_payload(db, session), "scoring_policy": SCORING_POLICY,
    }


# --- Lifecycle ------------------------------------------------------------------------------------------


def create_session(db: Database, user_id: str, req: SessionCreateRequest) -> dict:
    sessions = db[Collections.DSA_SESSIONS]
    uid = ObjectId(user_id)
    _sweep_expired(db, uid)
    if sessions.count_documents({"user_id": uid, "status": "in_progress"}) >= MAX_OPEN_SESSIONS:
        raise conflict("You have too many unfinished practice sessions. Finish or submit some before starting another.", "TOO_MANY_OPEN_SESSIONS")
    topic_ids, subtopic_ids = _resolve_filters(req)
    exam_mode = req.mode == "timed_mock"
    if exam_mode and req.immediate_feedback:
        raise invalid("Timed mock tests do not show answers during the test.", "FEEDBACK_NOT_ALLOWED")
    timer = req.timer_minutes
    if exam_mode and timer is None:
        timer = max(1, math.ceil(req.question_count * 1.5))
    immediate = False if exam_mode else (req.immediate_feedback if req.immediate_feedback is not None else req.mode in DEFAULT_IMMEDIATE)

    picked = _select_questions(db, user_id, req, topic_ids, subtopic_ids)
    if not picked:
        raise conflict("No questions are available for this selection yet.", "NO_QUESTIONS")
    questions = []
    for row in picked:
        order = [0, 1, 2, 3] if row["interaction"] == "mcq" else []
        _rng.shuffle(order)
        questions.append({"question_id": row["question_id"], "topic_id": row["topic_id"], "subtopic_id": row["subtopic_id"], "difficulty": row["difficulty"],
                          "interaction": row["interaction"], "option_order": order})
    now = _now()
    doc = {
        "user_id": uid, "mode": req.mode, "difficulty": req.difficulty, "topic_ids": topic_ids or sorted({q["topic_id"] for q in questions}), "subtopic_ids": subtopic_ids,
        "requested_count": req.question_count, "timer_minutes": timer, "immediate_feedback": immediate, "exam_mode": exam_mode, "status": "in_progress",
        "started_at": now, "expires_at": now + timedelta(minutes=timer) if timer else None, "finished_at": None, "auto_submitted": False,
        "questions": questions, "answers": {}, "schema_version": 1,
    }
    doc["_id"] = sessions.insert_one(doc).inserted_id
    return _session_out(db, doc)


def _load_owned(db: Database, user_id: str, session_id: str) -> dict:
    doc = db[Collections.DSA_SESSIONS].find_one({"_id": _oid(session_id), "user_id": ObjectId(user_id)})
    if doc is None:
        raise not_found()  # identical for "missing" and "someone else's": no existence leak
    return doc


def _is_expired(session: dict, now: datetime, grace: int = 0) -> bool:
    exp = _aware(session.get("expires_at"))
    return exp is not None and now > exp + timedelta(seconds=grace)


def _sweep_expired(db: Database, uid: ObjectId) -> None:
    now = _now()
    for s in db[Collections.DSA_SESSIONS].find({"user_id": uid, "status": "in_progress", "expires_at": {"$lt": now}}).limit(MAX_OPEN_SESSIONS):
        try:
            finalize(db, str(uid), str(s["_id"]), auto=True)
        except Exception:  # noqa: BLE001
            logger.warning("Could not auto-finalise expired DSA session %s", s["_id"], exc_info=True)


def get_session(db: Database, user_id: str, session_id: str) -> dict:
    session = _load_owned(db, user_id, session_id)
    if session["status"] == "in_progress" and _is_expired(session, _now()):
        finalize(db, user_id, session_id, auto=True)
        session = _load_owned(db, user_id, session_id)
    return _session_out(db, session)


def save_answer(db: Database, user_id: str, session_id: str, question_id: str, req: AnswerRequest) -> dict:
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
    existing = session.get("answers", {}).get(question_id, {})
    if existing.get("locked"):
        raise conflict("This answer is locked because its feedback was already shown.", "ANSWER_LOCKED")

    is_code = sq["interaction"] == "code"
    code_text = (req.code or "").strip("\n") if is_code else None
    if is_code and req.selected_index is not None:
        raise invalid("This is a coding question: send code, not an option.", "WRONG_ANSWER_TYPE")
    if not is_code and req.code is not None:
        raise invalid("This is a multiple-choice question: send an option, not code.", "WRONG_ANSWER_TYPE")
    if is_code and not (code_text or "").strip():
        code_text = None
    selected_orig = sq["option_order"][req.selected_index] if (not is_code and req.selected_index is not None) else None

    elapsed = max(0, int((now - _aware(session["started_at"])).total_seconds()))
    wants_reveal = bool(session["immediate_feedback"] and ((not is_code and selected_orig is not None) or (is_code and req.reveal and code_text)))
    entry = {"selected_orig": selected_orig, "code": code_text, "marked": bool(req.marked_for_review), "locked": wants_reveal,
             "time_spent": min(req.time_spent_seconds, elapsed, 3600), "answered_at": now}
    res = db[Collections.DSA_SESSIONS].update_one(
        {"_id": session["_id"], "user_id": session["user_id"], "status": "in_progress", f"answers.{question_id}.locked": {"$ne": True}},
        {"$set": {f"answers.{question_id}": entry}},
    )
    if res.matched_count == 0:
        raise conflict("This session was just submitted or the answer is already locked.", "SESSION_COMPLETED")
    result: dict[str, Any] = {"question_id": question_id, "selected_index": req.selected_index, "code_answer": code_text, "marked_for_review": entry["marked"],
                              "locked": wants_reveal, "feedback": None, "remaining_seconds": _remaining(session, now)}
    if wants_reveal:
        doc = db[Collections.DSA_QUESTIONS].find_one({"question_id": question_id})
        if doc:
            result["feedback"] = _feedback(doc, sq["option_order"], selected_orig)
    return result


def _compute_result(db: Database, session: dict) -> dict:
    ids = [q["question_id"] for q in session["questions"]]
    docs = {d["question_id"]: d for d in db[Collections.DSA_QUESTIONS].find({"question_id": {"$in": ids}}, {"question_id": 1, "correct_index": 1, "interaction": 1})}
    items, per_topic = [], {}
    correct = incorrect = unanswered = ungraded = 0
    for sq in session["questions"]:
        doc = docs.get(sq["question_id"])
        ans = session.get("answers", {}).get(sq["question_id"], {})
        sel = ans.get("selected_orig")
        if sq["interaction"] == "code":
            outcome = "ungraded"
        elif sel is None or doc is None:
            outcome = "unanswered"
        else:
            outcome = "correct" if sel == doc["correct_index"] else "incorrect"
        correct += outcome == "correct"
        incorrect += outcome == "incorrect"
        unanswered += outcome == "unanswered"
        ungraded += outcome == "ungraded"
        items.append({"question_id": sq["question_id"], "topic_id": sq["topic_id"], "subtopic_id": sq["subtopic_id"], "difficulty": sq["difficulty"], "interaction": sq["interaction"],
                      "outcome": outcome, "selected_orig": sel, "code": ans.get("code"), "marked": bool(ans.get("marked")), "time_spent": int(ans.get("time_spent", 0))})
        if outcome != "ungraded":
            t = per_topic.setdefault(sq["topic_id"], {"total": 0, "correct": 0, "incorrect": 0, "unanswered": 0, "weak_subtopics": set()})
            t["total"] += 1
            t[outcome] += 1
            if outcome != "correct":
                t["weak_subtopics"].add(sq["subtopic_id"])
    total = len(session["questions"])
    graded = total - ungraded
    started, finished = _aware(session["started_at"]), _aware(session["finished_at"])
    taken = max(0, int((finished - started).total_seconds()))
    if session.get("timer_minutes"):
        taken = min(taken, session["timer_minutes"] * 60)
    topic_perf = [{"topic_id": tid, "topic_title": topic_title(tid), "total": t["total"], "correct": t["correct"], "incorrect": t["incorrect"], "unanswered": t["unanswered"],
                   "accuracy": round(100.0 * t["correct"] / t["total"], 1)} for tid, t in sorted(per_topic.items(), key=lambda kv: topic_title(kv[0]))]
    revision = [{"topic_id": tp["topic_id"], "topic_title": tp["topic_title"], "accuracy": tp["accuracy"],
                 "subtopics": [{"subtopic_id": s, "title": SUBTOPIC_TITLES.get(s, s)} for s in sorted(per_topic[tp["topic_id"]]["weak_subtopics"])]}
                for tp in sorted(topic_perf, key=lambda x: x["accuracy"]) if tp["accuracy"] < REVISION_ACCURACY_BELOW]
    return {
        "total_questions": total, "graded_questions": graded, "ungraded_questions": ungraded, "correct": correct, "incorrect": incorrect, "unanswered": unanswered, "score": correct,
        "accuracy": round(100.0 * correct / graded, 1) if graded else 0.0, "time_taken_seconds": taken,
        "average_seconds_per_question": round(taken / total, 1) if total else 0.0, "topic_performance": topic_perf, "revision_topics": revision, "items": items,
    }


def _write_attempts(db: Database, session: dict, result: dict) -> None:
    rows = [{
        "user_id": session["user_id"], "session_id": session["_id"], "question_id": i["question_id"], "topic_id": i["topic_id"], "subtopic_id": i["subtopic_id"],
        "difficulty": i["difficulty"], "outcome": i["outcome"], "time_spent_seconds": i["time_spent"], "mode": session["mode"], "created_at": _aware(session["finished_at"]),
    } for i in result["items"]]
    try:
        db[Collections.DSA_ATTEMPTS].insert_many(rows, ordered=False)
    except BulkWriteError as exc:
        if [e for e in exc.details.get("writeErrors", []) if e.get("code") != 11000]:
            raise


def _materialise(db: Database, session: dict) -> dict:
    result = session.get("result")
    if result is None:
        result = _compute_result(db, session)
        db[Collections.DSA_SESSIONS].update_one({"_id": session["_id"], "result": {"$exists": False}}, {"$set": {"result": result}})
        session = db[Collections.DSA_SESSIONS].find_one({"_id": session["_id"]}) or session
        result = session.get("result", result)
    _write_attempts(db, session, result)
    return result


def finalize(db: Database, user_id: str, session_id: str, auto: bool = False) -> dict:
    """Idempotent: the first caller completes the session; later callers get the same stored result."""
    sessions = db[Collections.DSA_SESSIONS]
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
    docs = {d["question_id"]: d for d in db[Collections.DSA_QUESTIONS].find({"question_id": {"$in": ids}})}
    orders = {q["question_id"]: q["option_order"] for q in session["questions"]}
    assessments = session.get("self_assessments", {})
    questions, complexity_summary = [], []
    for item in result["items"]:
        doc = docs.get(item["question_id"])
        if doc is None:
            continue
        order = orders[item["question_id"]]
        sel = item["selected_orig"]
        is_code = doc["interaction"] == "code"
        questions.append({
            "question_id": doc["question_id"], "topic_id": doc["topic_id"], "subtopic_id": doc["subtopic_id"], "format": doc["format"], "interaction": doc["interaction"],
            "coding_type": doc.get("coding_type"), "difficulty": doc["difficulty"], "statement": doc["statement"], "code": doc.get("code"),
            "options": [doc["options"][i] for i in order] if order else [], "selected_index": order.index(sel) if (sel is not None and order) else None,
            "correct_index": order.index(doc["correct_index"]) if order else None, "code_answer": item.get("code"), "outcome": item["outcome"], "explanation": doc["explanation"],
            "complexity": doc.get("complexity"), "trace": doc.get("trace"), "reference_solution": doc["coding"]["reference_solution"] if is_code else None,
            "test_cases": _all_tests(doc) if is_code else None, "self_assessment": assessments.get(doc["question_id"]), "execution_note": EXECUTION_NOTE if is_code else None,
            "marked_for_review": item["marked"], "time_spent_seconds": item["time_spent"],
        })
        if doc.get("complexity"):
            complexity_summary.append({"question_id": doc["question_id"], "subtopic_id": doc["subtopic_id"], "subtopic_title": SUBTOPIC_TITLES.get(doc["subtopic_id"], doc["subtopic_id"]),
                                       "statement": doc["statement"][:140], "complexity": doc["complexity"]})
    return {
        "session_id": str(session["_id"]), "mode": session["mode"], "status": "completed", "total_questions": result["total_questions"], "graded_questions": result["graded_questions"],
        "ungraded_questions": result["ungraded_questions"], "correct": result["correct"], "incorrect": result["incorrect"], "unanswered": result["unanswered"], "score": result["score"],
        "accuracy": result["accuracy"], "time_taken_seconds": result["time_taken_seconds"], "average_seconds_per_question": result["average_seconds_per_question"],
        "auto_submitted": bool(session.get("auto_submitted")), "started_at": _aware(session["started_at"]), "finished_at": _aware(session["finished_at"]),
        "topic_performance": result["topic_performance"], "revision_topics": result["revision_topics"], "complexity_summary": complexity_summary,
        "questions": questions, "scoring_policy": SCORING_POLICY,
    }


def set_self_assessment(db: Database, user_id: str, session_id: str, question_id: str, verdict: str) -> dict:
    """Record the user's own verdict on a coding question after the session is complete. Never affects score/accuracy."""
    session = _load_owned(db, user_id, session_id)
    if session["status"] != "completed":
        raise conflict("You can assess a coding answer after the session is submitted.", "SESSION_NOT_FINISHED")
    sq = next((q for q in session["questions"] if q["question_id"] == question_id), None)
    if sq is None or sq["interaction"] != "code":
        raise invalid("Self-assessment applies only to coding questions in this session.", "NOT_A_CODING_QUESTION")
    if not (session.get("answers", {}).get(question_id, {}).get("code") or "").strip():
        raise conflict("You did not submit code for this question, so there is nothing to assess.", "NO_CODE_SUBMITTED")
    db[Collections.DSA_SESSIONS].update_one({"_id": session["_id"], "user_id": session["user_id"]}, {"$set": {f"self_assessments.{question_id}": verdict}})
    return {"question_id": question_id, "self_assessment": verdict, "counts_toward_score": False}


def list_history(db: Database, user_id: str, page: int, limit: int) -> dict:
    coll = db[Collections.DSA_SESSIONS]
    query = {"user_id": ObjectId(user_id)}
    total = coll.count_documents(query)
    rows = list(coll.find(query, {"mode": 1, "status": 1, "started_at": 1, "finished_at": 1, "result": 1, "questions": 1, "topic_ids": 1, "timer_minutes": 1})
                .sort("started_at", -1).skip((page - 1) * limit).limit(limit))
    items = []
    for s in rows:
        r = s.get("result")
        items.append({
            "session_id": str(s["_id"]), "mode": s["mode"], "status": s["status"], "started_at": _aware(s["started_at"]), "finished_at": _aware(s.get("finished_at")),
            "question_count": len(s["questions"]), "topic_ids": s.get("topic_ids", []), "score": r["score"] if r else None, "graded_questions": r["graded_questions"] if r else None,
            "accuracy": r["accuracy"] if r else None, "time_taken_seconds": r["time_taken_seconds"] if r else None, "timer_minutes": s.get("timer_minutes"),
        })
    return {"items": items, "page": page, "limit": limit, "total": total, "has_next": page * limit < total}
