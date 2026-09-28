"""
Weakness & strength detection.

Every rule here is deterministic and uses the thresholds documented in
`app.services.progress.aggregation_service` (WEAK_SCORE_THRESHOLD /
STRONG_SCORE_THRESHOLD / MIN_ATTEMPTS). A single bad session never produces
a weakness -- `MIN_ATTEMPTS` is enforced everywhere a threshold is applied
(spec section 9: "Avoid detecting weakness from one bad session").

CTF sessions are intentionally excluded from weakness/strength detection:
they have no numeric score (see `app.models.ctf`), so there is no real
signal to threshold against -- only completion counts, which are surfaced in
the dashboard's activity/overview instead (spec section 3: "Do not invent
metrics that are not actually stored").
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database

from app.db.collections import Collections
from app.services.progress.aggregation_service import (
    MIN_ATTEMPTS,
    STRONG_SCORE_THRESHOLD,
    WEAK_SCORE_THRESHOLD,
    get_communication_summary,
    get_interview_summary,
    get_practice_skill_breakdown,
    get_pressure_summary,
)

_COMM_DIMENSION_LABELS = {
    "clarity_score": "Clarity",
    "grammar_score": "Grammar",
    "vocabulary_score": "Vocabulary",
    "professionalism_score": "Professionalism",
    "confidence_score": "Confidence",
    "relevance_score": "Relevance",
    "conversation_flow_score": "Conversation Flow",
}


def _severity(average_score: int) -> str:
    """Severity within the weak range -- documented, not arbitrary (spec section 9)."""
    if average_score < WEAK_SCORE_THRESHOLD - 20:
        return "high"
    if average_score < WEAK_SCORE_THRESHOLD - 10:
        return "medium"
    return "low"


def detect_practice_weaknesses(skill_breakdown: list[dict]) -> list[dict]:
    return [
        {
            "area": row["category"],
            "skill": row["category"],
            "source": "cybersecurity_practice",
            "severity": _severity(row["average_score"]),
            "evidence": {
                "average_score": row["average_score"],
                "attempts": row["attempts"],
                "threshold": WEAK_SCORE_THRESHOLD,
                "minimum_attempts": MIN_ATTEMPTS,
            },
        }
        for row in skill_breakdown
        if row["status"] == "weak"
    ]


def detect_practice_strengths(skill_breakdown: list[dict]) -> list[str]:
    return [row["category"] for row in skill_breakdown if row["status"] == "strong"]


def detect_interview_weaknesses(interview_summary: dict | None) -> list[dict]:
    if not interview_summary:
        return []
    return [
        {
            "area": topic["label"],
            "skill": topic["topic"],
            "source": "interview",
            "severity": _severity(topic["average_score"]),
            "evidence": {
                "average_score": topic["average_score"],
                "attempts": topic["questions"],
                "threshold": WEAK_SCORE_THRESHOLD,
                "minimum_attempts": MIN_ATTEMPTS,
            },
        }
        for topic in interview_summary.get("topic_breakdown", [])
        if topic["average_score"] < WEAK_SCORE_THRESHOLD and topic["questions"] >= MIN_ATTEMPTS
    ]


def detect_interview_strengths(interview_summary: dict | None) -> list[str]:
    if not interview_summary:
        return []
    return [
        topic["label"]
        for topic in interview_summary.get("topic_breakdown", [])
        if topic["average_score"] >= STRONG_SCORE_THRESHOLD and topic["questions"] >= MIN_ATTEMPTS
    ]


def detect_communication_weaknesses(comm_summary: dict | None) -> list[dict]:
    if not comm_summary or comm_summary["attempts"] < MIN_ATTEMPTS:
        return []
    weaknesses = []
    for field, label in _COMM_DIMENSION_LABELS.items():
        score = comm_summary.get(field)
        if score is not None and score < WEAK_SCORE_THRESHOLD:
            weaknesses.append(
                {
                    "area": f"Communication - {label}",
                    "skill": label,
                    "source": "communication",
                    "severity": _severity(score),
                    "evidence": {
                        "average_score": score,
                        "attempts": comm_summary["attempts"],
                        "threshold": WEAK_SCORE_THRESHOLD,
                        "minimum_attempts": MIN_ATTEMPTS,
                    },
                }
            )
    return weaknesses


def detect_communication_strengths(comm_summary: dict | None) -> list[str]:
    if not comm_summary or comm_summary["attempts"] < MIN_ATTEMPTS:
        return []
    return [
        label
        for field, label in _COMM_DIMENSION_LABELS.items()
        if (comm_summary.get(field) or 0) >= STRONG_SCORE_THRESHOLD
    ]


def detect_pressure_weaknesses(pressure_summary: dict | None) -> list[dict]:
    if not pressure_summary or pressure_summary["attempts"] < MIN_ATTEMPTS:
        return []
    weaknesses = []
    for field, label in (
        ("pressure_handling_score", "Pressure Handling"),
        ("response_control_score", "Response Control Under Pressure"),
    ):
        score = pressure_summary.get(field)
        if score is not None and score < WEAK_SCORE_THRESHOLD:
            weaknesses.append(
                {
                    "area": label,
                    "skill": label,
                    "source": "pressure",
                    "severity": _severity(score),
                    "evidence": {
                        "average_score": score,
                        "attempts": pressure_summary["attempts"],
                        "threshold": WEAK_SCORE_THRESHOLD,
                        "minimum_attempts": MIN_ATTEMPTS,
                    },
                }
            )
    return weaknesses


def detect_all_weaknesses(db: Database, *, user_id: str) -> list[dict]:
    """All deterministically-detected weaknesses across every module, unpersisted."""
    return [
        *detect_practice_weaknesses(get_practice_skill_breakdown(db, user_id=user_id)),
        *detect_interview_weaknesses(get_interview_summary(db, user_id=user_id)),
        *detect_communication_weaknesses(get_communication_summary(db, user_id=user_id)),
        *detect_pressure_weaknesses(get_pressure_summary(db, user_id=user_id)),
    ]


def upsert_weaknesses(db: Database, *, user_id: str, weaknesses: list[dict]) -> list[dict]:
    """
    Replace the user's `user_weaknesses` with the freshly-detected set.
    A weakness that no longer meets the threshold (the user improved) is
    removed rather than left stale (spec section 30: recalculation rebuilds
    derived information from current historical data).
    """
    uid = ObjectId(user_id)
    now = datetime.now(timezone.utc)
    collection = db[Collections.USER_WEAKNESSES]

    current_keys = {(w["area"], w["skill"], w["source"]) for w in weaknesses}
    for existing in collection.find({"user_id": uid}, {"area": 1, "skill": 1, "source": 1}):
        key = (existing["area"], existing["skill"], existing["source"])
        if key not in current_keys:
            collection.delete_one({"_id": existing["_id"]})

    stored: list[dict] = []
    for weakness in weaknesses:
        existing = collection.find_one(
            {"user_id": uid, "area": weakness["area"], "skill": weakness["skill"], "source": weakness["source"]}
        )
        detected_at = existing["detected_at"] if existing else now
        doc = {
            "user_id": uid,
            "area": weakness["area"],
            "skill": weakness["skill"],
            "source": weakness["source"],
            "severity": weakness["severity"],
            "evidence": weakness["evidence"],
            "detected_at": detected_at,
            "last_updated_at": now,
        }
        collection.update_one(
            {"user_id": uid, "area": weakness["area"], "skill": weakness["skill"], "source": weakness["source"]},
            {"$set": doc},
            upsert=True,
        )
        stored.append(doc)
    return stored


def list_weaknesses(db: Database, *, user_id: str) -> list[dict]:
    docs = list(
        db[Collections.USER_WEAKNESSES].find({"user_id": ObjectId(user_id)}).sort("severity", -1)
    )
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        doc["user_id"] = str(doc["user_id"])
    return docs
