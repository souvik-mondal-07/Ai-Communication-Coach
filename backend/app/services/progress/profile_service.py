"""
Personal AI Profile service.

Builds the deterministic long-term profile (spec section 5) from the other
progress services' output, optionally layers on a natural-language AI
summary (spec section 13, reusing the existing `AIService` -- never a second
Gemini client), and exposes a small, compact "mentor context" object (spec
section 14/35/2's "Personal Mentor Context") that other features (the mentor
chat) can use to personalize themselves without ever sending the whole
database to Gemini.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from bson import ObjectId
from pydantic import BaseModel, Field
from pymongo.database import Database

from app.db.collections import Collections
from app.services.ai.ai_service import AIService, AIServiceError, ai_service
from app.services.interview.structured_ai import StructuredOutputError, generate_validated
from app.services.progress.prompts import PROFILE_SUMMARY_SYSTEM_PROMPT, build_profile_summary_prompt
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_FOCUS_ITEMS = 5


class _ProfileSummaryOut(BaseModel):
    summary: str = Field(default="", max_length=2000)
    strengths: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    suggested_next_focus: list[str] = Field(default_factory=list)


def build_technical_profile(skill_breakdown: list[dict], practice_strengths: list[str], interview_strengths: list[str]) -> dict:
    strong = sorted(set(practice_strengths) | set(interview_strengths))
    weak = sorted({row["category"] for row in skill_breakdown if row["status"] == "weak"})
    developing = sorted(
        {row["category"] for row in skill_breakdown if row["status"] == "developing"} - set(strong) - set(weak)
    )
    return {"strong_areas": strong, "developing_areas": developing, "weak_areas": weak}


def build_communication_profile(comm_strengths: list[str], comm_weaknesses: list[dict]) -> dict:
    return {
        "strengths": comm_strengths,
        "improvement_areas": sorted({w["skill"] for w in comm_weaknesses}),
    }


def build_interview_profile(interview_strengths: list[str], interview_weaknesses: list[dict]) -> dict:
    return {
        "strengths": interview_strengths,
        "improvement_areas": sorted({w["area"] for w in interview_weaknesses}),
    }


def build_pressure_profile(pressure_summary: dict | None, pressure_weaknesses: list[dict]) -> dict:
    indicators = list((pressure_summary or {}).get("recent_indicators") or [])
    return {
        "observed_indicators": indicators,
        "improvement_areas": sorted({w["area"] for w in pressure_weaknesses}),
    }


def build_learning_preferences(db: Database, *, user_id: str) -> dict:
    """Preferred difficulty = the most commonly attempted difficulty in completed practice sessions."""
    docs = db[Collections.PRACTICE_SESSIONS].find(
        {"user_id": ObjectId(user_id), "status": "completed"}, {"difficulty": 1}
    )
    counts = Counter(d.get("difficulty") for d in docs if d.get("difficulty"))
    preferred = counts.most_common(1)[0][0] if counts else "intermediate"
    return {"preferred_difficulty": preferred}


def build_recent_focus(recent_activity: list[dict]) -> list[str]:
    """Distinct categories/types from the most recent activity, most-recent-first."""
    seen: list[str] = []
    for item in recent_activity:
        label = item.get("category") or item.get("type")
        if label and label not in seen:
            seen.append(label)
        if len(seen) >= MAX_FOCUS_ITEMS:
            break
    return seen


def build_recommended_focus(recommendations: list[dict]) -> list[str]:
    """Top-priority active recommendation areas, deduplicated."""
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    ordered = sorted(recommendations, key=lambda r: priority_rank.get(r.get("priority"), 3))
    seen: list[str] = []
    for rec in ordered:
        if rec["area"] not in seen:
            seen.append(rec["area"])
        if len(seen) >= MAX_FOCUS_ITEMS:
            break
    return seen


async def generate_ai_summary(ai_service_: AIService, deterministic_profile: dict) -> dict | None:
    """
    Natural-language interpretation of the deterministic profile. Returns
    None (never raises) if the AI provider is unavailable or never returns
    valid output -- the deterministic profile is always usable on its own,
    consistent with the rest of this feature's "AI is optional interpretation,
    not the source of truth" stance.
    """
    try:
        result = await generate_validated(
            ai_service_,
            user_prompt=build_profile_summary_prompt(deterministic_profile),
            system_prompt=PROFILE_SUMMARY_SYSTEM_PROMPT,
            model=_ProfileSummaryOut,
        )
    except (AIServiceError, StructuredOutputError) as exc:
        logger.warning("Profile AI summary unavailable: %s", type(exc).__name__)
        return None
    return result.model_dump()


def build_mentor_context(profile_doc: dict) -> dict:
    """
    Compact context object for the mentor chat (spec section 35) -- never
    the full profile or any raw session history.
    """
    technical = profile_doc.get("technical_profile", {})
    strong = technical.get("strong_areas", [])
    weak = technical.get("weak_areas", [])
    if weak:
        technical_level = "developing"
    elif strong:
        technical_level = "proficient"
    else:
        technical_level = "beginner"

    return {
        "technical_level": technical_level,
        "strong_areas": strong[:MAX_FOCUS_ITEMS],
        "weak_areas": weak[:MAX_FOCUS_ITEMS],
        "recent_focus": profile_doc.get("recent_focus", [])[:MAX_FOCUS_ITEMS],
        "recommended_focus": profile_doc.get("recommended_focus", [])[:MAX_FOCUS_ITEMS],
    }


def upsert_profile(db: Database, *, user_id: str, profile: dict) -> dict:
    uid = ObjectId(user_id)
    now = datetime.now(timezone.utc)
    doc = {**profile, "user_id": uid, "updated_at": now}
    db[Collections.PERSONAL_PROFILES].update_one({"user_id": uid}, {"$set": doc}, upsert=True)
    doc["user_id"] = str(uid)
    return doc


def get_profile(db: Database, *, user_id: str) -> dict | None:
    doc = db[Collections.PERSONAL_PROFILES].find_one({"user_id": ObjectId(user_id)})
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    doc["user_id"] = str(doc["user_id"])
    return doc
