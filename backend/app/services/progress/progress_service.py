"""
Progress service.

Thin facade over the other `app.services.progress.*` modules -- the single
entry point `app.api.routes.progress` talks to, matching the project's
existing per-feature-service pattern:

    progress.py (route) -> ProgressService -> aggregation/weakness/
                            recommendation/profile services -> raw session
                            collections (+ AIService for the optional
                            profile summary -- never a second Gemini client)

Deterministic aggregation (skills, weaknesses, recommendations) is cheap
(plain Mongo aggregation pipelines), so every read here refreshes the cached
`learning_progress` / `user_weaknesses` / `recommendations` collections
first via `_run_deterministic()` -- the dashboard is never looking at stale
data just because nobody called `POST /progress/recalculate` yet. The one
genuinely expensive step -- the AI-generated profile narrative -- only ever
runs inside `recalculate()`, never on a plain GET (spec section 29: "Do not
run expensive Gemini analysis every time the dashboard loads").
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database

from app.db.collections import Collections
from app.services.ai.ai_service import AIService, ai_service
from app.services.progress import aggregation_service as agg
from app.services.progress import profile_service as profile_svc
from app.services.progress import recommendation_service as rec_svc
from app.services.progress import weakness_service as weak_svc
from app.services.progress.recommendation_service import (
    RecommendationForbiddenError,
    RecommendationNotFoundError,
)

TREND_DIMENSIONS = ("technical", "communication", "interview", "pressure", "overall")


def _upsert_learning_progress(db: Database, *, user_id: str, skill_breakdown: list[dict]) -> None:
    uid = ObjectId(user_id)
    now = datetime.now(timezone.utc)
    collection = db[Collections.LEARNING_PROGRESS]

    current_skills = {row["skill"] for row in skill_breakdown}
    for existing in collection.find({"user_id": uid}, {"skill": 1}):
        if existing["skill"] not in current_skills:
            collection.delete_one({"_id": existing["_id"]})

    for row in skill_breakdown:
        collection.update_one(
            {"user_id": uid, "skill": row["skill"]},
            {
                "$set": {
                    "user_id": uid,
                    "skill": row["skill"],
                    "category": row["category"],
                    "level": row["level"],
                    "score": row["average_score"],
                    "confidence": row["confidence"],
                    "attempts": row["attempts"],
                    "successful_attempts": row["successful_attempts"],
                    "last_practiced_at": row["last_practiced_at"],
                    "updated_at": now,
                }
            },
            upsert=True,
        )


class ProgressService:
    """Aggregation, weakness/recommendation, and personal-profile orchestration."""

    def __init__(self, ai_service_: AIService = ai_service) -> None:
        self._ai_service = ai_service_

    def ensure_indexes(self, db: Database) -> None:
        """Create required indexes. Idempotent -- safe to call on every startup."""
        db[Collections.LEARNING_PROGRESS].create_index([("user_id", 1), ("skill", 1)], unique=True)
        db[Collections.USER_WEAKNESSES].create_index([("user_id", 1), ("area", 1), ("skill", 1), ("source", 1)])
        db[Collections.RECOMMENDATIONS].create_index([("user_id", 1), ("completed", 1)])
        db[Collections.RECOMMENDATIONS].create_index([("user_id", 1), ("created_at", -1)])
        db[Collections.PERSONAL_PROFILES].create_index("user_id", unique=True)

    # --- Shared deterministic recompute -----------------------------------------

    def _run_deterministic(self, db: Database, *, user_id: str) -> dict:
        """
        Refresh `learning_progress` / `user_weaknesses` / `recommendations`
        from current session history and return every intermediate value the
        callers (overview, skills, profile/recalculate) need -- computed
        once, not once per collection.
        """
        skill_breakdown = agg.get_practice_skill_breakdown(db, user_id=user_id)
        ctf_breakdown = agg.get_ctf_breakdown(db, user_id=user_id)
        comm_summary = agg.get_communication_summary(db, user_id=user_id)
        interview_summary = agg.get_interview_summary(db, user_id=user_id)
        pressure_summary = agg.get_pressure_summary(db, user_id=user_id)

        _upsert_learning_progress(db, user_id=user_id, skill_breakdown=skill_breakdown)

        practice_weaknesses = weak_svc.detect_practice_weaknesses(skill_breakdown)
        interview_weaknesses = weak_svc.detect_interview_weaknesses(interview_summary)
        communication_weaknesses = weak_svc.detect_communication_weaknesses(comm_summary)
        pressure_weaknesses = weak_svc.detect_pressure_weaknesses(pressure_summary)
        all_weaknesses = [
            *practice_weaknesses,
            *interview_weaknesses,
            *communication_weaknesses,
            *pressure_weaknesses,
        ]
        weak_svc.upsert_weaknesses(db, user_id=user_id, weaknesses=all_weaknesses)

        new_recommendations = rec_svc.build_recommendations(all_weaknesses, ctf_breakdown)
        rec_svc.upsert_recommendations(db, user_id=user_id, recommendations=new_recommendations)
        active_recommendations = rec_svc.list_recommendations(db, user_id=user_id, active_only=True)

        recent_activity = agg.get_recent_activity(db, user_id=user_id, limit=15)

        return {
            "skill_breakdown": skill_breakdown,
            "ctf_breakdown": ctf_breakdown,
            "comm_summary": comm_summary,
            "interview_summary": interview_summary,
            "pressure_summary": pressure_summary,
            "practice_weaknesses": practice_weaknesses,
            "interview_weaknesses": interview_weaknesses,
            "communication_weaknesses": communication_weaknesses,
            "pressure_weaknesses": pressure_weaknesses,
            "all_weaknesses": all_weaknesses,
            "active_recommendations": active_recommendations,
            "recent_activity": recent_activity,
        }

    # --- Reads -----------------------------------------------------------------

    def get_overview(self, db: Database, *, user_id: str) -> dict:
        counts = agg.get_overview_counts(db, user_id=user_id)
        state = self._run_deterministic(db, user_id=user_id)
        skill_breakdown = state["skill_breakdown"]

        strengths = sorted(
            set(weak_svc.detect_practice_strengths(skill_breakdown))
            | set(weak_svc.detect_interview_strengths(state["interview_summary"]))
        )
        has_any_activity = any(v["total"] > 0 for v in counts.values())

        return {
            "session_counts": counts,
            "has_activity": has_any_activity,
            "cybersecurity_performance": {
                "categories_practiced": len(skill_breakdown),
                "average_score": (
                    round(sum(r["average_score"] for r in skill_breakdown) / len(skill_breakdown))
                    if skill_breakdown
                    else None
                ),
            },
            "communication_performance": state["comm_summary"],
            "interview_performance": state["interview_summary"],
            "pressure_performance": state["pressure_summary"],
            "recent_activity": state["recent_activity"][:8],
            "strengths": strengths,
            "weaknesses": weak_svc.list_weaknesses(db, user_id=user_id),
            "recommendations": state["active_recommendations"][:5],
        }

    def get_skills(self, db: Database, *, user_id: str) -> dict:
        return {
            "cybersecurity_skills": agg.get_practice_skill_breakdown(db, user_id=user_id),
            "ctf_activity": agg.get_ctf_breakdown(db, user_id=user_id),
        }

    def get_trends(self, db: Database, *, user_id: str, period: str) -> dict:
        dimensions = {
            dimension: agg.get_trend_series(db, user_id=user_id, dimension=dimension, period=period)
            for dimension in TREND_DIMENSIONS
        }
        return {"period": period, "dimensions": dimensions}

    def get_weaknesses(self, db: Database, *, user_id: str) -> list[dict]:
        self._run_deterministic(db, user_id=user_id)
        return weak_svc.list_weaknesses(db, user_id=user_id)

    def get_recommendations(self, db: Database, *, user_id: str, active_only: bool = True) -> list[dict]:
        self._run_deterministic(db, user_id=user_id)
        return rec_svc.list_recommendations(db, user_id=user_id, active_only=active_only)

    def complete_recommendation(self, db: Database, *, user_id: str, recommendation_id: str) -> dict:
        return rec_svc.complete_recommendation(db, user_id=user_id, recommendation_id=recommendation_id)

    def get_activity(self, db: Database, *, user_id: str, limit: int = 15) -> list[dict]:
        return agg.get_recent_activity(db, user_id=user_id, limit=limit)

    def get_profile(self, db: Database, *, user_id: str) -> dict:
        profile = profile_svc.get_profile(db, user_id=user_id)
        if profile is not None:
            return profile
        # No recalculation has ever run for this user yet -- an empty,
        # well-shaped profile rather than a 404, so the UI can show its
        # empty state (spec section 21) instead of handling a special case.
        return {
            "user_id": user_id,
            "technical_profile": {"strong_areas": [], "developing_areas": [], "weak_areas": []},
            "communication_profile": {"strengths": [], "improvement_areas": []},
            "interview_profile": {"strengths": [], "improvement_areas": []},
            "pressure_profile": {"observed_indicators": [], "improvement_areas": []},
            "learning_preferences": {"preferred_difficulty": "intermediate"},
            "recent_focus": [],
            "recommended_focus": [],
            "ai_summary": None,
            "updated_at": None,
        }

    def get_mentor_context(self, db: Database, *, user_id: str) -> dict | None:
        """
        Compact context for the mentor chat (spec section 14/35).

        Returns None when there is nothing to personalize with (a learner
        with no computed profile yet) or when the lookup fails, so callers
        can simply skip personalization. Never raises.
        """
        try:
            profile = profile_svc.get_profile(db, user_id=user_id)
            if profile is None:
                return None
            context = profile_svc.build_mentor_context(profile)
        except Exception:  # noqa: BLE001 - mentor chat must never break because of this
            return None
        if not (
            context["strong_areas"]
            or context["weak_areas"]
            or context["recent_focus"]
            or context["recommended_focus"]
        ):
            return None
        return context

    # --- Write: recalculation ---------------------------------------------------

    async def recalculate(self, db: Database, *, user_id: str) -> dict:
        """
        Rebuild every derived collection for this user from current session
        history, including the optional AI-generated profile summary. Only
        ever touches `user_id`'s own data.
        """
        state = self._run_deterministic(db, user_id=user_id)

        technical_profile = profile_svc.build_technical_profile(
            state["skill_breakdown"],
            weak_svc.detect_practice_strengths(state["skill_breakdown"]),
            weak_svc.detect_interview_strengths(state["interview_summary"]),
        )
        communication_profile = profile_svc.build_communication_profile(
            weak_svc.detect_communication_strengths(state["comm_summary"]), state["communication_weaknesses"]
        )
        interview_profile = profile_svc.build_interview_profile(
            weak_svc.detect_interview_strengths(state["interview_summary"]), state["interview_weaknesses"]
        )
        pressure_profile = profile_svc.build_pressure_profile(state["pressure_summary"], state["pressure_weaknesses"])
        learning_preferences = profile_svc.build_learning_preferences(db, user_id=user_id)
        recent_focus = profile_svc.build_recent_focus(state["recent_activity"])
        recommended_focus = profile_svc.build_recommended_focus(state["active_recommendations"])

        deterministic_profile = {
            "technical_profile": technical_profile,
            "communication_profile": communication_profile,
            "interview_profile": interview_profile,
            "pressure_profile": pressure_profile,
            "recent_focus": recent_focus,
            "recommended_focus": recommended_focus,
            "active_recommendations": [
                {"area": r["area"], "reason": r["reason"], "priority": r["priority"]}
                for r in state["active_recommendations"]
            ],
        }
        ai_summary = await profile_svc.generate_ai_summary(self._ai_service, deterministic_profile)

        profile = {
            "technical_profile": technical_profile,
            "communication_profile": communication_profile,
            "interview_profile": interview_profile,
            "pressure_profile": pressure_profile,
            "learning_preferences": learning_preferences,
            "recent_focus": recent_focus,
            "recommended_focus": recommended_focus,
            "ai_summary": ai_summary,
        }
        profile_svc.upsert_profile(db, user_id=user_id, profile=profile)

        return {
            "skills_recalculated": len(state["skill_breakdown"]),
            "weaknesses_detected": len(state["all_weaknesses"]),
            "recommendations_active": len(state["active_recommendations"]),
            "ai_summary_generated": ai_summary is not None,
            "profile_updated": True,
        }


# Module-level singleton, matching the project's existing pattern.
progress_service = ProgressService()

__all__ = [
    "ProgressService",
    "progress_service",
    "RecommendationNotFoundError",
    "RecommendationForbiddenError",
]
