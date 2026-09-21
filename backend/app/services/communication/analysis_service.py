"""
Speaking analysis.

Two layers, combined:

1. **Deterministic metrics** (no AI): word/sentence counts, filler words,
   repetition, speaking rate, pause statistics, and heuristic clarity /
   vocabulary / conciseness scores. A metric that can't be measured reliably
   is `None` — never invented.
2. **AI feedback** through the existing `AIService` (never a second Gemini
   client): qualitative scores for clarity, grammar, vocabulary and
   conciseness plus strengths/improvements.

Everything here is an *approximate communication indicator*. Nothing claims
to measure psychological confidence, anxiety, or any medical condition.
Transcripts are never logged.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.services.ai.ai_service import AIService, ai_service
from app.services.communication.prompts import (
    SPEAKING_ANALYSIS_PROMPT,
    build_speaking_feedback_prompt,
)
from app.utils.helpers import parse_json_object
from app.utils.logger import get_logger
from app.utils.text_analysis import (
    count_sentences,
    count_words,
    detect_filler_words,
    find_overused_words,
    find_repeated_words,
    lexical_diversity,
)

logger = get_logger(__name__)

# --- Tunable constants (approximate guidance, not scientific thresholds) ----

MIN_PAUSE_SECONDS = 0.5  # a gap this long between words counts as a pause
LONG_PAUSE_SECONDS = 2.0
MIN_DURATION_FOR_WPM = 2.0  # too little audio => rate is meaningless
WPM_SLOW_BELOW = 100
WPM_FAST_ABOVE = 160
MIN_WORDS_FOR_SCORES = 8
MIN_WORDS_FOR_VOCABULARY = 20
AI_SCORE_WEIGHT = 0.6  # blended score = 0.6 * AI + 0.4 * deterministic
MAX_FEEDBACK_ITEMS = 6


def _clamp_score(value: float) -> int:
    return int(max(0, min(100, round(value))))


# --- Pauses -----------------------------------------------------------------


def calculate_pause_metrics(
    intervals: Sequence[tuple[float, float]] | None, *, granularity: str = "word"
) -> dict | None:
    """
    Pause statistics from (start, end) timestamps of consecutive words (or
    segments). A "pause" is a gap of at least `MIN_PAUSE_SECONDS` between one
    item's end and the next one's start; leading/trailing silence is ignored.

    Returns None when there aren't at least two valid timed items — i.e. when
    pauses can't be measured. `average_pause_seconds` / `longest_pause_seconds`
    are None when the speech was measured but contained no pauses.
    """
    if not intervals:
        return None
    valid = sorted(
        (
            (float(s), float(e))
            for s, e in intervals
            if math.isfinite(s) and math.isfinite(e) and 0 <= s <= e
        )
    )
    if len(valid) < 2:
        return None

    gaps: list[float] = []
    prev_end = valid[0][1]
    for start, end in valid[1:]:
        gap = start - prev_end
        if gap >= MIN_PAUSE_SECONDS:
            gaps.append(gap)
        prev_end = max(prev_end, end)

    return {
        "pause_count": len(gaps),
        "long_pauses": sum(1 for g in gaps if g >= LONG_PAUSE_SECONDS),
        "average_pause_seconds": round(sum(gaps) / len(gaps), 2) if gaps else None,
        "longest_pause_seconds": round(max(gaps), 2) if gaps else None,
        "total_pause_seconds": round(sum(gaps), 2),
        "granularity": granularity,
    }


# --- Speaking rate ----------------------------------------------------------


def calculate_speaking_rate(word_count: int, duration_seconds: float | None) -> int | None:
    """Words per minute = words / minutes, or None if it can't be trusted."""
    if not duration_seconds or duration_seconds < MIN_DURATION_FOR_WPM or word_count <= 0:
        return None
    return round(word_count / (duration_seconds / 60))


def speaking_rate_label(wpm: int | None) -> str | None:
    if wpm is None:
        return None
    if wpm < WPM_SLOW_BELOW:
        return "slow"
    if wpm > WPM_FAST_ABOVE:
        return "fast"
    return "moderate"


# --- Per-message analysis ---------------------------------------------------


