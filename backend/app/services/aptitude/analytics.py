"""
Progress analytics and weak-topic detection, computed only from the user's recorded attempts
(`aptitude_attempts`, written once per question when a session is finalised). Nothing is
estimated or invented: with no attempts the functions return empty results.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from bson import ObjectId
from pymongo.database import Database

from app.db.collections import Collections
from app.services.aptitude.syllabus import SUBTOPIC_TITLES, TOPIC_BY_ID, topic_title

WEAK_MIN_ANSWERED = 5          # a topic needs this many answered questions before it can be called weak
WEAK_ACCURACY_BELOW = 60.0     # percent
WEAK_SUBTOPIC_MIN = 3
WEAK_SUBTOPIC_BELOW = 50.0
MAX_ATTEMPTS_SCANNED = 5000    # most recent attempts considered (documented bound)


def _pct(correct: int, total: int) -> float:
    return round(100.0 * correct / total, 1) if total else 0.0


def load_attempts(db: Database, user_id: str) -> list[dict]:
    return list(db[Collections.APTITUDE_ATTEMPTS].find({"user_id": ObjectId(user_id)}).sort("created_at", -1).limit(MAX_ATTEMPTS_SCANNED))


def weak_areas(attempts: list[dict]) -> list[dict[str, Any]]:
    """Topics with enough answered questions and accuracy below the threshold, weakest first."""
    per_topic: dict[str, dict[str, int]] = defaultdict(lambda: {"answered": 0, "correct": 0})
    per_sub: dict[str, dict[str, int]] = defaultdict(lambda: {"answered": 0, "correct": 0})
    for a in attempts:
        if a["outcome"] == "unanswered":
            continue
        per_topic[a["topic_id"]]["answered"] += 1
        per_sub[a["subtopic_id"]]["answered"] += 1
        if a["outcome"] == "correct":
            per_topic[a["topic_id"]]["correct"] += 1
            per_sub[a["subtopic_id"]]["correct"] += 1
    out = []
    for topic_id, c in per_topic.items():
        acc = _pct(c["correct"], c["answered"])
        if c["answered"] >= WEAK_MIN_ANSWERED and acc < WEAK_ACCURACY_BELOW and topic_id in TOPIC_BY_ID:
            subs = []
            for s in TOPIC_BY_ID[topic_id].subtopics:
                sc = per_sub.get(s.id)
                if sc and sc["answered"] >= WEAK_SUBTOPIC_MIN and _pct(sc["correct"], sc["answered"]) < WEAK_SUBTOPIC_BELOW:
                    subs.append({"subtopic_id": s.id, "title": s.title, "accuracy": _pct(sc["correct"], sc["answered"]), "answered": sc["answered"]})
            subs.sort(key=lambda x: x["accuracy"])
            out.append({
                "topic_id": topic_id, "topic_title": topic_title(topic_id), "answered": c["answered"], "correct": c["correct"], "accuracy": acc,
                "reason": f"{acc}% accuracy over {c['answered']} answered questions (below {int(WEAK_ACCURACY_BELOW)}%).",
                "weak_subtopics": subs,
            })
    out.sort(key=lambda x: (x["accuracy"], -x["answered"]))
    return out


def latest_incorrect_question_ids(attempts: list[dict]) -> list[str]:
    """Questions whose most recent recorded outcome was incorrect (attempts are newest first)."""
    latest: dict[str, str] = {}
    for a in attempts:
        latest.setdefault(a["question_id"], a["outcome"])
    return [qid for qid, outcome in latest.items() if outcome == "incorrect"]


def progress_summary(db: Database, user_id: str) -> dict[str, Any]:
    uid = ObjectId(user_id)
    attempts = load_attempts(db, user_id)
    answered = [a for a in attempts if a["outcome"] != "unanswered"]
    correct = sum(1 for a in attempts if a["outcome"] == "correct")
    topic: dict[str, dict[str, int]] = defaultdict(lambda: {"answered": 0, "correct": 0, "presented": 0})
    diff: dict[str, dict[str, int]] = defaultdict(lambda: {"answered": 0, "correct": 0})
    for a in attempts:
        t = topic[a["topic_id"]]
        t["presented"] += 1
        if a["outcome"] != "unanswered":
            t["answered"] += 1
            diff[a["difficulty"]]["answered"] += 1
        if a["outcome"] == "correct":
            t["correct"] += 1
            diff[a["difficulty"]]["correct"] += 1
    sessions = list(db[Collections.APTITUDE_SESSIONS].find({"user_id": uid, "status": "completed", "result": {"$exists": True}}, {"mode": 1, "result": 1, "started_at": 1, "finished_at": 1}).sort("finished_at", -1).limit(50))
    recent = [{
        "session_id": str(s["_id"]), "mode": s["mode"], "score": s["result"]["score"], "total": s["result"]["total_questions"], "accuracy": s["result"]["accuracy"],
        "time_taken_seconds": s["result"]["time_taken_seconds"], "finished_at": s["finished_at"],
    } for s in sessions[:10]]
    chron = list(reversed(sessions[:20]))
    trend = [{"session_id": str(s["_id"]), "accuracy": s["result"]["accuracy"], "finished_at": s["finished_at"]} for s in chron]
    improvement = None
    if len(chron) >= 4:
        half = len(chron) // 2
        early = sum(s["result"]["accuracy"] for s in chron[:half]) / half
        late = sum(s["result"]["accuracy"] for s in chron[half:]) / (len(chron) - half)
        improvement = round(late - early, 1)
    avg_secs = None
    if sessions:
        avg_secs = round(sum(s["result"]["average_seconds_per_question"] for s in sessions) / len(sessions), 1)
    return {
        "sessions_completed": db[Collections.APTITUDE_SESSIONS].count_documents({"user_id": uid, "status": "completed"}),
        "questions_presented": len(attempts), "questions_answered": len(answered), "correct": correct,
        "incorrect": len(answered) - correct, "unanswered": len(attempts) - len(answered),
        "accuracy": _pct(correct, len(answered)), "average_seconds_per_question": avg_secs,
        "topic_accuracy": sorted(
            [{"topic_id": tid, "topic_title": topic_title(tid), "answered": c["answered"], "correct": c["correct"], "presented": c["presented"], "accuracy": _pct(c["correct"], c["answered"])}
             for tid, c in topic.items()], key=lambda x: x["topic_title"]),
        "difficulty_accuracy": [{"difficulty": d, "answered": diff[d]["answered"], "correct": diff[d]["correct"], "accuracy": _pct(diff[d]["correct"], diff[d]["answered"])}
                                for d in ("easy", "medium", "hard") if d in diff],
        "recent_sessions": recent, "trend": trend, "improvement_points": improvement,
        "weak_topics": weak_areas(attempts),
        "attempts_scanned_limit": MAX_ATTEMPTS_SCANNED,
    }


def recommendations(db: Database, user_id: str) -> dict[str, Any]:
    attempts = load_attempts(db, user_id)
    weak = weak_areas(attempts)
    incorrect = latest_incorrect_question_ids(attempts)
    return {
        "has_history": bool(attempts), "weak_topics": weak, "incorrect_question_count": len(incorrect),
        "message": (
            "Complete a few practice sessions first; recommendations are based only on your recorded answers." if not attempts
            else ("No topic is currently below the weak-topic threshold." if not weak else f"{len(weak)} topic(s) need revision.")
        ),
        "thresholds": {"min_answered": WEAK_MIN_ANSWERED, "accuracy_below": WEAK_ACCURACY_BELOW},
    }


__all__ = ["progress_summary", "recommendations", "weak_areas", "latest_incorrect_question_ids", "load_attempts", "SUBTOPIC_TITLES"]
