"""Time-bucketed metric series (7d daily, 30d daily, 90d weekly, all-time monthly)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from app.services.analytics import config
from app.services.analytics.common import DateRange, as_utc, mean
from app.services.analytics.facts import Facts, spoken_samples

GRANULARITY = {"7d": "day", "30d": "day", "90d": "week", "all": "month", "custom": "week"}

# metric key -> (label, higher_is_better)
METRICS = {
    "technical": ("Technical", True),
    "communication": ("Communication", True),
    "confidence": ("Confidence", True),
    "overall": ("Interview overall", True),
    "structure": ("Answer structure", True),
    "clarity": ("Speaking clarity", True),
    "filler_rate": ("Filler words / 100 words", False),
    "speaking_speed": ("Words per minute", True),
}


def bucket_key(at: datetime, granularity: str) -> str:
    at = as_utc(at)
    if granularity == "day":
        return at.strftime("%Y-%m-%d")
    if granularity == "week":
        return (at - timedelta(days=at.weekday())).strftime("%Y-%m-%d")   # Monday of that week
    return at.strftime("%Y-%m")


def _points(pairs: list[tuple[datetime, float | None]], granularity: str) -> list[dict]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for at, value in pairs:
        if at is not None and value is not None:
            buckets[bucket_key(at, granularity)].append(value)
    return [{"period": k, "value": mean(v, digits=1), "samples": len(v)} for k, v in sorted(buckets.items())]


def trend_direction(points: list[dict], *, higher_is_better: bool) -> str:
    """Direction from the first vs last third of buckets; needs MIN_TREND_POINTS buckets."""
    if len(points) < config.MIN_TREND_POINTS:
        return "insufficient_data"
    third = max(1, len(points) // 3)
    first = mean((p["value"] for p in points[:third]), digits=None)
    last = mean((p["value"] for p in points[-third:]), digits=None)
    delta = (last - first) * (1 if higher_is_better else -1)
    if delta >= config.IMPROVING_DELTA:
        return "improving"
    if delta <= -config.IMPROVING_DELTA:
        return "declining"
    return "stable"


def trend_report(facts: Facts, window: DateRange) -> dict:
    granularity = GRANULARITY.get(window.label, "week")
    qa = facts.interviews
    answers = [(s["at"], a) for s in facts.interviews + facts.pressure for a in s["answers"]]
    spoken = spoken_samples(facts)
    series_pairs = {
        "technical": [(s["at"], s["technical"]) for s in qa],
        "communication": [(s["at"], s["communication"]) for s in qa],
        "confidence": [(s["at"], s["confidence"]) for s in facts.communication],
        "overall": [(s["at"], s["overall"]) for s in qa],
        "structure": [(at, a["structure"]) for at, a in answers if a["structure"] is not None],
        "clarity": [(at, a["clarity"]) for at, a in answers if a["voice"] and a["clarity"] is not None],
        "filler_rate": [(s["at"], s["filler_rate"]) for s in spoken if s.get("filler_rate") is not None],
        "speaking_speed": [(s["at"], s["wpm"]) for s in spoken if s.get("wpm") and (s.get("duration") or 0) >= config.MIN_DURATION_FOR_RATE],
    }
    series = {}
    for key, (label, hib) in METRICS.items():
        pts = _points(series_pairs[key], granularity)
        series[key] = {"label": label, "higher_is_better": hib, "points": pts,
                       "direction": trend_direction(pts, higher_is_better=hib)}
    return {"range": window.label, "granularity": granularity, "series": series}