def _heuristic_scores(
    *,
    word_count: int,
    avg_sentence_length: float,
    filler_rate: float,
    repeated_total: int,
    overused: dict[str, int],
    long_pauses: int,
    diversity: float | None,
) -> dict[str, int | None]:
    if word_count < MIN_WORDS_FOR_SCORES:
        return {"clarity_score": None, "vocabulary_score": None, "conciseness_score": None}

    long_sentence = min(25.0, max(0.0, avg_sentence_length - 25) * 1.5)
    clarity = (
        100
        - long_sentence
        - min(25.0, filler_rate * 2.5)
        - min(15.0, repeated_total * 3)
        - min(10.0, long_pauses * 3)
    )
    overuse_excess = sum(max(0, c - 2) for c in overused.values())
    conciseness = (
        100
        - min(30.0, max(0.0, avg_sentence_length - 20) * 2)
        - min(25.0, filler_rate * 2)
        - min(15.0, repeated_total * 3)
        - min(20.0, overuse_excess * 4)
    )
    vocabulary = (
        min(92, _clamp_score(35 + 90 * diversity))  # short samples inflate diversity
        if diversity is not None and word_count >= MIN_WORDS_FOR_VOCABULARY
        else None
    )
    return {
        "clarity_score": _clamp_score(clarity),
        "vocabulary_score": vocabulary,
        "conciseness_score": _clamp_score(conciseness),
    }


def analyze_transcript(
    text: str,
    *,
    duration_seconds: float | None = None,
    pause_metrics: dict | None = None,
    language: str | None = None,
    transcript_edited: bool = False,
    filler_words: Iterable[str] | None = None,
) -> dict:
    """
    Deterministic analysis of one spoken message.

    `duration_seconds` and `pause_metrics` come from the audio (via the
    speech-to-text step); when absent, the audio-based fields are None.
    Grammar is not scored here — that needs the AI (see `SpeakingAnalysisService`).
    """
    if filler_words is None:
        filler_words = settings.filler_words_list

    word_count = count_words(text)
    sentence_count = count_sentences(text)
    avg_sentence_length = round(word_count / sentence_count, 1) if sentence_count else 0.0

    fillers, total_fillers = detect_filler_words(text, filler_words)
    repeated, total_repeated = find_repeated_words(text)
    overused = find_overused_words(text)
    filler_rate = (total_fillers / word_count * 100) if word_count else 0.0

    wpm = calculate_speaking_rate(word_count, duration_seconds)
    pauses = pause_metrics or {}

    scores = _heuristic_scores(
        word_count=word_count,
        avg_sentence_length=avg_sentence_length,
        filler_rate=filler_rate,
        repeated_total=total_repeated,
        overused=overused,
        long_pauses=pauses.get("long_pauses") or 0,
        diversity=lexical_diversity(text),
    )

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "average_sentence_length": avg_sentence_length,
        "duration_seconds": round(duration_seconds, 1) if duration_seconds else None,
        "speaking_rate_wpm": wpm,
        "speaking_rate_label": speaking_rate_label(wpm),
        "filler_words": fillers,
        "total_filler_words": total_fillers,
        "filler_rate_per_100_words": round(filler_rate, 1),
        "repeated_words": repeated,
        "total_repeated_words": total_repeated,
        "overused_words": overused,
        # Audio-based: None => not measurable (never a made-up 0).
        "pause_count": pauses.get("pause_count"),
        "long_pauses": pauses.get("long_pauses"),
        "average_pause_seconds": pauses.get("average_pause_seconds"),
        "longest_pause_seconds": pauses.get("longest_pause_seconds"),
        "total_pause_seconds": pauses.get("total_pause_seconds"),
        **scores,
        "language": language,
        "transcript_edited": transcript_edited,
    }


# --- Session-level aggregation ----------------------------------------------


def _weighted_mean(pairs: list[tuple[float, int]]) -> int | None:
    total_weight = sum(w for _, w in pairs)
    if not pairs or total_weight <= 0:
        return None
    return _clamp_score(sum(v * w for v, w in pairs) / total_weight)


