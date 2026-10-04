"""
Explainable "what should I learn next" + adaptive difficulty.

Pure functions over (profile, preferences, topic performance, strengths,
weaknesses, existing Step 11 non-practice weaknesses) plus the topic catalogue
already stored in `cybersecurity_topics`. Every recommendation carries
`reasons` built from observable facts and a `basis` that says honestly whether
it came from `performance` or only from the user's `profile`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo.database import Database

from app.db.collections import Collections
from app.services.personalization.performance_service import topic_key
from app.services.progress.aggregation_service import MIN_ATTEMPTS

LEVELS = ("beginner", "intermediate", "advanced")
MAX_RECOMMENDATIONS = 5

# Profile interest / learning-goal -> practice category (the canonical topic names).
INTEREST_CATEGORIES = {
    "web_security": ["Web Security"],
    "penetration_testing": ["Penetration Testing"],
    "red_teaming": ["Penetration Testing"],
    "soc": ["SOC"],
    "siem": ["SIEM"],
    "digital_forensics": ["Digital Forensics"],
    "incident_response": ["Incident Response"],
    "threat_intelligence": ["Threat Intelligence"],
    "network_security": ["Networking"],
    "cloud_security": ["Cloud Security"],
    "malware_analysis": ["Malware Basics"],
    "active_directory": ["Active Directory"],
    "cryptography": ["Cryptography"],
    "security_research": ["Cybersecurity Fundamentals"],
}
GOAL_CATEGORIES = {
    "improve_penetration_testing": ["Penetration Testing"],
    "learn_web_security": ["Web Security"],
    "improve_networking": ["Networking"],
    "learn_soc_siem": ["SOC", "SIEM"],
    "improve_linux": ["Linux"],
    "improve_active_directory": ["Active Directory"],
}
# Free-text career goal keywords -> categories (light, deterministic matching).
CAREER_KEYWORDS = (
    (("soc", "blue team", "analyst"), ["SOC", "SIEM", "Incident Response"]),
    (("red team", "pentest", "penetration", "offensive"), ["Penetration Testing", "Web Security"]),
    (("forensic",), ["Digital Forensics"]),
    (("cloud",), ["Cloud Security"]),
    (("web", "appsec", "application security"), ["Web Security"]),
    (("network",), ["Networking"]),
)

_COMM_TIPS = {
    "Clarity": "Practice 60-second structured answers (point, reason, example).",
    "Confidence": "Practice answering aloud with a clear opening line and a firm close.",
    "Relevance": "Practice restating the question before answering to stay on topic.",
    "Professionalism": "Practice workplace scenarios that call for formal, concise wording.",
}

_ROUTES = {
    "interview": "/interview",
    "communication": "/communication",
    "pressure": "/pressure-training",
    "ctf": "/ctf",
    "practice": "/cybersecurity",
}


def _step(level: str, delta: int) -> str:
    return LEVELS[max(0, min(len(LEVELS) - 1, LEVELS.index(level) + delta))]


def choose_difficulty(*, preference: str, experience_level: str | None, row: dict | None) -> tuple[str, str]:
    """
    Returns (difficulty, reason). A fixed preference is always honoured. For
    `adaptive` the base is the stated experience level and the topic's
    evidence moves it by at most ONE level -- never a jump from a single result.
    """
    if preference in LEVELS:
        return preference, f"You chose {preference} difficulty."
    base = experience_level if experience_level in LEVELS else "beginner"
    if not row or row["attempts"] < MIN_ATTEMPTS or row["average_score"] is None:
        return base, "Based on your experience level (not enough practice data on this topic yet)."
    avg, trend = row["average_score"], row["trend"]
    if avg < 60 and trend != "improving":
        return _step(base, -1), "Repeated low scores here, so we reinforce fundamentals first."
    if avg >= 80 and trend != "declining":
        return _step(base, +1), "Consistently strong results here, so difficulty steps up slightly."
    return base, "Your results on this topic are steady at your current level."


def _interest_categories(profile: dict) -> dict[str, str]:
    """category -> why it matches the profile (first match wins)."""
    matches: dict[str, str] = {}
    for goal in profile.get("learning_goals", []):
        for cat in GOAL_CATEGORIES.get(goal, []):
            matches.setdefault(cat, "It matches one of your learning goals.")
    career = (profile.get("career_goal") or "").lower()
    for keywords, cats in CAREER_KEYWORDS:
        if any(k in career for k in keywords):
            for cat in cats:
                matches.setdefault(cat, "It matches your career goal.")
    for interest in profile.get("cybersecurity_interests", []):
        for cat in INTEREST_CATEGORIES.get(interest, []):
            matches.setdefault(cat, "It matches your cybersecurity interests.")
    return matches


def _pick_topic_slug(db: Database, *, user_id: str, category: str, difficulty: str) -> dict | None:
    """The catalogue topic to open next: unpracticed first, nearest to the target difficulty."""
    topics = list(
        db[Collections.CYBERSECURITY_TOPICS].find(
            {"category": category, "practice_enabled": True}, {"slug": 1, "title": 1, "difficulty": 1}
        )
    )
    if not topics:
        return None
    done = {
        d["topic_slug"]
        for d in db[Collections.PRACTICE_SESSIONS].find(
            {"user_id": ObjectId(user_id), "status": "completed", "category": category}, {"topic_slug": 1}
        )
    }
    target = LEVELS.index(difficulty)

    def rank(t: dict) -> tuple:
        level = LEVELS.index(t["difficulty"]) if t.get("difficulty") in LEVELS else target
        return (t["slug"] in done, abs(level - target), level, t["title"])

    best = min(topics, key=rank)
    return {"slug": best["slug"], "title": best["title"]}


def _practice_rec(db, *, user_id, category, row, difficulty, difficulty_reason, reasons, basis, priority, score) -> dict:
    pick = _pick_topic_slug(db, user_id=user_id, category=category, difficulty=difficulty)
    return {
        "type": "practice",
        "topic": category,
        "topic_key": topic_key(category),
        "topic_slug": pick["slug"] if pick else None,
        "title": f"Practice {pick['title']}" if pick else f"Practice {category}",
        "difficulty": difficulty,
        "difficulty_reason": difficulty_reason,
        "reasons": reasons,
        "basis": basis,
        "priority": priority,
        "route": (
            f"/cybersecurity/{pick['slug']}?difficulty={difficulty}" if pick else _ROUTES["practice"]
        ),
        "_score": score,
    }


def build_recommendations(
    db: Database,
    *,
    user_id: str,
    profile: dict,
    preferences: dict,
    rows: list[dict],
    weaknesses: list[dict],
    other_weaknesses: list[dict],
    has_interview_data: bool,
    now: datetime | None = None,
) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    by_topic = {r["topic"]: r for r in rows}
    fits = _interest_categories(profile)
    pref = preferences.get("difficulty", "adaptive")
    exp = profile.get("experience_level")
    recs: list[dict] = []
    covered: set[str] = set()

    # 1) Evidence-based: weaknesses (performance).
    sev_weight = {"high": 30, "medium": 20, "low": 10}
    for w in weaknesses:
        row = by_topic[w["topic"]]
        diff, diff_reason = choose_difficulty(preference=pref, experience_level=exp, row=row)
        score = sev_weight[w["severity"]] + (8 if w["topic"] in fits else 0)
        last = row.get("last_practiced")
        if last and now - last >= timedelta(days=7):
            score += 3  # topic freshness: it has gone stale
        reasons = [f"Your recent results show this is an area to strengthen: {f}." for f in w["evidence"][:2]]
        if w["topic"] in fits:
            reasons.append(fits[w["topic"]])
        recs.append(_practice_rec(db, user_id=user_id, category=w["topic"], row=row, difficulty=diff,
                                  difficulty_reason=diff_reason, reasons=reasons, basis="performance",
                                  priority=w["severity"], score=score))
        covered.add(w["topic"])

    # 2) Other modules' weaknesses already detected by Step 11 (interview / communication / pressure).
    for w in other_weaknesses:
        if w["source"] == "cybersecurity_practice":
            continue
        ev = w["evidence"]
        reason = f"Average {ev['average_score']}/100 over {ev['attempts']} recorded attempts."
        if w["source"] == "communication":
            title = f"Improve {w['skill'].lower()} in your answers"
            reasons = [reason, _COMM_TIPS.get(w["skill"], "Practice a short communication scenario.")]
            kind = "communication"
        elif w["source"] == "interview":
            focus = preferences.get("interview_focus") or []
            title = f"Practice interview questions on {w['area']}"
            reasons = [reason] + ([f"Your interview focus includes {focus[0].replace('_', ' ')}."] if focus else [])
            kind = "interview"
        else:
            title = "Practice answering under pressure"
            reasons = [reason]
            kind = "pressure"
        recs.append({
            "type": kind, "topic": w["area"], "topic_key": topic_key(w["area"]), "topic_slug": None,
            "title": title, "difficulty": None, "difficulty_reason": None, "reasons": reasons,
            "basis": "performance", "priority": w["severity"], "route": _ROUTES[kind],
            "_score": sev_weight[w["severity"]] - 2,
        })

    # 3) Profile-based: topics the user cares about but has too little data on.
    for category, why in fits.items():
        if category in covered:
            continue
        row = by_topic.get(category)
        if row and row["attempts"] >= MIN_ATTEMPTS:
            continue  # enough data and not weak: nothing to push
        diff, diff_reason = choose_difficulty(preference=pref, experience_level=exp, row=row)
        reasons = [why, "Not enough practice data yet to judge performance here; this is based on your profile."]
        recs.append(_practice_rec(db, user_id=user_id, category=category, row=row, difficulty=diff,
                                  difficulty_reason=diff_reason, reasons=reasons, basis="profile",
                                  priority="low", score=5 + (1 if row is None else 0)))

    # 4) Interview preparation from profile when nothing is recorded yet.
    focus = preferences.get("interview_focus") or []
    if (focus or "prepare_for_interviews" in profile.get("learning_goals", [])) and not has_interview_data:
        label = focus[0].replace("_", " ") if focus else "cybersecurity"
        recs.append({
            "type": "interview", "topic": label, "topic_key": topic_key(label), "topic_slug": None,
            "title": f"Try a {label} mock interview", "difficulty": None, "difficulty_reason": None,
            "reasons": ["It matches your interview focus / learning goals.",
                        "No interview results recorded yet; this is based on your profile."],
            "basis": "profile", "priority": "low", "route": _ROUTES["interview"], "_score": 4,
        })

    recs.sort(key=lambda r: -r["_score"])
    for r in recs:
        r.pop("_score")
    return recs[:MAX_RECOMMENDATIONS]
