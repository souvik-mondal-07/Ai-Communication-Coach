"""
Progress aggregation service.

Pure, deterministic reads over the *existing* session collections written by
Steps 5-10 (`practice_sessions`, `ctf_sessions`, `communication_sessions`,
`interview_sessions`, `pressure_sessions`). Nothing here calls the AI
service, and nothing here writes anything -- it only computes numbers from
what is actually stored, so the dashboard is never guessing at a metric that
doesn't exist for a given module (e.g. CTF sessions have no numeric score,
so CTF's contribution here is completion/attempt counts, never a score).

    cybersecurity_topics categories are the canonical "skill" names used
    throughout Step 11 (Networking, Linux, Web Security, ...). CTF and
    interview signals are folded in by matching their own category/topic
    strings against the same set.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database

from app.db.collections import Collections

# --- Documented thresholds ---------------------------------------------------
# Deliberately the same thresholds `PracticeService`/`InterviewEvaluationService`
# already use (WEAK_THRESHOLD/STRONG_THRESHOLD, WEAK_TOPIC_THRESHOLD), kept as
# a single documented pair here so every Step 11 module (practice, interview,
# communication, pressure) is judged the same way:
#
#   average score <  WEAK_SCORE_THRESHOLD   AND attempts >= MIN_ATTEMPTS  -> weak
#   average score >= STRONG_SCORE_THRESHOLD AND attempts >= MIN_ATTEMPTS  -> strong
#   otherwise                                                             -> developing
#
# A single low-scoring session never classifies anything -- MIN_ATTEMPTS
# guards against that (see spec section 9: "Do not use arbitrary thresholds
# without documenting them").
WEAK_SCORE_THRESHOLD = 60
STRONG_SCORE_THRESHOLD = 80
MIN_ATTEMPTS = 3

_PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90}


def _period_start(period: str) -> datetime:
    days = _PERIOD_DAYS.get(period, 30)
    return datetime.now(timezone.utc) - timedelta(days=days)


def _classify(average_score: float | None, attempts: int) -> str:
    if average_score is None or attempts < MIN_ATTEMPTS:
        return "developing"
    if average_score < WEAK_SCORE_THRESHOLD:
        return "weak"
    if average_score >= STRONG_SCORE_THRESHOLD:
        return "strong"
    return "developing"


def _level_for(average_score: float | None, attempts: int) -> str:
    if average_score is None or attempts == 0:
        return "beginner"
    if attempts < MIN_ATTEMPTS:
        return "developing"
    if average_score >= STRONG_SCORE_THRESHOLD:
        return "proficient"
    if average_score >= WEAK_SCORE_THRESHOLD:
        return "intermediate"
    return "developing"


def _confidence_for(attempts: int) -> str:
    if attempts >= 8:
        return "high"
    if attempts >= MIN_ATTEMPTS:
        return "medium"
    return "low"


# --- Overview -----------------------------------------------------------------


def get_overview_counts(db: Database, *, user_id: str) -> dict:
    """Session counts per module -- total and completed. Real data only."""
    uid = ObjectId(user_id)

    def counts(collection_name: str) -> dict:
        collection = db[collection_name]
        total = collection.count_documents({"user_id": uid})
        completed = collection.count_documents({"user_id": uid, "status": "completed"})
        return {"total": total, "completed": completed}

    return {
        "practice_sessions": counts(Collections.PRACTICE_SESSIONS),
        "ctf_sessions": counts(Collections.CTF_SESSIONS),
        "communication_sessions": counts(Collections.COMMUNICATION_SESSIONS),
        "interview_sessions": counts(Collections.INTERVIEW_SESSIONS),
        "pressure_sessions": counts(Collections.PRESSURE_SESSIONS),
    }


# --- Cybersecurity practice: per-category skill breakdown --------------------


def get_practice_skill_breakdown(db: Database, *, user_id: str) -> list[dict]:
    """
    Per-category performance from completed `practice_sessions` -- the
    primary signal for cybersecurity skill areas (see spec section 8).
    """
    pipeline = [
        {"$match": {"user_id": ObjectId(user_id), "status": "completed"}},
        {
            "$group": {
                "_id": "$category",
                "average_score": {"$avg": "$score"},
                "attempts": {"$sum": 1},
                "successful_attempts": {
                    "$sum": {"$cond": [{"$gte": ["$score", STRONG_SCORE_THRESHOLD]}, 1, 0]}
                },
                "last_practiced_at": {"$max": "$completed_at"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = list(db[Collections.PRACTICE_SESSIONS].aggregate(pipeline))
    breakdown = []
    for row in rows:
        average_score = round(row["average_score"] or 0)
        attempts = row["attempts"]
        breakdown.append(
            {
                "skill": row["_id"],
                "category": row["_id"],
                "average_score": average_score,
                "attempts": attempts,
                "successful_attempts": row["successful_attempts"],
                "status": _classify(average_score, attempts),
                "level": _level_for(average_score, attempts),
                "confidence": _confidence_for(attempts),
                "last_practiced_at": row["last_practiced_at"],
                "source": "cybersecurity_practice",
            }
        )
    return breakdown


def get_ctf_breakdown(db: Database, *, user_id: str) -> list[dict]:
    """
    Per-category CTF activity. CTF sessions have no numeric score (see
    `app.models.ctf`) -- only completion and hint usage are real signals.
    """
    pipeline = [
        {"$match": {"user_id": ObjectId(user_id)}},
        {
            "$group": {
                "_id": "$category",
                "attempts": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                "hints_used_total": {"$sum": "$hints_used"},
                "last_activity_at": {"$max": "$updated_at"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = list(db[Collections.CTF_SESSIONS].aggregate(pipeline))
    return [
        {
            "category": row["_id"],
            "attempts": row["attempts"],
            "completed": row["completed"],
            "completion_rate": round(100 * row["completed"] / row["attempts"]) if row["attempts"] else 0,
            "average_hints_used": round(row["hints_used_total"] / row["attempts"], 1) if row["attempts"] else 0,
            "last_activity_at": row["last_activity_at"],
        }
        for row in rows
    ]


# --- Communication -------------------------------------------------------------

_COMM_SCORE_FIELDS = [
    "overall_score",
    "clarity_score",
    "grammar_score",
    "vocabulary_score",
    "professionalism_score",
    "confidence_score",
    "relevance_score",
    "conversation_flow_score",
]


def get_communication_summary(db: Database, *, user_id: str) -> dict | None:
    """Average communication-evaluation scores over completed sessions, or None if there are none."""
    query = {"user_id": ObjectId(user_id), "status": "completed", "evaluation": {"$ne": None}}
    collection = db[Collections.COMMUNICATION_SESSIONS]
    attempts = collection.count_documents(query)
    if attempts == 0:
        return None

    group_stage = {"_id": None, "attempts": {"$sum": 1}}
    for field in _COMM_SCORE_FIELDS:
        group_stage[field] = {"$avg": f"$evaluation.{field}"}

    pipeline = [{"$match": query}, {"$group": group_stage}]
    row = next(iter(db[Collections.COMMUNICATION_SESSIONS].aggregate(pipeline)), None)
    if row is None:
        return None

    last = collection.find_one(query, sort=[("completed_at", DESCENDING)])
    return {
        "attempts": attempts,
        **{field: round(row.get(field) or 0) for field in _COMM_SCORE_FIELDS},
        "last_session_at": last["completed_at"] if last else None,
    }


# --- Interview -------------------------------------------------------------


def get_interview_summary(db: Database, *, user_id: str) -> dict | None:
    """
    Average overall/technical/communication scores from completed
    `interview_sessions.final_evaluation`, plus a per-topic breakdown built
    from each session's own `topic_scores` (already computed deterministically
    by the Step 9 evaluator -- never recomputed here).
    """
    query = {"user_id": ObjectId(user_id), "status": "completed", "final_evaluation": {"$ne": None}}
    collection = db[Collections.INTERVIEW_SESSIONS]
    attempts = collection.count_documents(query)
    if attempts == 0:
        return None

    docs = list(collection.find(query, {"final_evaluation": 1, "completed_at": 1}))
    overall = [d["final_evaluation"].get("overall_score") for d in docs if d["final_evaluation"].get("overall_score") is not None]
    technical = [d["final_evaluation"].get("technical_score") for d in docs if d["final_evaluation"].get("technical_score") is not None]
    communication = [d["final_evaluation"].get("communication_score") for d in docs if d["final_evaluation"].get("communication_score") is not None]

    topics: dict[str, dict] = {}
    for doc in docs:
        for topic_score in doc["final_evaluation"].get("topic_scores") or []:
            key = topic_score.get("topic") or topic_score.get("label")
            if not key or topic_score.get("average_score") is None:
                continue
            bucket = topics.setdefault(key, {"label": topic_score.get("label", key), "scores": [], "questions": 0})
            bucket["scores"].append(topic_score["average_score"])
            bucket["questions"] += topic_score.get("questions", 0)

    topic_breakdown = [
        {
            "topic": topic,
            "label": bucket["label"],
            "average_score": round(sum(bucket["scores"]) / len(bucket["scores"])),
            "sessions": len(bucket["scores"]),
            "questions": bucket["questions"],
        }
        for topic, bucket in topics.items()
    ]
    topic_breakdown.sort(key=lambda t: t["average_score"])

    last = collection.find_one(query, sort=[("completed_at", DESCENDING)])
    return {
        "attempts": attempts,
        "overall_score": round(sum(overall) / len(overall)) if overall else 0,
        "technical_score": round(sum(technical) / len(technical)) if technical else 0,
        "communication_score": round(sum(communication) / len(communication)) if communication else 0,
        "topic_breakdown": topic_breakdown,
        "last_session_at": last["completed_at"] if last else None,
    }


# --- Pressure ----------------------------------------------------------------


def get_pressure_summary(db: Database, *, user_id: str) -> dict | None:
    """
    Average pressure-specific scores from completed `pressure_sessions`.
    Only uses fields the Step 10 evaluator actually produces -- never a
    fabricated psychological score (see `app.models.pressure`).
    """
    query = {"user_id": ObjectId(user_id), "status": "completed", "final_evaluation": {"$ne": None}}
    collection = db[Collections.PRESSURE_SESSIONS]
    attempts = collection.count_documents(query)
    if attempts == 0:
        return None

    docs = list(collection.find(query, {"final_evaluation": 1, "completed_at": 1}))

    def collect(field: str) -> list[int]:
        return [d["final_evaluation"].get(field) for d in docs if d["final_evaluation"].get(field) is not None]

    handling = collect("pressure_handling_score")
    control = collect("response_control_score")
    overall = collect("overall_score")

    indicators: list[str] = []
    for doc in docs:
        indicators.extend(doc["final_evaluation"].get("pressure_indicators") or [])

    last = collection.find_one(query, sort=[("completed_at", DESCENDING)])
    return {
        "attempts": attempts,
        "overall_score": round(sum(overall) / len(overall)) if overall else 0,
        "pressure_handling_score": round(sum(handling) / len(handling)) if handling else None,
        "response_control_score": round(sum(control) / len(control)) if control else None,
        "recent_indicators": indicators[-6:],
        "last_session_at": last["completed_at"] if last else None,
    }


# --- Trends --------------------------------------------------------------------

_TREND_SOURCES: dict[str, tuple[str, str]] = {
    # dimension -> (collection, score field on the completed document)
    "technical": (Collections.PRACTICE_SESSIONS, "score"),
    "communication": (Collections.COMMUNICATION_SESSIONS, "evaluation.overall_score"),
    "interview": (Collections.INTERVIEW_SESSIONS, "final_evaluation.overall_score"),
    "pressure": (Collections.PRESSURE_SESSIONS, "final_evaluation.overall_score"),
}


def _dig(doc: dict, dotted_path: str):
    value = doc
    for part in dotted_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _timestamp_field(collection_name: str) -> str:
    return "completed_at"


def get_trend_series(db: Database, *, user_id: str, dimension: str, period: str) -> dict:
    """
    Historical score series for one dimension, bucketed by week within
    `period`. Returns `insufficient_data=True` rather than a misleading trend
    when there aren't enough data points (see spec section 7/11/29).
    """
    if dimension == "overall":
        return _overall_trend_series(db, user_id=user_id, period=period)

    collection_name, score_path = _TREND_SOURCES[dimension]
    since = _period_start(period)
    match: dict = {
        "user_id": ObjectId(user_id),
        "status": "completed",
        _timestamp_field(collection_name): {"$gte": since},
    }
    docs = list(
        db[collection_name]
        .find(match)
        .sort(_timestamp_field(collection_name), 1)
    )

    points: list[tuple[datetime, int]] = []
    for doc in docs:
        score = _dig(doc, score_path)
        ts = doc.get(_timestamp_field(collection_name))
        if score is not None and ts is not None:
            points.append((ts, score))

    return _bucket_by_week(points)


def _overall_trend_series(db: Database, *, user_id: str, period: str) -> dict:
    """A single combined trend averaged across whichever dimensions have data for each week."""
    since = _period_start(period)
    all_points: list[tuple[datetime, int]] = []
    for collection_name, score_path in _TREND_SOURCES.values():
        match = {
            "user_id": ObjectId(user_id),
            "status": "completed",
            _timestamp_field(collection_name): {"$gte": since},
        }
        for doc in db[collection_name].find(match):
            score = _dig(doc, score_path)
            ts = doc.get(_timestamp_field(collection_name))
            if score is not None and ts is not None:
                all_points.append((ts, score))
    all_points.sort(key=lambda p: p[0])
    return _bucket_by_week(all_points)


def _bucket_by_week(points: list[tuple[datetime, int]]) -> dict:
    if not points:
        return {"points": [], "trend": "insufficient_data"}

    buckets: dict[str, list[int]] = {}
    for ts, score in points:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        iso_year, iso_week, _ = ts.isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        buckets.setdefault(key, []).append(score)

    ordered_keys = sorted(buckets.keys())
    series = [
        {"period": key, "average_score": round(sum(buckets[key]) / len(buckets[key])), "count": len(buckets[key])}
        for key in ordered_keys
    ]

    if len(series) < 2:
        trend = "insufficient_data"
    else:
        half = max(1, len(series) // 2)
        early = series[:half]
        late = series[half:] or series[-1:]
        early_avg = sum(p["average_score"] for p in early) / len(early)
        late_avg = sum(p["average_score"] for p in late) / len(late)
        if late_avg - early_avg >= 5:
            trend = "improving"
        elif early_avg - late_avg >= 5:
            trend = "declining"
        else:
            trend = "stable"

    return {"points": series, "trend": trend}


# --- Recent activity -----------------------------------------------------------


def get_recent_activity(db: Database, *, user_id: str, limit: int = 15) -> list[dict]:
    """Merged, timestamp-sorted list of recently completed sessions across every module. Real data only."""
    uid = ObjectId(user_id)
    activity: list[dict] = []

    for doc in db[Collections.PRACTICE_SESSIONS].find(
        {"user_id": uid, "status": "completed"}, {"topic_title": 1, "category": 1, "score": 1, "completed_at": 1}
    ):
        activity.append(
            {
                "type": "practice",
                "label": f"Completed {doc.get('topic_title', 'Practice')} practice",
                "category": doc.get("category"),
                "score": doc.get("score"),
                "completed_at": doc.get("completed_at"),
            }
        )

    for doc in db[Collections.CTF_SESSIONS].find(
        {"user_id": uid, "status": "completed"}, {"title": 1, "category": 1, "completed_at": 1}
    ):
        activity.append(
            {
                "type": "ctf",
                "label": f"Completed CTF session: {doc.get('title', doc.get('category', 'Challenge'))}",
                "category": doc.get("category"),
                "score": None,
                "completed_at": doc.get("completed_at"),
            }
        )

    for doc in db[Collections.COMMUNICATION_SESSIONS].find(
        {"user_id": uid, "status": "completed"},
        {"scenario_title": 1, "category": 1, "evaluation.overall_score": 1, "completed_at": 1},
    ):
        activity.append(
            {
                "type": "communication",
                "label": f"Completed Communication practice: {doc.get('scenario_title', '')}".strip(),
                "category": doc.get("category"),
                "score": (doc.get("evaluation") or {}).get("overall_score"),
                "completed_at": doc.get("completed_at"),
            }
        )

    for doc in db[Collections.INTERVIEW_SESSIONS].find(
        {"user_id": uid, "status": "completed"},
        {"interview_type": 1, "final_evaluation.overall_score": 1, "completed_at": 1},
    ):
        activity.append(
            {
                "type": "interview",
                "label": f"Completed {doc.get('interview_type', 'Interview')} interview",
                "category": doc.get("interview_type"),
                "score": (doc.get("final_evaluation") or {}).get("overall_score"),
                "completed_at": doc.get("completed_at"),
            }
        )

    for doc in db[Collections.PRESSURE_SESSIONS].find(
        {"user_id": uid, "status": "completed"},
        {"pressure_level": 1, "final_evaluation.overall_score": 1, "completed_at": 1},
    ):
        activity.append(
            {
                "type": "pressure",
                "label": f"Completed Pressure Training (level {doc.get('pressure_level')})",
                "category": None,
                "score": (doc.get("final_evaluation") or {}).get("overall_score"),
                "completed_at": doc.get("completed_at"),
            }
        )

    activity = [a for a in activity if a["completed_at"] is not None]
    activity.sort(key=lambda a: a["completed_at"], reverse=True)
    return activity[:limit]