def aggregate_voice_analyses(analyses: Sequence[dict]) -> dict | None:
    """Combine per-message analyses into session-level deterministic metrics."""
    if not analyses:
        return None

    total_words = sum(a.get("word_count") or 0 for a in analyses)

    timed = [a for a in analyses if a.get("speaking_rate_wpm") is not None and a.get("duration_seconds")]
    timed_words = sum(a["word_count"] for a in timed)
    timed_seconds = sum(a["duration_seconds"] for a in timed)
    avg_wpm = calculate_speaking_rate(timed_words, timed_seconds) if timed else None
    total_duration = (
        round(sum(a["duration_seconds"] for a in analyses if a.get("duration_seconds")), 1) or None
    )

    fillers: Counter[str] = Counter()
    repeated: Counter[str] = Counter()
    for a in analyses:
        fillers.update(a.get("filler_words") or {})
        repeated.update(a.get("repeated_words") or {})
    total_fillers = sum(fillers.values())

    with_pauses = [a for a in analyses if a.get("pause_count") is not None]
    if with_pauses:
        pause_count = sum(a["pause_count"] for a in with_pauses)
        long_pauses = sum(a.get("long_pauses") or 0 for a in with_pauses)
        pause_seconds = sum(a.get("total_pause_seconds") or 0.0 for a in with_pauses)
        longest = [a["longest_pause_seconds"] for a in with_pauses if a.get("longest_pause_seconds")]
        pauses: dict[str, Any] = {
            "pause_count": pause_count,
            "long_pauses": long_pauses,
            "average_pause_seconds": round(pause_seconds / pause_count, 2) if pause_count else None,
            "longest_pause_seconds": round(max(longest), 2) if longest else None,
        }
    else:
        pauses = {
            "pause_count": None,
            "long_pauses": None,
            "average_pause_seconds": None,
            "longest_pause_seconds": None,
        }

    def _avg(key: str) -> int | None:
        return _weighted_mean(
            [(a[key], a.get("word_count") or 1) for a in analyses if a.get(key) is not None]
        )

    return {
        "voice_message_count": len(analyses),
        "total_words_spoken": total_words,
        "total_speaking_duration_seconds": total_duration,
        "average_speaking_rate_wpm": avg_wpm,
        "speaking_rate_label": speaking_rate_label(avg_wpm),
        "total_filler_words": total_fillers,
        "filler_rate_per_100_words": round(total_fillers / total_words * 100, 1) if total_words else 0.0,
        "filler_words": dict(sorted(fillers.items(), key=lambda kv: (-kv[1], kv[0]))),
        "repeated_words": dict(sorted(repeated.items(), key=lambda kv: (-kv[1], kv[0]))),
        **pauses,
        "clarity_score": _avg("clarity_score"),
        "vocabulary_score": _avg("vocabulary_score"),
        "conciseness_score": _avg("conciseness_score"),
    }


def build_metric_insights(aggregate: dict) -> tuple[list[str], list[str]]:
    """Plain-language, purely metric-based strengths and improvements."""
    strengths: list[str] = []
    improvements: list[str] = []

    wpm = aggregate.get("average_speaking_rate_wpm")
    label = aggregate.get("speaking_rate_label")
    if label == "moderate":
        strengths.append(f"Your speaking pace (about {wpm} WPM) was in a comfortable conversational range.")
    elif label == "slow":
        improvements.append(
            f"Your pace was on the slower side (about {wpm} WPM). Practising answers out loud can help them flow more smoothly."
        )
    elif label == "fast":
        improvements.append(
            f"Your pace was quick (about {wpm} WPM). Slowing down slightly can help listeners follow you."
        )

    total_fillers = aggregate.get("total_filler_words") or 0
    rate = aggregate.get("filler_rate_per_100_words") or 0
    if total_fillers >= 2 or rate >= 3:
        top = list(aggregate.get("filler_words", {}).items())[:3]
        listed = ", ".join(f'"{w}" ({c}×)' for w, c in top)
        improvements.append(f"Reduce filler words such as {listed}.")
    elif (aggregate.get("total_words_spoken") or 0) >= 20:
        strengths.append("You used very few filler words.")

    long_pauses = aggregate.get("long_pauses")
    if long_pauses:
        improvements.append(
            f"You had {long_pauses} long pause{'s' if long_pauses != 1 else ''} (over {LONG_PAUSE_SECONDS:g} seconds). "
            "A short bridging phrase like \"Let me think about that\" can help."
        )
    elif long_pauses == 0 and (aggregate.get("pause_count") is not None):
        strengths.append("You kept a steady flow without long pauses.")

    repeated = list(aggregate.get("repeated_words", {}).items())[:3]
    if repeated:
        listed = ", ".join(f'"{w}"' for w, _ in repeated)
        improvements.append(f"Avoid immediately repeating words (for example {listed}).")

    return strengths, improvements


# --- AI feedback ------------------------------------------------------------


class _GeneratedSpeakingFeedback(BaseModel):
    """Validated shape of the AI's speaking feedback (internal only)."""

    clarity_score: int = Field(ge=0, le=100)
    grammar_score: int = Field(ge=0, le=100)
    vocabulary_score: int = Field(ge=0, le=100)
    conciseness_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=2000)


def _blend(deterministic: int | None, ai: int | None) -> int | None:
    if ai is None:
        return deterministic
    if deterministic is None:
        return ai
    return _clamp_score(AI_SCORE_WEIGHT * ai + (1 - AI_SCORE_WEIGHT) * deterministic)


def _clean_items(items: list[str]) -> list[str]:
    cleaned = [i.strip()[:300] for i in items if isinstance(i, str) and i.strip()]
    return cleaned[:MAX_FEEDBACK_ITEMS]


