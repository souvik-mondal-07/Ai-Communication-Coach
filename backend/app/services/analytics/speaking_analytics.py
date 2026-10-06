"""
Speaking analytics from stored Step 8 voice metrics.

Only spoken answers contribute. With no voice data the report says so
(`available: false`) -- there are no zeros and no estimates. Pause rate needs
both a pause count and a measured duration; answers lacking either are simply
left out of that metric.
"""

from __future__ import annotations

from app.services.analytics import config
from app.services.analytics.common import mean
from app.services.analytics.facts import Facts, spoken_samples


def _usable_for_rate(s: dict) -> bool:
    return (s["words"] or 0) >= config.MIN_WORDS_FOR_RATE and (s.get("duration") or 0) >= config.MIN_DURATION_FOR_RATE


def aggregate_samples(samples: list[dict]) -> dict:
    """Aggregate metrics over spoken samples; every metric is None when it cannot be measured."""
    timed = [s for s in samples if _usable_for_rate(s)]
    pausable = [s for s in timed if s.get("pauses") is not None]
    words_total = sum(s["words"] for s in samples)
    fillers_known = [s for s in samples if s.get("fillers") is not None]
    filler_words = sum(s["fillers"] for s in fillers_known)
    filler_base = sum(s["words"] for s in fillers_known)
    pause_minutes = sum(s["duration"] for s in pausable) / 60
    return {
        "spoken_answers": len(samples),
        "words_per_minute": mean((s["wpm"] for s in timed), digits=0),
        "filler_per_100_words": round(filler_words / filler_base * 100, 1) if filler_base else None,
        "total_filler_words": filler_words if fillers_known else None,
        "pauses_per_minute": round(sum(s["pauses"] for s in pausable) / pause_minutes, 1) if pause_minutes else None,
        "long_pauses": sum(s.get("long_pauses") or 0 for s in pausable) if pausable else None,
        "average_pause_seconds": mean((s["avg_pause"] for s in pausable if s.get("avg_pause") is not None), digits=2),
        "average_answer_seconds": mean((s["duration"] for s in samples if s.get("duration")), digits=1),
        "repeated_words_per_answer": mean((s["repeats"] for s in samples if s.get("repeats") is not None), digits=1),
        "total_words": words_total,
    }


def speaking_report(facts: Facts) -> dict:
    samples = spoken_samples(facts)
    if len(samples) < config.MIN_VOICE_SAMPLES:
        return {
            "available": False,
            "spoken_answers": len(samples),
            "message": "No voice answers yet." if not samples
            else "Early data: complete a few more spoken answers for reliable speaking metrics.",
            "metrics": None,
            "not_tracked": NOT_TRACKED,
        }
    return {"available": True, "spoken_answers": len(samples), "message": None,
            "metrics": aggregate_samples(samples), "not_tracked": NOT_TRACKED}


# Requested by the spec but not stored by any earlier step, so deliberately not reported.
NOT_TRACKED = ["self_corrections", "incomplete_sentences", "weak_opening_statement", "weak_conclusion"]
