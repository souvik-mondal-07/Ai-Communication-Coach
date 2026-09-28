"""
Recommendation engine.

Every recommendation is generated from a detected weakness or another
real, stored signal -- never an arbitrary suggestion (spec section 12:
"Do NOT generate arbitrary recommendations", "Recommendations must explain
WHY they were generated"). `build_recommendations()` is pure and testable in
isolation from MongoDB; `upsert_recommendations()` persists the result
without duplicating an already-active (incomplete) recommendation for the
same area/topic.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database

from app.db.collections import Collections

# A CTF category is flagged for more practice once there's enough attempts
# to be meaningful and completion is still under half -- documented,
# evidence-based, and CTF-appropriate (CTF sessions have no numeric score,
# so completion rate is the only real signal available; see
# `app.services.progress.aggregation_service.get_ctf_breakdown`).
CTF_MIN_ATTEMPTS = 3
CTF_LOW_COMPLETION_RATE = 50

_SEVERITY_TO_PRIORITY = {"high": "high", "medium": "medium", "low": "low"}


class RecommendationError(Exception):
    pass


class RecommendationNotFoundError(RecommendationError):
    pass


class RecommendationForbiddenError(RecommendationError):
    pass


def _from_weakness(weakness: dict) -> dict:
    evidence = weakness["evidence"]
    priority = _SEVERITY_TO_PRIORITY.get(weakness["severity"], "medium")

    if weakness["source"] == "cybersecurity_practice":
        return {
            "type": "practice",
            "area": weakness["area"],
            "topic": weakness["skill"],
            "priority": priority,
            "reason": (
                f"Repeated low scores in {weakness['area']} practice sessions "
                f"(average {evidence['average_score']}/100 over {evidence['attempts']} attempts)."
            ),
        }
    if weakness["source"] == "interview":
        return {
            "type": "interview",
            "area": weakness["area"],
            "topic": weakness["skill"],
            "priority": priority,
            "reason": (
                f"Interview questions on {weakness['area']} have repeatedly scored low "
                f"(average {evidence['average_score']}/100 over {evidence['attempts']} questions)."
            ),
        }
    if weakness["source"] == "communication":
        return {
            "type": "communication",
            "area": weakness["area"],
            "topic": weakness["skill"],
            "priority": priority,
            "reason": (
                f"{weakness['skill']} has repeatedly scored low in communication sessions "
                f"(average {evidence['average_score']}/100 over {evidence['attempts']} sessions)."
            ),
        }
    # source == "pressure"
    return {
        "type": "pressure",
        "area": weakness["area"],
        "topic": weakness["skill"],
        "priority": priority,
        "reason": (
            f"{weakness['area']} has repeatedly scored low in pressure training "
            f"(average {evidence['average_score']}/100 over {evidence['attempts']} sessions)."
        ),
    }


def _from_ctf_breakdown(ctf_breakdown: list[dict]) -> list[dict]:
    recommendations = []
    for row in ctf_breakdown:
        if row["attempts"] >= CTF_MIN_ATTEMPTS and row["completion_rate"] < CTF_LOW_COMPLETION_RATE:
            recommendations.append(
                {
                    "type": "ctf",
                    "area": row["category"],
                    "topic": row["category"],
                    "priority": "medium",
                    "reason": (
                        f"Only {row['completion_rate']}% of {row['category']} CTF sessions have been "
                        f"completed over {row['attempts']} attempts."
                    ),
                }
            )
    return recommendations


def build_recommendations(weaknesses: list[dict], ctf_breakdown: list[dict]) -> list[dict]:
    """Pure function: weaknesses + CTF completion data -> recommendation dicts (unpersisted)."""
    return [_from_weakness(w) for w in weaknesses] + _from_ctf_breakdown(ctf_breakdown)


def upsert_recommendations(db: Database, *, user_id: str, recommendations: list[dict]) -> None:
    """
    Insert any recommendation that doesn't already have an active
    (incomplete) match for the same (type, area, topic). Existing active
    recommendations are left untouched -- completing one is a user action,
    not something recalculation should silently undo or duplicate.
    """
    uid = ObjectId(user_id)
    collection = db[Collections.RECOMMENDATIONS]
    now = datetime.now(timezone.utc)

    for rec in recommendations:
        existing = collection.find_one(
            {
                "user_id": uid,
                "type": rec["type"],
                "area": rec["area"],
                "topic": rec["topic"],
                "completed": False,
            }
        )
        if existing is not None:
            continue
        collection.insert_one(
            {
                "user_id": uid,
                "type": rec["type"],
                "area": rec["area"],
                "topic": rec["topic"],
                "priority": rec["priority"],
                "reason": rec["reason"],
                "created_at": now,
                "completed": False,
                "completed_at": None,
            }
        )


def list_recommendations(db: Database, *, user_id: str, active_only: bool = True) -> list[dict]:
    query: dict = {"user_id": ObjectId(user_id)}
    if active_only:
        query["completed"] = False
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    docs = list(db[Collections.RECOMMENDATIONS].find(query).sort("created_at", -1))
    docs.sort(key=lambda d: priority_rank.get(d.get("priority"), 3))
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        doc["user_id"] = str(doc["user_id"])
    return docs


def complete_recommendation(db: Database, *, user_id: str, recommendation_id: str) -> dict:
    try:
        object_id = ObjectId(recommendation_id)
    except (InvalidId, TypeError) as exc:
        raise RecommendationNotFoundError(recommendation_id) from exc

    collection = db[Collections.RECOMMENDATIONS]
    doc = collection.find_one({"_id": object_id})
    if doc is None:
        raise RecommendationNotFoundError(recommendation_id)
    if str(doc["user_id"]) != user_id:
        raise RecommendationForbiddenError(recommendation_id)

    now = datetime.now(timezone.utc)
    collection.update_one({"_id": object_id}, {"$set": {"completed": True, "completed_at": now}})
    doc["completed"] = True
    doc["completed_at"] = now
    doc["_id"] = str(doc["_id"])
    doc["user_id"] = str(doc["user_id"])
    return doc
