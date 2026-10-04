"""
Evidence-gated strength / weakness classification over topic performance rows.

Reuses the Step 11 thresholds (WEAK 60 / STRONG 80 / MIN_ATTEMPTS 3) so the
dashboard, progress page and personalization never disagree. A topic is only
labelled when it has at least MIN_ATTEMPTS completed practice sessions --
a single bad (or good) session never classifies anything.
"""

from __future__ import annotations

from app.services.progress.aggregation_service import (
    MIN_ATTEMPTS,
    STRONG_SCORE_THRESHOLD,
    WEAK_SCORE_THRESHOLD,
)

# Average hints per CTF session at/above which hint reliance counts as evidence.
HIGH_HINT_USAGE = 2.0


def _severity(score: int) -> str:
    if score < WEAK_SCORE_THRESHOLD - 20:
        return "high"
    if score < WEAK_SCORE_THRESHOLD - 10:
        return "medium"
    return "low"


def _evidence(row: dict) -> list[str]:
    """Short, observable facts only -- these are shown to the user."""
    facts = [f"{row['attempts']} practice sessions, average {row['average_score']}/100"]
    if row.get("accuracy") is not None:
        facts.append(f"{round(row['accuracy'] * 100)}% of questions answered correctly")
    if row.get("trend") in ("improving", "declining"):
        facts.append(f"recent performance is {row['trend']}")
    if row.get("hint_usage") is not None and row.get("ctf_attempts", 0) >= 2:
        facts.append(f"{row['hint_usage']} hints per CTF session on average")
    if row.get("interview_average") is not None and row.get("interview_questions", 0) >= MIN_ATTEMPTS:
        facts.append(f"interview answers on this topic average {row['interview_average']}/100")
    return facts


def classify(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (strengths, weaknesses), each sorted most-notable first."""
    strengths: list[dict] = []
    weaknesses: list[dict] = []
    for row in rows:
        if row["attempts"] < MIN_ATTEMPTS or row["average_score"] is None:
            continue
        avg = row["average_score"]
        # Use the recent average as a tie-breaker so an improving topic that was
        # weak long ago is not still flagged weak.
        recent = row["recent_average"] if row["recent_average"] is not None else avg
        if avg < WEAK_SCORE_THRESHOLD and not (row["trend"] == "improving" and recent >= WEAK_SCORE_THRESHOLD):
            weaknesses.append(
                {"topic": row["topic"], "key": row["key"], "severity": _severity(avg),
                 "average_score": avg, "trend": row["trend"], "evidence": _evidence(row)}
            )
        elif avg >= STRONG_SCORE_THRESHOLD and row["trend"] != "declining":
            strengths.append(
                {"topic": row["topic"], "key": row["key"],
                 "average_score": avg, "trend": row["trend"], "evidence": _evidence(row)}
            )
    rank = {"high": 0, "medium": 1, "low": 2}
    weaknesses.sort(key=lambda w: (rank[w["severity"]], w["average_score"]))
    strengths.sort(key=lambda s: -s["average_score"])
    return strengths, weaknesses
