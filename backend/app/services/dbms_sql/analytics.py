"""
Progress analytics for the DBMS & SQL lab, computed ONLY from recorded attempts (`dbms_sql_attempts`, one row per question
when a session is finalised). Nothing is estimated or invented: with no attempts every function returns empty results.
Unanswered questions are presented-but-not-scored and never count toward accuracy.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from bson import ObjectId
from pymongo.database import Database

from app.db.collections import Collections
from app.services.dbms_sql.syllabus import TOPIC_BY_ID, TOPIC_TO_UNIT, topic_title, unit_title

WEAK_MIN_ANSWERED = 5
WEAK_ACCURACY_BELOW = 60.0
REPEATED_MISTAKE_MIN = 2
MAX_ATTEMPTS_SCANNED = 5000
_SCORED = ("correct", "incorrect")


def _pct(correct: int, total: int) -> float:
    return round(100.0 * correct / total, 1) if total else 0.0


def load_attempts(db: Database, user_id: str) -> list[dict]:
    return list(db[Collections.DBMS_SQL_ATTEMPTS].find({"user_id": ObjectId(user_id)}).sort("created_at", -1).limit(MAX_ATTEMPTS_SCANNED))


def weak_areas(attempts: list[dict]) -> list[dict[str, Any]]:
    per_topic: dict[str, dict[str, int]] = defaultdict(lambda: {"answered": 0, "correct": 0})
    for a in attempts:
        if a["outcome"] in _SCORED:
            per_topic[a["topic_id"]]["answered"] += 1
            per_topic[a["topic_id"]]["correct"] += a["outcome"] == "correct"
    out = []
    for topic_id, c in per_topic.items():
        acc = _pct(c["correct"], c["answered"])
        if c["answered"] >= WEAK_MIN_ANSWERED and acc < WEAK_ACCURACY_BELOW and topic_id in TOPIC_BY_ID:
            out.append({"topic_id": topic_id, "topic_title": topic_title(topic_id), "unit_id": TOPIC_TO_UNIT[topic_id], "answered": c["answered"], "correct": c["correct"],
                        "accuracy": acc, "reason": f"{acc}% accuracy over {c['answered']} answered questions (below {int(WEAK_ACCURACY_BELOW)}%)."})
    out.sort(key=lambda x: (x["accuracy"], -x["answered"]))
    return out


def latest_incorrect_question_ids(attempts: list[dict]) -> list[str]:
    latest: dict[str, str] = {}
    for a in attempts:  # newest first
        latest.setdefault(a["question_id"], a["outcome"])
    return [qid for qid, outcome in latest.items() if outcome == "incorrect"]


def repeated_mistakes(attempts: list[dict]) -> list[dict[str, Any]]:
    """Questions answered incorrectly at least twice (across sessions)."""
    wrong: dict[str, dict[str, Any]] = {}
    for a in attempts:
        if a["outcome"] == "incorrect":
            e = wrong.setdefault(a["question_id"], {"question_id": a["question_id"], "topic_id": a["topic_id"], "times_incorrect": 0})
            e["times_incorrect"] += 1
    rows = [dict(e, topic_title=topic_title(e["topic_id"])) for e in wrong.values() if e["times_incorrect"] >= REPEATED_MISTAKE_MIN]
    rows.sort(key=lambda e: (-e["times_incorrect"], e["topic_title"]))
    return rows[:20]


def progress_summary(db: Database, user_id: str) -> dict[str, Any]:
    uid = ObjectId(user_id)
    attempts = load_attempts(db, user_id)
    scored = [a for a in attempts if a["outcome"] in _SCORED]
    correct = sum(1 for a in scored if a["outcome"] == "correct")
    topic: dict[str, dict[str, int]] = defaultdict(lambda: {"answered": 0, "correct": 0, "presented": 0})
    unit: dict[str, dict[str, int]] = defaultdict(lambda: {"answered": 0, "correct": 0})
    diff: dict[str, dict[str, int]] = defaultdict(lambda: {"answered": 0, "correct": 0})
    sql = {"questions_answered": 0, "queries_checked": 0, "solved": 0, "solutions_revealed": 0}
    timed = [a["time_spent_seconds"] for a in scored if a.get("time_spent_seconds")]
    for a in attempts:
        t = topic[a["topic_id"]]
        t["presented"] += 1
        if a["outcome"] in _SCORED:
            ok = a["outcome"] == "correct"
            for bucket, key in ((t, None), (unit[a.get("unit_id") or TOPIC_TO_UNIT.get(a["topic_id"], "")], None), (diff[a["difficulty"]], None)):
                bucket["answered"] += 1
                bucket["correct"] += ok
        if a.get("interaction") == "sql":
            sql["queries_checked"] += int(a.get("sql_checks", 0))
            sql["solutions_revealed"] += bool(a.get("revealed"))
            if a["outcome"] in _SCORED:
                sql["questions_answered"] += 1
                sql["solved"] += a["outcome"] == "correct"
    sessions = list(db[Collections.DBMS_SQL_SESSIONS].find({"user_id": uid, "status": "completed", "result": {"$exists": True}},
                                                           {"mode": 1, "result": 1, "started_at": 1, "finished_at": 1}).sort("finished_at", -1).limit(50))
    recent = [{"session_id": str(s["_id"]), "mode": s["mode"], "score": s["result"]["score"], "total": s["result"]["total_questions"], "accuracy": s["result"]["accuracy"],
               "time_taken_seconds": s["result"]["time_taken_seconds"], "finished_at": s["finished_at"]} for s in sessions[:10]]
    mocks = [{"session_id": str(s["_id"]), "score": s["result"]["score"], "total": s["result"]["total_questions"], "accuracy": s["result"]["accuracy"],
              "time_taken_seconds": s["result"]["time_taken_seconds"], "finished_at": s["finished_at"]} for s in sessions if s["mode"] == "timed_mock"][:10]
    chron = list(reversed([s for s in sessions if s["result"]["total_questions"] > 0][:20]))
    trend = [{"session_id": str(s["_id"]), "accuracy": s["result"]["accuracy"], "finished_at": s["finished_at"]} for s in chron]
    improvement = None
    if len(chron) >= 4:
        half = len(chron) // 2
        improvement = round(sum(s["result"]["accuracy"] for s in chron[half:]) / (len(chron) - half) - sum(s["result"]["accuracy"] for s in chron[:half]) / half, 1)
    return {
        "sessions_completed": db[Collections.DBMS_SQL_SESSIONS].count_documents({"user_id": uid, "status": "completed"}),
        "questions_presented": len(attempts), "questions_answered": len(scored), "correct": correct, "incorrect": len(scored) - correct,
        "unanswered": sum(1 for a in attempts if a["outcome"] == "unanswered"), "accuracy": _pct(correct, len(scored)),
        "average_seconds_per_answered_question": round(sum(timed) / len(timed), 1) if timed else None,
        "topic_accuracy": sorted([{"topic_id": tid, "topic_title": topic_title(tid), "unit_id": TOPIC_TO_UNIT.get(tid, ""), "answered": c["answered"], "correct": c["correct"],
                                   "presented": c["presented"], "accuracy": _pct(c["correct"], c["answered"])} for tid, c in topic.items()], key=lambda x: x["topic_title"]),
        "unit_accuracy": sorted([{"unit_id": uid_, "unit_title": unit_title(uid_), "answered": c["answered"], "correct": c["correct"], "accuracy": _pct(c["correct"], c["answered"])}
                                 for uid_, c in unit.items() if uid_], key=lambda x: x["unit_id"]),
        "difficulty_accuracy": [{"difficulty": d, "answered": diff[d]["answered"], "correct": diff[d]["correct"], "accuracy": _pct(diff[d]["correct"], diff[d]["answered"])}
                                for d in ("easy", "medium", "hard") if d in diff],
        "sql": {**sql, "success_rate": _pct(sql["solved"], sql["questions_answered"])},
        "mock_interviews": mocks, "recent_sessions": recent, "trend": trend, "improvement_points": improvement, "weak_topics": weak_areas(attempts),
        "repeated_mistakes": repeated_mistakes(attempts), "attempts_scanned_limit": MAX_ATTEMPTS_SCANNED,
    }


def recommendations(db: Database, user_id: str) -> dict[str, Any]:
    attempts = load_attempts(db, user_id)
    weak = weak_areas(attempts)
    incorrect = latest_incorrect_question_ids(attempts)
    return {
        "has_history": bool(attempts), "weak_topics": weak, "incorrect_question_count": len(incorrect), "repeated_mistake_count": len(repeated_mistakes(attempts)),
        "message": ("Complete a few practice sessions first; recommendations are based only on your recorded answers." if not attempts
                    else ("No topic is currently below the weak-topic threshold." if not weak else f"{len(weak)} topic(s) need revision.")),
        "thresholds": {"min_answered": WEAK_MIN_ANSWERED, "accuracy_below": WEAK_ACCURACY_BELOW},
    }
