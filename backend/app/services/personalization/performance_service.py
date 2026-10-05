"""
Per-topic performance model, derived from existing data only.

One normalised row per cybersecurity category (the same canonical "skill"
names Step 5/11 use). Signals come from:

* completed `practice_sessions`  -> attempts, questions, correct, scores, trend
* `ctf_sessions`                 -> attempts, completions, hint usage
* completed interview sessions   -> per-topic average score (when the topic
                                    maps onto a category)

Hint usage exists only for CTF sessions; practice sessions store none, so
`hint_usage` is `None` (never a fabricated 0) when there is no CTF data.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database

from app.db.collections import Collections
from app.services.cybersecurity.practice_results import session_category_entries
from app.services.progress import aggregation_service as agg

# Minimum completed practice sessions needed before a trend is reported.
# Four = two "previous" + two "recent"; fewer is noise, not a trend.
MIN_TREND_POINTS = 4
# Recent-vs-previous average change (score points) that counts as a trend.
TREND_DELTA = 5
# Recent window used for the "recent average".
RECENT_WINDOW = 3

# Interview topic ids / labels -> practice category, where an honest match exists.
_INTERVIEW_ALIASES = {
    "networking": "Networking",
    "network_security": "Networking",
    "linux": "Linux",
    "web_security": "Web Security",
    "soc_blue_team": "SOC",
    "soc": "SOC",
    "siem": "SIEM",
    "penetration_testing": "Penetration Testing",
    "active_directory": "Active Directory",
    "cloud_security": "Cloud Security",
    "cryptography": "Cryptography",
    "digital_forensics": "Digital Forensics",
    "incident_response": "Incident Response",
    "threat_intelligence": "Threat Intelligence",
}


def topic_key(label: str) -> str:
    """'Web Security' -> 'web_security' (stable id shared with profile interests)."""
    return re.sub(r"[^a-z0-9]+", "_", (label or "").lower()).strip("_")


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def compute_trend(scores: list[int | float]) -> str:
    """`scores` oldest -> newest. Needs MIN_TREND_POINTS before saying anything."""
    if len(scores) < MIN_TREND_POINTS:
        return "insufficient_data"
    recent = scores[-RECENT_WINDOW:]
    previous = scores[:-RECENT_WINDOW] or scores[:1]
    delta = sum(recent) / len(recent) - sum(previous) / len(previous)
    if delta >= TREND_DELTA:
        return "improving"
    if delta <= -TREND_DELTA:
        return "declining"
    return "stable"


def _practice_rows(db: Database, user_id: str) -> dict[str, dict]:
    docs = db[Collections.PRACTICE_SESSIONS].find(
        {"user_id": ObjectId(user_id), "status": "completed", "score": {"$ne": None}},
        {"category": 1, "score": 1, "correct_answers": 1, "questions_answered": 1,
         "difficulty": 1, "completed_at": 1, "topic_slug": 1, "category_results": 1},
    )
    # Step 17: a session spanning several categories credits each category with
    # the score for its own questions (single-category sessions are unchanged).
    by_cat: dict[str, list[dict]] = {}
    for doc in docs:
        for entry in session_category_entries(doc):
            by_cat.setdefault(entry["category"], []).append(
                {**entry, "difficulty": doc.get("difficulty"), "completed_at": doc.get("completed_at")}
            )

    rows: dict[str, dict] = {}
    for category, sessions in by_cat.items():
        sessions.sort(key=lambda d: _as_utc(d.get("completed_at")) or datetime.min.replace(tzinfo=timezone.utc))
        scores = [s["score"] for s in sessions]
        questions = sum(s.get("questions_answered") or 0 for s in sessions)
        correct = sum(s.get("correct_answers") or 0 for s in sessions)
        recent = scores[-RECENT_WINDOW:]
        rows[category] = {
            "attempts": len(sessions),
            "questions": questions,
            "correct": correct,
            "accuracy": round(correct / questions, 2) if questions else None,
            "average_score": round(sum(scores) / len(scores)),
            "recent_average": round(sum(recent) / len(recent)),
            "trend": compute_trend(scores),
            "last_difficulty": sessions[-1].get("difficulty"),
            "last_practiced": _as_utc(sessions[-1].get("completed_at")),
        }
    return rows


def build_topic_performance(
    db: Database, *, user_id: str, ctf_breakdown: list[dict], interview_summary: dict | None
) -> list[dict]:
    """
    Derived per-topic summaries (never a copy of the underlying history).

    The CTF breakdown and interview summary are passed in so the caller reads
    each collection once per personalization request.
    """
    practice = _practice_rows(db, user_id)
    ctf = {row["category"]: row for row in ctf_breakdown}
    interview = interview_summary or {}

    interview_by_cat: dict[str, dict] = {}
    for item in interview.get("topic_breakdown", []):
        category = _INTERVIEW_ALIASES.get(item["topic"]) or _INTERVIEW_ALIASES.get(topic_key(item.get("label", "")))
        if category:
            interview_by_cat[category] = item

    rows = []
    for category in sorted(set(practice) | set(ctf) | set(interview_by_cat)):
        p = practice.get(category, {})
        c = ctf.get(category)
        i = interview_by_cat.get(category)
        rows.append(
            {
                "topic": category,
                "key": topic_key(category),
                "attempts": p.get("attempts", 0),
                "questions": p.get("questions", 0),
                "correct": p.get("correct", 0),
                "accuracy": p.get("accuracy"),
                "average_score": p.get("average_score"),
                "recent_average": p.get("recent_average"),
                "trend": p.get("trend", "insufficient_data"),
                "last_difficulty": p.get("last_difficulty"),
                "last_practiced": p.get("last_practiced"),
                "hint_usage": c["average_hints_used"] if c else None,
                "ctf_attempts": c["attempts"] if c else 0,
                "ctf_completed": c["completed"] if c else 0,
                "interview_average": i["average_score"] if i else None,
                "interview_questions": i["questions"] if i else 0,
            }
        )
    return rows


def build_communication_signals(comm: dict | None, pressure: dict | None) -> dict | None:
    """
    Recorded communication results only (Step 7/9/10 evaluations). Filler-word
    and speaking-speed analytics are not stored per user, so they are not
    reported here -- no invented metrics.
    """
    if not comm and not pressure:
        return None
    return {
        "communication_sessions": comm["attempts"] if comm else 0,
        "overall_score": comm["overall_score"] if comm else None,
        "clarity_score": comm["clarity_score"] if comm else None,
        "confidence_score": comm["confidence_score"] if comm else None,
        "pressure_sessions": pressure["attempts"] if pressure else 0,
        "pressure_handling_score": pressure["pressure_handling_score"] if pressure else None,
    }
