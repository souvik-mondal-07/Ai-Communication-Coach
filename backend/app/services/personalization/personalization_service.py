"""
Personalization facade (Step 16).

Computes, on request, a compact personalization profile from data the earlier
steps already store, and builds the *bounded* context the AI mentor receives.
No new collection and no background job: aggregation is a handful of cheap
Mongo queries, and the mentor path adds a short in-process TTL cache so a
chat session does not recompute on every message (API reads are always fresh).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from pymongo.database import Database

from app.models.user import UserDocument
from app.services.auth.profile_service import to_profile_response
from app.services.personalization import performance_service as perf
from app.services.personalization import recommendation_service as rec
from app.services.personalization import weakness_service as weak
from app.services.progress import aggregation_service as agg
from app.services.progress import weakness_service as step11_weak
from app.services.progress.aggregation_service import MIN_ATTEMPTS

MENTOR_CONTEXT_TTL_SECONDS = 30
MAX_CONTEXT_ITEMS = 3
MAX_CONTEXT_TEXT = 100

NO_DATA_MESSAGE = (
    "Not enough data yet. Complete a few practice sessions to receive "
    "personalized recommendations."
)

_mentor_cache: dict[str, tuple[float, dict | None]] = {}


def clear_cache() -> None:
    _mentor_cache.clear()


def _clean(text: str | None, limit: int = MAX_CONTEXT_TEXT) -> str:
    """User-authored text going into an AI prompt: single line, bounded."""
    return " ".join((text or "").split())[:limit]


def _label(value: str) -> str:
    return value.replace("_", " ")


class PersonalizationService:
    # ------------------------------------------------------------------ compute
    def compute(self, db: Database, *, user: UserDocument) -> dict:
        """Everything is scoped to `user["_id"]` (from the JWT) -- no other id is ever accepted."""
        user_id = str(user["_id"])
        settings = to_profile_response(user)
        profile = settings.profile.model_dump(mode="json")
        prefs = settings.preferences.model_dump(mode="json")

        ctf = agg.get_ctf_breakdown(db, user_id=user_id)
        interview = agg.get_interview_summary(db, user_id=user_id)
        comm = agg.get_communication_summary(db, user_id=user_id)
        pressure = agg.get_pressure_summary(db, user_id=user_id)

        rows = perf.build_topic_performance(db, user_id=user_id, ctf_breakdown=ctf, interview_summary=interview)
        strengths, weaknesses = weak.classify(rows)
        other = [
            *step11_weak.detect_interview_weaknesses(interview),
            *step11_weak.detect_communication_weaknesses(comm),
            *step11_weak.detect_pressure_weaknesses(pressure),
        ]
        recs = rec.build_recommendations(
            db, user_id=user_id, profile=profile, preferences=prefs, rows=rows,
            weaknesses=weaknesses, other_weaknesses=other, has_interview_data=interview is not None,
        )

        has_activity = bool(rows or comm or pressure or interview)
        enough = any(r["attempts"] >= MIN_ATTEMPTS for r in rows)
        data_status = "sufficient" if enough else ("limited" if has_activity else "none")

        top = recs[0] if recs else None
        top_practice = next((r for r in recs if r["type"] == "practice"), None)
        experience = profile.get("experience_level")
        pref_diff = prefs["difficulty"]
        recommended_difficulty = (
            top_practice["difficulty"]
            if top_practice
            else rec.choose_difficulty(preference=pref_diff, experience_level=experience, row=None)[0]
        )

        return {
            "data_status": data_status,
            "message": None if data_status == "sufficient" else NO_DATA_MESSAGE,
            "user_level": experience or "beginner",
            "difficulty_preference": pref_diff,
            "recommended_difficulty": recommended_difficulty,
            "career_goal": profile.get("career_goal") or None,
            "interests": profile.get("cybersecurity_interests", []),
            "response_style": prefs["response_style"],
            "learning_style": prefs["learning_style"],
            "interview_focus": prefs["interview_focus"],
            "strengths": strengths,
            "weaknesses": weaknesses,
            "other_weaknesses": [
                {"area": w["area"], "source": w["source"], "severity": w["severity"],
                 "average_score": w["evidence"]["average_score"], "attempts": w["evidence"]["attempts"]}
                for w in other
            ],
            "topic_performance": [
                {**r, "last_practiced": r["last_practiced"].isoformat() if r["last_practiced"] else None}
                for r in sorted(rows, key=lambda r: -r["attempts"])
            ],
            "communication": perf.build_communication_signals(comm, pressure),
            "current_focus": (
                {"topic": top["topic"], "title": top["title"], "basis": top["basis"], "reasons": top["reasons"]}
                if top else None
            ),
            "recommended_topics": [r["topic"] for r in recs if r["type"] == "practice"],
            "recommended_activity": top,
            "recommendations": recs,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------ API read views
    def get_profile(self, db: Database, *, user: UserDocument) -> dict:
        return self.compute(db, user=user)

    def get_recommendations(self, db: Database, *, user: UserDocument) -> dict:
        full = self.compute(db, user=user)
        return {k: full[k] for k in (
            "data_status", "message", "current_focus", "recommended_difficulty",
            "recommended_activity", "recommendations",
        )}

    def get_weaknesses(self, db: Database, *, user: UserDocument) -> dict:
        full = self.compute(db, user=user)
        return {k: full[k] for k in ("data_status", "message", "weaknesses", "strengths", "other_weaknesses")}

    # ------------------------------------------------------------ AI mentor context
    def build_mentor_context(self, db: Database, *, user: UserDocument, use_cache: bool = True) -> dict | None:
        """
        Compact, bounded context for the mentor prompt: a handful of short
        fields, never raw sessions, transcripts or history. Returns None when
        there is nothing to personalize with. Never raises.
        """
        user_id = str(user["_id"])
        now = time.monotonic()
        if use_cache:
            hit = _mentor_cache.get(user_id)
            if hit and now - hit[0] < MENTOR_CONTEXT_TTL_SECONDS:
                return hit[1]
        try:
            context = self._context_from(self.compute(db, user=user))
        except Exception:  # noqa: BLE001 - personalization must never break the chat
            return None
        if use_cache:
            _mentor_cache[user_id] = (now, context)
        return context

    @staticmethod
    def _context_from(full: dict) -> dict | None:
        top = full["recommended_activity"]
        strengths = [s["topic"] for s in full["strengths"]][:MAX_CONTEXT_ITEMS]
        weaknesses = [w["topic"] for w in full["weaknesses"]][:MAX_CONTEXT_ITEMS]
        interests = [_label(i) for i in full["interests"]][:5]
        practiced = sorted(
            (r for r in full["topic_performance"] if r["last_practiced"]),
            key=lambda r: r["last_practiced"], reverse=True,
        )
        recent = [r["topic"] for r in practiced]
        has_signal = bool(full["career_goal"] or interests or strengths or weaknesses or top)
        if not has_signal:
            return None
        return {
            # Step 11 keys (existing mentor block already renders these) ...
            "technical_level": full["user_level"],
            "strong_areas": strengths,
            "weak_areas": weaknesses,
            "recent_focus": recent[:MAX_CONTEXT_ITEMS],
            "recommended_focus": [top["topic"]] if top else [],
            # ... plus the Step 16 additions.
            "career_goal": _clean(full["career_goal"]),
            "interests": interests,
            "response_style": full["response_style"],
            "learning_style": full["learning_style"],
            "suggested_difficulty": full["recommended_difficulty"],
            "recommended_topic": _clean(top["title"]) if top else "",
            "data_basis": top["basis"] if top else "none",
        }


personalization_service = PersonalizationService()
