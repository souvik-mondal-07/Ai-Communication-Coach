"""
Interview question service.

Plans which topic each question covers, generates questions and follow-ups
through the existing `AIService` (never a second Gemini client), and prevents
repeats within an interview.

    interview_service -> QuestionService -> AIService -> Gemini
"""

from __future__ import annotations

import random
import re

from pydantic import BaseModel, Field, field_validator

from app.services.ai.ai_service import AIService, ai_service
from app.services.interview import prompts
from app.services.interview.structured_ai import StructuredOutputError, generate_validated
from app.services.interview.topics import (
    HR_OPENER_FOCUS,
    MIXED_HR_SHARE,
    MIXED_SCENARIO_SHARE,
    TOPICS,
    TYPE_TOPICS,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_GENERATION_ATTEMPTS = 3


class QuestionGenerationError(Exception):
    """A usable, non-duplicate question could not be generated."""


class GeneratedQuestion(BaseModel):
    """Validated shape of a question/follow-up returned by the AI."""

    question: str = Field(min_length=8, max_length=600)

    @field_validator("question")
    @classmethod
    def clean(cls, value: str) -> str:
        return " ".join(value.split())


# --- Duplicate detection ------------------------------------------------------


_FILLER_WORDS = frozenset(
    """what is are was were the a an of and or to in on for how does do did can could
    would should you your explain describe tell me about between difference differences
    vs versus with by it its this that these those which who why when where as at be
    from have has we our i my give example examples walk through please briefly s""".split()
)

# Reworded questions about the same things share almost all their content words.
CONTENT_OVERLAP_THRESHOLD = 0.75


def normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


def _content_tokens(text: str) -> set[str]:
    return {t for t in normalize_question(text).split() if t not in _FILLER_WORDS}


def is_duplicate(candidate: str, previous: list[str]) -> bool:
    """
    True if `candidate` repeats an earlier question — exactly, or reworded
    ("difference between IDS and IPS" vs "explain IDS vs IPS").

    Deliberately compares *content words*, not raw text: templated questions
    about different subjects ("...between TCP and UDP" / "...between IDS and
    IPS") look alike as strings but are different questions.
    """
    norm = normalize_question(candidate)
    tokens = _content_tokens(candidate)
    for other in previous:
        other_norm = normalize_question(other)
        if norm == other_norm:
            return True
        other_tokens = _content_tokens(other)
        shared = tokens & other_tokens
        union = tokens | other_tokens
        if len(shared) >= 2 and union and len(shared) / len(union) >= CONTENT_OVERLAP_THRESHOLD:
            return True
    return False


# --- Planning -----------------------------------------------------------------


def _topic_sequence(interview_type: str, count: int, rng: random.Random) -> list[str]:
    def cycle(pool: tuple[str, ...], n: int) -> list[str]:
        """n topics from `pool`, every topic used before any repeats, no back-to-back repeats."""
        out: list[str] = []
        while len(out) < n:
            batch = list(pool)
            rng.shuffle(batch)
            if out and len(batch) > 1 and batch[0] == out[-1]:
                batch[0], batch[1] = batch[1], batch[0]
            out.extend(batch)
        return out[:n]

    if interview_type != "mixed":
        return cycle(TYPE_TOPICS[interview_type], count)

    n_hr = max(1, round(count * MIXED_HR_SHARE))
    n_scenario = max(1, round(count * MIXED_SCENARIO_SHARE))
    n_technical = max(0, count - n_hr - n_scenario)
    technical = cycle(TYPE_TOPICS["cybersecurity"], n_technical)
    rest = ["hr"] * (n_hr - 1) + ["scenario_based"] * n_scenario + technical
    rng.shuffle(rest)
    return ["hr"] + rest  # a real interview opens with the HR introduction


def plan_questions(
    interview_type: str, question_count: int, rng: random.Random | None = None
) -> list[dict]:
    """
    Decide the topic and focus subject of every question up front, spreading
    focus areas so an interview doesn't circle the same subject.
    """
    rng = rng or random.Random()
    topics = _topic_sequence(interview_type, question_count, rng)

    remaining: dict[str, list[str]] = {}
    plan: list[dict] = []
    for topic_id in topics:
        pool = remaining.get(topic_id)
        if not pool:
            pool = list(TOPICS[topic_id].focus_areas)
            rng.shuffle(pool)
            if topic_id == "hr" and HR_OPENER_FOCUS in pool:
                # A real interview opens with "Tell me about yourself": put the
                # opener last so `pop()` hands it out first (and only once per cycle).
                pool.remove(HR_OPENER_FOCUS)
                pool.append(HR_OPENER_FOCUS)
            remaining[topic_id] = pool
        plan.append({"topic": topic_id, "focus": pool.pop()})
    return plan


def performance_hint(technical_scores: list[int]) -> str:
    """Tell the generator how the candidate is doing so difficulty can adapt."""
    if not technical_scores:
        return "no answers yet — start at the stated difficulty"
    recent = technical_scores[-3:]
    average = round(sum(recent) / len(recent))
    if average >= 75:
        return (
            f"strong (recent technical average {average}/100) — a slightly more "
            "demanding question within this difficulty level is appropriate"
        )
    if average < 45:
        return (
            f"struggling (recent technical average {average}/100) — choose a "
            "slightly more accessible angle within this difficulty level"
        )
    return f"steady (recent technical average {average}/100) — keep the stated difficulty"


# --- Service ------------------------------------------------------------------


class QuestionService:
    """Generates interview questions and follow-ups via the existing AIService."""

    def __init__(self, ai_service_: AIService = ai_service) -> None:
        self._ai_service = ai_service_

    async def _generate_unique(
        self, build_prompt, *, previous: list[str]
    ) -> str:
        """Generate a question that is not a duplicate of anything in `previous`."""
        avoid_note = ""
        for _ in range(MAX_GENERATION_ATTEMPTS):
            try:
                generated = await generate_validated(
                    self._ai_service,
                    user_prompt=build_prompt(avoid_note),
                    system_prompt=prompts.INTERVIEW_SYSTEM_PROMPT,
                    model=GeneratedQuestion,
                )
            except StructuredOutputError as exc:
                raise QuestionGenerationError("AI returned an unusable question.") from exc
            if not is_duplicate(generated.question, previous):
                return generated.question
            avoid_note = (
                "Your previous attempt was too similar to an earlier question. "
                "Ask about a clearly different aspect of the subject."
            )
        raise QuestionGenerationError("Could not generate a non-repeating question.")

    async def generate_question(
        self,
        *,
        interview_type: str,
        difficulty: str,
        mode: str,
        question_number: int,
        total_questions: int,
        topic: str,
        focus: str,
        previous_questions: list[str],
        recent_answers: list[tuple[str, str]],
        technical_scores: list[int],
    ) -> str:
        performance = performance_hint(technical_scores)
        return await self._generate_unique(
            lambda avoid_note: prompts.build_question_prompt(
                interview_type=interview_type,
                difficulty=difficulty,
                question_number=question_number,
                total_questions=total_questions,
                topic=topic,
                focus=focus,
                previous_questions=previous_questions,
                recent_answers=recent_answers,
                performance=performance,
                voice=mode == "voice",
                avoid_note=avoid_note,
            ),
            previous=previous_questions,
        )

    async def generate_follow_up(
        self,
        *,
        interview_type: str,
        difficulty: str,
        mode: str,
        topic: str,
        question: str,
        answer: str,
        focus: str,
        previous_follow_ups: list[str],
        all_previous_questions: list[str],
    ) -> str:
        return await self._generate_unique(
            lambda avoid_note: prompts.build_follow_up_prompt(
                interview_type=interview_type,
                difficulty=difficulty,
                topic=topic,
                question=question,
                answer=answer,
                focus=focus,
                previous_follow_ups=previous_follow_ups,
                voice=mode == "voice",
                avoid_note=avoid_note,
            ),
            previous=all_previous_questions,
        )


question_service = QuestionService()