def compose_voice_summary(aggregate: dict, ai_feedback: _GeneratedSpeakingFeedback | None) -> dict:
    """Merge deterministic aggregate metrics with (optional) AI feedback."""
    metric_strengths, metric_improvements = build_metric_insights(aggregate)
    ai_strengths = _clean_items(ai_feedback.strengths) if ai_feedback else []
    ai_improvements = _clean_items(ai_feedback.improvements) if ai_feedback else []

    return {
        **aggregate,
        "clarity_score": _blend(aggregate.get("clarity_score"), ai_feedback.clarity_score if ai_feedback else None),
        # Grammar can't be measured deterministically — AI only.
        "grammar_score": ai_feedback.grammar_score if ai_feedback else None,
        "vocabulary_score": _blend(
            aggregate.get("vocabulary_score"), ai_feedback.vocabulary_score if ai_feedback else None
        ),
        "conciseness_score": _blend(
            aggregate.get("conciseness_score"), ai_feedback.conciseness_score if ai_feedback else None
        ),
        "strengths": (ai_strengths + metric_strengths)[:MAX_FEEDBACK_ITEMS],
        "improvements": (ai_improvements + metric_improvements)[:MAX_FEEDBACK_ITEMS],
        "summary": ai_feedback.summary.strip() if ai_feedback and ai_feedback.summary.strip() else None,
        "ai_feedback_available": ai_feedback is not None,
    }


def _format_metrics_for_prompt(aggregate: dict) -> str:
    def fmt(value: Any, suffix: str = "") -> str:
        return "not measurable" if value is None else f"{value}{suffix}"

    fillers = ", ".join(f"{w} ×{c}" for w, c in aggregate.get("filler_words", {}).items()) or "none"
    return "\n".join(
        [
            f"- Words spoken: {aggregate.get('total_words_spoken')}",
            f"- Average speaking rate: {fmt(aggregate.get('average_speaking_rate_wpm'), ' WPM')}",
            f"- Filler words: {aggregate.get('total_filler_words')} ({fillers})",
            f"- Pauses over {MIN_PAUSE_SECONDS:g}s: {fmt(aggregate.get('pause_count'))} "
            f"(longest {fmt(aggregate.get('longest_pause_seconds'), ' s')})",
        ]
    )


def _voice_messages(session: dict) -> list[dict]:
    return [
        m
        for m in session.get("messages", [])
        if m.get("role") == "user" and m.get("input_type") == "voice"
    ]


def _build_speaking_transcript(session: dict) -> str:
    lines = []
    for m in session.get("messages", []):
        if m["role"] == "assistant":
            lines.append(f"AI character: {m['content']}")
        else:
            kind = "spoken" if m.get("input_type") == "voice" else "typed"
            lines.append(f"Learner ({kind}): {m['content']}")
    return "\n".join(lines)


class SpeakingAnalysisService:
    """Builds the session-level `voice_summary` for a voice-mode session."""

    def __init__(self, ai_service_: AIService = ai_service) -> None:
        self._ai_service = ai_service_

    async def build_voice_summary(self, session: dict) -> dict | None:
        """
        Returns the `voice_summary` for `session`, or None if it has no spoken
        messages. Never raises: if the AI part fails, the deterministic
        metrics are still returned with `ai_feedback_available: False`.
        """
        voice_messages = _voice_messages(session)
        if not voice_messages:
            return None

        analyses = [m.get("voice_analysis") or analyze_transcript(m["content"]) for m in voice_messages]
        aggregate = aggregate_voice_analyses(analyses)
        if aggregate is None:
            return None

        feedback: _GeneratedSpeakingFeedback | None = None
        try:
            prompt = build_speaking_feedback_prompt(
                scenario_title=session.get("scenario_title", ""),
                objective=session.get("objective", "realistic conversation practice"),
                metrics=_format_metrics_for_prompt(aggregate),
                transcript=_build_speaking_transcript(session),
            )
            result = await self._ai_service.generate_response(
                user_message=prompt, system_prompt=SPEAKING_ANALYSIS_PROMPT
            )
            feedback = _GeneratedSpeakingFeedback.model_validate(parse_json_object(result.text))
        except (ValueError, ValidationError) as exc:
            logger.warning("Speaking feedback was not valid JSON/schema: %s", type(exc).__name__)
        except Exception as exc:  # noqa: BLE001 - optional enrichment must never break completion
            logger.warning("Speaking feedback unavailable: %s", type(exc).__name__)

        return compose_voice_summary(aggregate, feedback)


# Module-level singleton, matching the project's existing pattern.
speaking_analysis_service = SpeakingAnalysisService()


# Public names for other features (e.g. the interview simulator) that reuse the
# Step 8 blending and prompt-formatting rather than reimplementing them.
blend_scores = _blend
format_metrics_for_prompt = _format_metrics_for_prompt
