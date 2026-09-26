"""
Pressure performance evaluation.

Deliberately thin: the technical/communication scoring, weak-topic
detection, AI narrative (strengths/weaknesses/recommendations/summary) and
voice-metrics aggregation are ALL produced by the existing
`InterviewEvaluationService.build_final_evaluation` (Step 9) -- called here
unmodified, on the pressure session's own question/answer documents (which
use the same shape as an interview session; see `app.models.pressure`).

This module only adds what is genuinely pressure-specific and does not
duplicate anything the interview evaluator already computes:

* a deterministic "Pressure Performance" score from how the candidate
  actually handled the pressure conditions (time limits, follow-ups,
  interruptions) -- never a proxy for confidence or anxiety
* plain-language "Observed Indicators" (pattern-level, not a nervousness
  score)
* an optional, clearly-labelled comparison against the user's own recent
  *normal* (non-pressure) interview practice

IMPORTANT: nothing here concludes that the user "was nervous" or "has
anxiety" -- see the module docstring in `app.models.pressure` and the
neutral-terminology rule in the Step 10 spec.
"""

from __future__ import annotations

from pymongo.database import Database

from app.db.collections import Collections
from app.services.interview.evaluation_service import (
    InterviewEvaluationService,
    answered_records,
)

# A response counts as "on time" up to this many seconds past its limit --
# network/UI latency shouldn't be held against the candidate.
TIMING_GRACE_SECONDS = 3

PRESSURE_CONDITION_LABELS = {
    "time_pressure": "a time limit",
    "topic_switch": "a topic switch",
    "difficult_question": "an unexpectedly harder question",
    "ambiguous_question": "an open-ended scenario",
    "none": "no added pressure condition",
}


def _all_records(question: dict) -> list[dict]:
    return [question] + list(question.get("follow_up_questions", []))


def compute_pressure_handling_score(session: dict) -> tuple[int | None, dict]:
    """
    Deterministic score (0-100) for how well timing, follow-ups and
    interruptions were handled, plus the raw counts it was built from.

    This measures observable handling of the pressure *conditions* (did the
    candidate answer within the time limit, keep going through follow-ups
    and interruptions) -- never the candidate's internal state.
    """
    questions = session.get("questions", [])
    timed_total = 0
    timed_ontime = 0
    follow_up_total = 0
    follow_up_answered = 0
    interruption_total = 0
    interruption_answered = 0
    conditions_faced: dict[str, int] = {}

    for q in questions:
        condition = q.get("condition") or {}
        ctype = condition.get("type", "none")
        conditions_faced[ctype] = conditions_faced.get(ctype, 0) + 1

        if condition.get("time_limit_seconds") is not None:
            timed_total += 1
            duration = q.get("response_duration_seconds")
            if not q.get("timed_out") and duration is not None and duration <= condition["time_limit_seconds"] + TIMING_GRACE_SECONDS:
                timed_ontime += 1

        for fu in q.get("follow_up_questions", []):
            if fu.get("kind") == "interruption":
                interruption_total += 1
                if fu.get("answer"):
                    interruption_answered += 1
            elif fu.get("kind") == "rapid":
                follow_up_total += 1
                if fu.get("answer"):
                    follow_up_answered += 1

    components: list[float] = []
    if timed_total:
        components.append(100 * timed_ontime / timed_total)
    if follow_up_total:
        components.append(100 * follow_up_answered / follow_up_total)
    if interruption_total:
        components.append(100 * interruption_answered / interruption_total)

    score = round(sum(components) / len(components)) if components else None
    return score, {
        "timed_prompts": timed_total,
        "timed_prompts_on_time": timed_ontime,
        "follow_ups_faced": follow_up_total,
        "follow_ups_answered": follow_up_answered,
        "interruptions_faced": interruption_total,
        "interruptions_answered": interruption_answered,
        "conditions_faced": conditions_faced,
    }


def compute_response_control_score(session: dict) -> int | None:
    """
    A second, complementary deterministic score: consistency of communication
    quality across the session (does clarity/conciseness hold up as
    conditions escalate). Uses the same per-answer communication_evaluation
    the interview evaluator already produced -- no new AI call.
    """
    scores: list[int] = []
    for q in session.get("questions", []):
        for record in answered_records(q):
            comm = record.get("communication_evaluation") or {}
            if comm.get("communication_score") is not None:
                scores.append(comm["communication_score"])
    if len(scores) < 2:
        return round(sum(scores)) if scores else None
    # Lower variance across answers => better response control under escalating pressure.
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    penalty = min(40.0, variance ** 0.5 * 2.5)  # stdev-based penalty, capped
    return max(0, min(100, round(mean - penalty + 20)))  # +20: don't punish a short, steady session


