"""
Interview Readiness Score.

    Interview Readiness = Technical x 0.35 + Communication x 0.25 + Confidence x 0.15
                        + Consistency x 0.10 + Follow-up x 0.10 + Pressure x 0.05

(weights live in `config.READINESS_WEIGHTS`). Components:

* technical     - mean technical score of completed interviews
* communication - mean communication score of completed interviews
* confidence    - mean confidence score of communication sessions
                  (the only place a confidence score is recorded)
* consistency   - 100 - 2.5 x stdev of interview overall scores (steady = high)
* follow_up     - mean technical score on follow-up answers
* pressure      - mean pressure-handling score of pressure sessions

A component is used only with enough data (`READINESS_MIN_SESSIONS`). Technical and
communication are mandatory: without both the result is "Not enough data" and no
number is produced. Otherwise the weights of the available components are
re-normalised to 1.0 and `coverage` reports what share of the full formula was
actually backed by data, so a score built from two components is never mistaken for
a complete one.
"""

from __future__ import annotations

from app.services.analytics import config
from app.services.analytics.common import mean, stdev
from app.services.analytics.facts import Facts, all_answers

COMPONENT_LABELS = {
    "technical": "Technical", "communication": "Communication", "confidence": "Confidence",
    "consistency": "Consistency", "follow_up": "Follow-up", "pressure": "Pressure",
}
NOT_ENOUGH = "Not enough data"


def _components(facts: Facts) -> dict[str, tuple[float | None, int]]:
    qa = facts.interviews
    follow = [a["technical"] for a in all_answers(qa + facts.pressure) if a["is_follow_up"] and a["technical"] is not None]
    overall = [s["overall"] for s in qa if s["overall"] is not None]
    spread = stdev(overall)
    return {
        "technical": (mean(s["technical"] for s in qa), len(qa)),
        "communication": (mean(s["communication"] for s in qa), len(qa)),
        "confidence": (mean(c["confidence"] for c in facts.communication), len(facts.communication)),
        "consistency": (None if spread is None else max(0, 100 - config.CONSISTENCY_PENALTY * spread), len(overall)),
        "follow_up": (mean(follow), len(follow)),
        "pressure": (mean(s["pressure_handling"] for s in facts.pressure), len(facts.pressure)),
    }


def readiness_report(facts: Facts) -> dict:
    comps = _components(facts)
    used, missing = {}, []
    for key, weight in config.READINESS_WEIGHTS.items():
        value, samples = comps[key]
        if value is not None and samples >= config.READINESS_MIN_SESSIONS[key]:
            used[key] = {"label": COMPONENT_LABELS[key], "score": round(value), "samples": samples, "weight": weight}
        else:
            missing.append({"key": key, "label": COMPONENT_LABELS[key], "samples": samples,
                            "needed": config.READINESS_MIN_SESSIONS[key]})

    formula = {k: w for k, w in config.READINESS_WEIGHTS.items()}
    base = {"formula": formula, "components": list(used.values()), "missing_components": missing}
    if not all(k in used for k in config.READINESS_REQUIRED):
        return {**base, "available": False, "score": None, "band": None, "coverage": 0.0, "message": NOT_ENOUGH,
                "detail": "Complete at least %d interviews to unlock your readiness score." % config.READINESS_MIN_SESSIONS["technical"]}
    total_weight = sum(c["weight"] for c in used.values())
    score = round(sum(c["score"] * c["weight"] for c in used.values()) / total_weight)
    for c in used.values():
        c["effective_weight"] = round(c["weight"] / total_weight, 3)
    band = next(label for floor, label in config.READINESS_BANDS if score >= floor)
    return {**base, "available": True, "score": score, "band": band, "coverage": round(total_weight, 2),
            "message": None, "detail": None if not missing else "Some components lack data and were left out; the score will sharpen as you practise."}
