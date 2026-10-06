"""
Analytics facade (Step 18).

A derived, read-only layer: every number comes from existing session documents via
`facts.load_facts`. Nothing is stored. The user is always the authenticated user
passed in by the route -- no other id is ever accepted.

Insights are deterministic and evidence-gated. Gemini is optional and only ever
receives a compact, already-computed summary (no transcripts, no raw history); if
it is unavailable the deterministic insights are returned unchanged.

Recommendations reuse the existing personalization recommender (Step 16): its
`recommendations` are returned as-is, and analytics weaknesses are mapped to a short
action plus the same app routes the recommender uses -- no second recommender.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pymongo.database import Database

from app.models.user import UserDocument
from app.services.ai.ai_service import AIService, AIServiceError, ai_service
from app.services.analytics import config
from app.services.analytics.common import DateRange, change_label, mean
from app.services.analytics.communication_analytics import communication_report
from app.services.analytics.facts import Facts, load_facts, spoken_samples
from app.services.analytics.interview_analytics import (
    domain_breakdown, interview_report, mode_breakdown, window_compare,
)
from app.services.analytics.pressure_analytics import pressure_report
from app.services.analytics.readiness import readiness_report
from app.services.analytics.speaking_analytics import aggregate_samples, speaking_report
from app.services.analytics.trend_analytics import trend_report
from app.services.interview.structured_ai import StructuredOutputError, generate_validated
from app.services.personalization.personalization_service import personalization_service
from app.services.personalization.recommendation_service import _ROUTES
from app.utils.logger import get_logger

logger = get_logger(__name__)

NO_DATA_MESSAGE = "Complete your first interview to unlock analytics."
EARLY_MESSAGE = "Early data. More practice is needed for reliable trends."

# weakness id -> (action, route kind). Routes come from the existing recommender.
WEAKNESS_ACTIONS = {
    "filler_words": ("Do a 5-minute speaking practice focused on pausing instead of using fillers.", "communication"),
    "long_pauses": ("Practise Think -> Speak: take two seconds to plan, then answer in one steady flow.", "communication"),
    "repeated_words": ("Do a short voice conversation and re-read the transcript for repeated words.", "communication"),
    "weak_structure": ("Practise 60-second structured answers (definition, explanation, example).", "interview"),
    "answers_too_short": ("Aim to add an example and a practical use to each answer.", "interview"),
    "answers_too_long": ("Practise concluding each answer in under a minute, then offering to expand.", "interview"),
    "shallow_technical_explanation": ("Revisit the topic and practise explaining the 'why', not just the 'what'.", "practice"),
    "low_confidence": ("Practise answering aloud with a clear opening line and a firm close.", "communication"),
}


class _AiSummary(BaseModel):
    summary: str = Field(min_length=1, max_length=900)


def data_status(facts: Facts) -> dict:
    total = facts.total_sessions
    if total == 0:
        return {"status": "none", "message": NO_DATA_MESSAGE, "sessions": 0}
    if total < config.EARLY_DATA_SESSIONS:
        return {"status": "early", "message": EARLY_MESSAGE, "sessions": total}
    return {"status": "sufficient", "message": None, "sessions": total}


def _meta(window: DateRange, facts: Facts) -> dict:
    return {
        "range": window.label,
        "start": window.start.isoformat() if window.start else None,
        "end": window.end.isoformat(),
        "truncated": facts.truncated,
        "data": data_status(facts),
    }


class AnalyticsService:
    def __init__(self, ai_service_: AIService = ai_service) -> None:
        self._ai = ai_service_

    # ------------------------------------------------------------------ loading
    def _load(self, db: Database, user: UserDocument, window: DateRange) -> Facts:
        return load_facts(db, user_id=str(user["_id"]), window=window)

    def _load_previous(self, db: Database, user: UserDocument, window: DateRange) -> Facts | None:
        prev = window.previous()
        return None if prev is None else load_facts(db, user_id=str(user["_id"]), window=prev)

    # ----------------------------------------------------------------- sections
    def overview(self, db: Database, *, user: UserDocument, window: DateRange) -> dict:
        facts = self._load(db, user, window)
        previous = self._load_previous(db, user, window)
        iv = interview_report(facts)["overview"]
        confidence = mean(c["confidence"] for c in facts.communication)
        return {
            **_meta(window, facts),
            "readiness": readiness_report(facts),
            "scores": {
                "technical": iv["technical_score"],
                "communication": iv["communication_score"],
                "confidence": confidence,
                "overall": iv["overall_score"],
            },
            "counts": {"interviews": len(facts.interviews), "pressure": len(facts.pressure),
                       "communication": len(facts.communication), "practice": len(facts.practice)},
            "comparison": window_compare(previous, facts),
        }

    def interviews(self, db: Database, *, user: UserDocument, window: DateRange) -> dict:
        facts = self._load(db, user, window)
        return {**_meta(window, facts), **interview_report(facts), "domains_note": "See /analytics/domains."}

    def communication(self, db: Database, *, user: UserDocument, window: DateRange) -> dict:
        facts = self._load(db, user, window)
        return {**_meta(window, facts), **communication_report(facts)}

    def speaking(self, db: Database, *, user: UserDocument, window: DateRange) -> dict:
        facts = self._load(db, user, window)
        previous = self._load_previous(db, user, window)
        report = speaking_report(facts)
        comparison: dict = {"available": False}
        if previous is not None and report["available"]:
            cur, prev = spoken_samples(facts), spoken_samples(previous)
            cur_m, prev_m = aggregate_samples(cur), aggregate_samples(prev) if prev else {}
            comparison = {
                "available": len(prev) >= config.MIN_VOICE_SAMPLES,
                "filler_per_100_words": _metric_change(prev_m.get("filler_per_100_words"), cur_m["filler_per_100_words"], False),
                "words_per_minute": _metric_change(prev_m.get("words_per_minute"), cur_m["words_per_minute"], True),
            } if len(prev) >= config.MIN_VOICE_SAMPLES else {"available": False}
        return {**_meta(window, facts), **report, "comparison": comparison}

    def pressure(self, db: Database, *, user: UserDocument, window: DateRange) -> dict:
        facts = self._load(db, user, window)
        return {**_meta(window, facts), **pressure_report(facts)}

    def domains(self, db: Database, *, user: UserDocument, window: DateRange) -> dict:
        facts = self._load(db, user, window)
        return {**_meta(window, facts), **domain_breakdown(facts), "modes": mode_breakdown(facts)}

    def trends(self, db: Database, *, user: UserDocument, window: DateRange) -> dict:
        facts = self._load(db, user, window)
        return {**_meta(window, facts), **trend_report(facts, window)}

    def readiness(self, db: Database, *, user: UserDocument, window: DateRange) -> dict:
        facts = self._load(db, user, window)
        return {**_meta(window, facts), **readiness_report(facts)}

    # ----------------------------------------------------------------- insights
    def build_insights(self, db: Database, *, user: UserDocument, window: DateRange) -> dict:
        facts = self._load(db, user, window)
        previous = self._load_previous(db, user, window)
        status = data_status(facts)
        base = {**_meta(window, facts), "insights": [], "strengths": [], "weaknesses": [], "next_actions": [],
                "recommendations": [], "ai_summary": None}
        if status["status"] == "none":
            return base

        comm = communication_report(facts)
        domains = domain_breakdown(facts)
        modes = mode_breakdown(facts)
        pressure = pressure_report(facts)
        cmp_ = window_compare(previous, facts)
        insights: list[dict] = []

        def add(kind: str, text: str, evidence: str) -> None:
            insights.append({"kind": kind, "text": text, "evidence": evidence})

        if cmp_["available"]:
            for key, label in (("technical", "technical score"), ("communication", "communication score")):
                c = cmp_[key]
                if c["available"] and c["label"] in ("Significant improvement", "Improving"):
                    add("improvement", f"Your {label} improved by {c['change']} points compared with the previous period.",
                        f"{c['previous']} -> {c['current']} ({c['previous_samples']} vs {c['current_samples']} sessions)")
                elif c["available"] and c["label"] in ("Slight decline", "Needs attention"):
                    add("decline", f"Your {label} dropped by {abs(c['change'])} points compared with the previous period.",
                        f"{c['previous']} -> {c['current']} ({c['previous_samples']} vs {c['current_samples']} sessions)")

        reliable_modes = [m for m in modes if m["reliable"] and m["mode"] != "pressure"]
        if len(reliable_modes) >= 2:
            best, worst = reliable_modes[0], reliable_modes[-1]
            if best["overall_score"] - worst["overall_score"] >= config.IMPROVING_DELTA:
                add("mode", f"Your strongest interview type is {best['label']} ({best['overall_score']}%); {worst['label']} is your weakest ({worst['overall_score']}%).",
                    f"{best['sessions']} and {worst['sessions']} sessions")
        if domains["strongest"]:
            d = domains["strongest"][0]
            add("domain", f"{d['domain']} is your strongest cybersecurity domain ({d['score']}%).", f"{d['questions']} scored questions")
        if domains["weakest"]:
            d = domains["weakest"][0]
            add("domain", f"{d['domain']} is your weakest cybersecurity domain ({d['score']}%).", f"{d['questions']} scored questions")

        if comm["weaknesses"]:
            w = comm["weaknesses"][0]
            add("communication", f"Your biggest recurring communication issue is: {w['label'].lower()}.", w["evidence"])

        dims = {d["key"]: d["score"] for d in comm["dimensions"]}
        tech = mean(s["technical"] for s in facts.interviews)
        if tech is not None and tech >= config.STRONG_SCORE and dims.get("structure") is not None and dims["structure"] < config.WEAK_SCORE:
            add("structure", "Your answers are technically strong but often lack a clear structure.",
                f"technical {tech}, structure {dims['structure']}")

        insights.extend({"kind": "pressure", "text": t, "evidence": "normal vs pressure sessions"}
                        for t in pressure.get("insights", []))

        mode_gap = [m for m in modes if m["reliable"] and m["mode"] != "pressure" and m["overall_score"] < config.WEAK_SCORE + 10]
        if mode_gap:
            m = min(mode_gap, key=lambda x: x["overall_score"])
            add("next", f"You should practise {m['label'].lower()} questions next.", f"{m['overall_score']}% over {m['sessions']} sessions")

        strengths = [f"{d['domain']} ({d['score']}%)" for d in domains["strongest"]]
        strengths += [f"{d['key'].title()} ({d['score']})" for d in comm["dimensions"] if d["band"] == "strong"][:3]

        actions = []
        for w in comm["weaknesses"]:
            action, kind = WEAKNESS_ACTIONS[w["id"]]
            actions.append({"weakness": w["label"], "action": action, "route": _ROUTES.get(kind, "/interview"), "evidence": w["evidence"]})
        for d in domains["weakest"]:
            actions.append({"weakness": f"Weak {d['domain']} reasoning", "action": f"Practise {d['domain']} questions.",
                            "route": _ROUTES["practice"], "evidence": f"{d['score']}% over {d['questions']} questions"})

        recs: list[dict] = []
        try:
            recs = personalization_service.get_recommendations(db, user=user).get("recommendations", [])
        except Exception:  # noqa: BLE001 - analytics must not fail because recommendations did
            logger.warning("Recommendations unavailable for analytics", exc_info=True)

        return {**base, "insights": insights[: config.MAX_LIST_ITEMS + 4], "strengths": strengths[:5],
                "weaknesses": comm["weaknesses"], "next_actions": actions[: config.MAX_LIST_ITEMS], "recommendations": recs}

    async def insights_with_ai(self, db: Database, *, user: UserDocument, window: DateRange, use_ai: bool) -> dict:
        result = self.build_insights(db, user=user, window=window)
        if not use_ai or not result["insights"] or result["data"]["status"] != "sufficient":
            return result
        compact = "\n".join(f"- {i['text']} ({i['evidence']})" for i in result["insights"][:8])
        try:
            out = await generate_validated(
                self._ai,
                user_prompt=("Summarise these already-computed interview analytics for the learner in 2-3 "
                             "encouraging, performance-focused sentences. Do not add facts, numbers or medical/"
                             "psychological claims.\n" + compact),
                system_prompt="You are a concise cybersecurity interview coach. Respond only with JSON {\"summary\": string}.",
                model=_AiSummary,
            )
            result["ai_summary"] = out.summary.strip()
        except (AIServiceError, StructuredOutputError) as exc:
            logger.warning("Analytics AI summary unavailable: %s", type(exc).__name__)
        return result


def _metric_change(prev: float | None, cur: float | None, higher_is_better: bool) -> dict:
    if prev is None or cur is None:
        return {"previous": prev, "current": cur, "change": None, "label": None}
    return {"previous": prev, "current": cur, "change": round(cur - prev, 1),
            "label": change_label(cur - prev, higher_is_better=higher_is_better)}


analytics_service = AnalyticsService()
