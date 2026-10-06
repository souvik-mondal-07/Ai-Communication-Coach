"""Interview analytics: modes, difficulty, follow-ups, domains, technical/communication dimensions."""

from __future__ import annotations

from collections import defaultdict

from app.services.analytics import config
from app.services.analytics.common import compare, mean, score_band, stdev
from app.services.analytics.facts import Facts, all_answers
from app.services.interview.topics import INTERVIEW_TYPE_LABELS
from app.services.personalization.performance_service import _INTERVIEW_ALIASES

# Interview topic ids -> practice category names (reuses the Step 16 mapping, plus
# "fundamentals", which exists in both vocabularies but was not aliased there).
DOMAIN_ALIASES = {**_INTERVIEW_ALIASES, "fundamentals": "Cybersecurity Fundamentals"}

MODE_LABELS = {**INTERVIEW_TYPE_LABELS, "pressure": "Pressure"}


def mode_breakdown(facts: Facts) -> list[dict]:
    """One row per interview mode that actually has data (never a placeholder row)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in facts.interviews + facts.pressure:
        groups[s["type"]].append(s)
    rows = []
    for mode, sessions in groups.items():
        overall = mean(s["overall"] for s in sessions)
        rows.append({
            "mode": mode,
            "label": MODE_LABELS.get(mode, mode.replace("_", " ").title()),
            "sessions": len(sessions),
            "overall_score": overall,
            "technical_score": mean(s["technical"] for s in sessions),
            "communication_score": mean(s["communication"] for s in sessions),
            "completion_rate": mean((s["completion"] for s in sessions), digits=2),
            "band": score_band(overall),
            "reliable": len(sessions) >= config.MIN_SESSIONS_FOR_SCORE,
        })
    rows.sort(key=lambda r: -(r["overall_score"] or 0))
    return rows


def difficulty_breakdown(facts: Facts) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in facts.interviews:
        if s.get("difficulty"):
            groups[s["difficulty"]].append(s)
    order = {"beginner": 0, "intermediate": 1, "advanced": 2}
    return sorted(
        ({"difficulty": d, "sessions": len(v), "overall_score": mean(s["overall"] for s in v),
          "technical_score": mean(s["technical"] for s in v),
          "reliable": len(v) >= config.MIN_SESSIONS_FOR_SCORE} for d, v in groups.items()),
        key=lambda r: order.get(r["difficulty"], 9),
    )


def technical_dimensions(answers: list[dict]) -> dict:
    """Mean of each stored technical rubric dimension (None when never scored)."""
    return {
        "accuracy": mean(a["accuracy"] for a in answers),
        "completeness": mean(a["completeness"] for a in answers),
        "depth": mean(a["depth"] for a in answers),
        "samples": len(answers),
    }


def follow_up_analytics(facts: Facts) -> dict:
    """
    Follow-up performance. `consistency` is a score-level proxy: 100 minus the mean
    absolute gap between a question's main-answer technical score and its follow-up
    scores (a big swing means the first answer was not backed by deeper knowledge).
    """
    answers = all_answers(facts.interviews + facts.pressure)
    follow_ups = [a for a in answers if a["is_follow_up"]]
    if len(follow_ups) < config.READINESS_MIN_SESSIONS["follow_up"]:
        return {"available": False, "follow_up_answers": len(follow_ups),
                "message": "Not enough follow-up answers yet."}
    gaps = [abs(a["technical"] - a["main_technical"]) for a in follow_ups
            if a["technical"] is not None and a["main_technical"] is not None]
    main_scores = [a["technical"] for a in answers if not a["is_follow_up"]]
    fu_tech = mean(a["technical"] for a in follow_ups)
    main_tech = mean(main_scores)
    return {
        "available": True,
        "follow_up_answers": len(follow_ups),
        "accuracy": mean(a["accuracy"] for a in follow_ups),
        "completeness": mean(a["completeness"] for a in follow_ups),
        "technical_depth": mean(a["depth"] for a in follow_ups),
        "technical_score": fu_tech,
        "main_answer_technical_score": main_tech,
        "difference_vs_main": None if fu_tech is None or main_tech is None else fu_tech - main_tech,
        "consistency": None if not gaps else max(0, round(100 - mean(gaps, digits=None))),
        "ability_to_go_deeper": None if fu_tech is None else score_band(fu_tech),
    }


def domain_breakdown(facts: Facts) -> dict:
    """
    Per cybersecurity domain, combining practice sessions and interview topic scores.
    Each source is weighted by the number of questions behind it. A domain with fewer
    than MIN_DOMAIN_QUESTIONS scored questions gets NO percentage.
    """
    acc: dict[str, dict] = defaultdict(lambda: {"w": 0.0, "ws": 0.0, "practice": 0, "interview": 0, "sessions": 0})
    for p in facts.practice:
        weight = p.get("questions_answered") or 0
        if not weight or p.get("score") is None:
            continue
        d = acc[p["category"]]
        d["w"] += weight; d["ws"] += weight * p["score"]; d["practice"] += weight; d["sessions"] += 1
    for s in facts.interviews:
        for ts in s["topic_scores"]:
            category = DOMAIN_ALIASES.get(ts.get("topic"))
            weight = ts.get("questions") or 0
            if not category or not weight or ts.get("average_score") is None:
                continue
            d = acc[category]
            d["w"] += weight; d["ws"] += weight * ts["average_score"]; d["interview"] += weight; d["sessions"] += 1

    rated, insufficient = [], []
    for category, d in acc.items():
        questions = d["practice"] + d["interview"]
        row = {"domain": category, "questions": questions, "sessions": d["sessions"],
               "practice_questions": d["practice"], "interview_questions": d["interview"]}
        if questions >= config.MIN_DOMAIN_QUESTIONS:
            score = round(d["ws"] / d["w"])
            rated.append({**row, "score": score, "band": score_band(score)})
        else:
            insufficient.append({**row, "score": None, "band": None})
    rated.sort(key=lambda r: -r["score"])
    insufficient.sort(key=lambda r: r["domain"])
    return {
        "domains": rated,
        "insufficient_data": insufficient,
        "strongest": [r for r in rated if r["band"] == "strong"][:3],
        "weakest": [r for r in reversed(rated) if r["band"] == "weak"][:3],
    }


def interview_overview(facts: Facts) -> dict:
    sessions = facts.interviews
    answers = all_answers(sessions)
    overall = [s["overall"] for s in sessions]
    return {
        "sessions": len(sessions),
        "overall_score": mean(overall),
        "technical_score": mean(s["technical"] for s in sessions),
        "communication_score": mean(s["communication"] for s in sessions),
        "average_answer_quality": mean(a["technical"] for a in answers),
        "answered_questions": len(answers),
        "question_completion_rate": mean((s["completion"] for s in sessions), digits=2),
        "score_spread": None if stdev(overall) is None else round(stdev(overall), 1),
    }


def interview_report(facts: Facts) -> dict:
    sessions = facts.interviews
    answers = all_answers(sessions)
    return {
        "overview": interview_overview(facts),
        "modes": mode_breakdown(facts),
        "difficulty": difficulty_breakdown(facts),
        "technical_dimensions": technical_dimensions(answers),
        "follow_ups": follow_up_analytics(facts),
    }


def window_compare(previous: Facts | None, current: Facts) -> dict:
    """Previous-vs-current for the headline interview metrics (None => all-time, no comparison)."""
    if previous is None:
        return {"available": False, "reason": "Comparison needs a bounded date range."}
    return {
        "available": True,
        "technical": compare([s["technical"] for s in previous.interviews], [s["technical"] for s in current.interviews]),
        "communication": compare([s["communication"] for s in previous.interviews], [s["communication"] for s in current.interviews]),
        "overall": compare([s["overall"] for s in previous.interviews], [s["overall"] for s in current.interviews]),
        "confidence": compare([s["confidence"] for s in previous.communication], [s["confidence"] for s in current.communication]),
    }
