"""Normal vs pressure performance. Performance-oriented language only -- no psychological claims."""

from __future__ import annotations

from app.services.analytics import config
from app.services.analytics.common import mean
from app.services.analytics.facts import Facts, spoken_samples
from app.services.analytics.speaking_analytics import aggregate_samples


def _side(sessions: list[dict], spoken: list[dict]) -> dict:
    return {
        "sessions": len(sessions),
        "technical": mean(s["technical"] for s in sessions),
        "communication": mean(s["communication"] for s in sessions),
        # Interviews and pressure sessions store no confidence score, so it is not compared.
        "confidence": None,
        "words_per_minute": aggregate_samples(spoken)["words_per_minute"] if spoken else None,
        "filler_per_100_words": aggregate_samples(spoken)["filler_per_100_words"] if spoken else None,
    }


def pressure_report(facts: Facts) -> dict:
    normal, pressure = facts.interviews, facts.pressure
    if not pressure:
        return {"available": False, "message": "No pressure sessions yet.", "normal": None, "pressure": None,
                "differences": {}, "insights": [], "pressure_handling_score": None}
    spoken = spoken_samples(facts)
    n_spoken = [s for s in spoken if not s["pressure"]]
    p_spoken = [s for s in spoken if s["pressure"]]
    n_side, p_side = _side(normal, n_spoken), _side(pressure, p_spoken)
    handling = mean(s["pressure_handling"] for s in pressure)

    base = {"available": True, "normal": n_side, "pressure": p_side,
            "pressure_handling_score": handling, "response_control_score": mean(s["response_control"] for s in pressure)}
    if not normal:
        return {**base, "comparison_available": False, "differences": {}, "insights": [],
                "message": "No normal interviews in this range to compare against."}
    if len(normal) < config.MIN_COMPARE_SAMPLES or len(pressure) < config.MIN_COMPARE_SAMPLES:
        return {**base, "comparison_available": False, "differences": {}, "insights": [],
                "message": "Early data: at least two normal and two pressure sessions are needed for a reliable comparison."}

    diffs = {}
    for key in ("technical", "communication"):
        if n_side[key] is not None and p_side[key] is not None:
            diffs[key] = p_side[key] - n_side[key]
    notable = config.PRESSURE_NOTABLE_DELTA
    tech, comm = diffs.get("technical"), diffs.get("communication")
    insights: list[str] = []
    if tech is not None and comm is not None:
        if abs(tech) < notable and comm <= -notable:
            insights.append("Your technical performance stays stable under pressure, but communication drops noticeably.")
        elif tech <= -notable and abs(comm) < notable:
            insights.append("Your communication holds up under pressure, but technical answers become weaker.")
        elif tech <= -notable and comm <= -notable:
            insights.append("Both technical and communication scores are lower in pressure sessions.")
        elif abs(tech) < notable and abs(comm) < notable:
            insights.append("Your scores in pressure sessions are close to your normal interviews.")
        elif tech >= notable or comm >= notable:
            insights.append("You score at least as well under pressure as in normal interviews.")
    n_f, p_f = n_side["filler_per_100_words"], p_side["filler_per_100_words"]
    if n_f is not None and p_f is not None and p_f - n_f >= 1.5:
        insights.append("You use more filler words in pressure sessions than in normal interviews.")
    n_w, p_w = n_side["words_per_minute"], p_side["words_per_minute"]
    if n_w and p_w and abs(p_w - n_w) / n_w >= 0.15:
        insights.append("Your speaking pace %s under pressure." % ("increases" if p_w > n_w else "slows"))
    return {**base, "comparison_available": True, "message": None, "differences": diffs, "insights": insights}