def build_pressure_indicators(session: dict) -> list[str]:
    """
    Plain-language, pattern-level observations -- never a diagnosis. Compares
    early vs. late answers in the session (a rough proxy for "as pressure
    increased"), using only measurable indicators.
    """
    indicators: list[str] = []
    questions = [q for q in session.get("questions", []) if q.get("answer")]
    if len(questions) < 2:
        return indicators

    half = max(1, len(questions) // 2)
    early, late = questions[:half], questions[half:]

    def metric(records: list[dict], key: str) -> list[float]:
        values = []
        for q in records:
            source = q.get("voice_analysis") or q.get("text_metrics")
            if source and source.get(key) is not None:
                values.append(source[key])
        return values

    early_wpm, late_wpm = metric(early, "speaking_rate_wpm"), metric(late, "speaking_rate_wpm")
    if early_wpm and late_wpm:
        e, l = sum(early_wpm) / len(early_wpm), sum(late_wpm) / len(late_wpm)
        if l > e * 1.1:
            indicators.append("Your speaking rate increased in the later part of the session.")
        elif l < e * 0.9:
            indicators.append("Your speaking rate slowed in the later part of the session.")

    early_fillers = sum(metric(early, "total_filler_words"))
    late_fillers = sum(metric(late, "total_filler_words"))
    if late_fillers > early_fillers:
        indicators.append("You used more filler words in the later, higher-pressure questions.")

    early_len = [q.get("text_metrics", {}).get("word_count") or 0 for q in early if q.get("text_metrics")]
    late_len = [q.get("text_metrics", {}).get("word_count") or 0 for q in late if q.get("text_metrics")]
    if early_len and late_len and (sum(late_len) / len(late_len)) < (sum(early_len) / len(early_len)) * 0.7:
        indicators.append("Your responses became noticeably shorter under time limits.")

    long_pauses = [q.get("voice_analysis", {}).get("long_pauses") for q in late if q.get("voice_analysis")]
    long_pauses = [p for p in long_pauses if p]
    if long_pauses:
        indicators.append("You had longer pauses on some of the later, harder questions.")

    timed_out = sum(1 for q in questions if q.get("timed_out"))
    if timed_out:
        indicators.append(
            f"The time limit expired before you finished {timed_out} response"
            f"{'s' if timed_out != 1 else ''}."
        )

    return indicators[:6]


def build_baseline_comparison(db: Database, *, user_id: str, exclude_session_id: str | None = None) -> dict | None:
    """
    Compare this pressure session against the user's most recent completed,
    *normal* (non-pressure) interview practice, if any. Returns None -- and
    the caller must say "No baseline available yet" -- rather than a made-up
    comparison when there isn't one.
    """
    from bson import ObjectId

    query: dict = {"user_id": ObjectId(user_id), "status": "completed"}
    baseline = (
        db[Collections.INTERVIEW_SESSIONS]
        .find(query, {"final_evaluation": 1})
        .sort("started_at", -1)
        .limit(1)
    )
    doc = next(baseline, None)
    if doc is None or not doc.get("final_evaluation"):
        return None

    normal = doc["final_evaluation"]
    normal_voice = normal.get("voice_summary") or {}
    return {
        "baseline_available": True,
        "normal_practice": {
            "technical_score": normal.get("technical_score"),
            "communication_score": normal.get("communication_score"),
            "speaking_rate_wpm": normal_voice.get("average_speaking_rate_wpm"),
            "filler_words": normal_voice.get("total_filler_words"),
        },
    }


def unavailable_baseline() -> dict:
    return {"baseline_available": False, "message": "No baseline available yet."}


class PressureEvaluationService:
    """Builds the Step 10 final evaluation on top of the Step 9 interview evaluator."""

    def __init__(self, interview_evaluation_service_: InterviewEvaluationService) -> None:
        self._interview_eval = interview_evaluation_service_

    async def build_final_evaluation(
        self, db: Database, session: dict, *, learning_topics: list[dict]
    ) -> dict:
        # Reuse the existing interview engine's scoring, weak-topic detection,
        # AI narrative and voice-summary aggregation, unmodified.
        base = await self._interview_eval.build_final_evaluation(session, learning_topics=learning_topics)

        pressure_score, pressure_counts = compute_pressure_handling_score(session)
        response_control = compute_response_control_score(session)
        indicators = build_pressure_indicators(session)
        comparison = build_baseline_comparison(db, user_id=str(session["user_id"])) or unavailable_baseline()

        return {
            **base,
            "pressure_handling_score": pressure_score,
            "pressure_handling_label": "Pressure Performance",
            "response_control_score": response_control,
            "clarity_score": (base.get("voice_summary") or {}).get("clarity_score"),
            "pressure_indicators": indicators,
            "pressure_condition_counts": pressure_counts,
            "areas_to_improve": base.get("weaknesses", []),
            "comparison": comparison,
        }
