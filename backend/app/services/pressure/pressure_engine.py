"""
Pressure engine.

Pure, deterministic-given-its-inputs functions that decide *what pressure
condition applies next* -- rapid follow-up, interruption, topic switch, a
harder question, or none. Nothing here talks to Gemini or MongoDB: it only
returns decisions that `pressure_service.py` acts on (which then calls the
existing interview `QuestionService` / `InterviewEvaluationService` to do the
actual question generation and evaluation).

Interruptions are capped and never fire on the first question, so "used
sparingly" (per the spec) is enforced in code, not just by a low probability.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.services.interview.topics import TOPICS, TYPE_TOPICS
from app.services.pressure.pressure_config import PressureConfig
from app.services.pressure.prompts import INTERRUPTIONS, RAPID_FOLLOW_UPS

MAX_INTERRUPTIONS_PER_SESSION = 2
# Per question: at most this many rapid follow-ups/interruptions combined,
# so a question can never chain indefinitely.
MAX_FOLLOW_UPS_PER_QUESTION = 2
DIFFICULTY_ORDER = ("beginner", "intermediate", "advanced")

# A harder/shorter time limit for a bumped-difficulty question.
DIFFICULT_TIME_LIMIT_FACTOR = 0.75


def bump_difficulty(difficulty: str, levels: int) -> str:
    """Move `levels` steps up the difficulty ladder, capped at 'advanced'."""
    index = DIFFICULTY_ORDER.index(difficulty) if difficulty in DIFFICULTY_ORDER else 0
    return DIFFICULTY_ORDER[min(len(DIFFICULTY_ORDER) - 1, index + max(0, levels))]


def _topic_pool(interview_type: str) -> tuple[str, ...]:
    if interview_type == "mixed":
        return tuple(TOPICS.keys())
    return TYPE_TOPICS.get(interview_type, tuple(TOPICS.keys()))


def pick_topic_switch(*, interview_type: str, current_topic: str, rng: random.Random) -> str | None:
    """A different topic from the interview type's pool, or None if there isn't one."""
    pool = [t for t in _topic_pool(interview_type) if t != current_topic]
    if not pool:
        return None
    return rng.choice(pool)


def pick_focus(topic: str, rng: random.Random, exclude: list[str] | None = None) -> str:
    areas = list(TOPICS[topic].focus_areas)
    if exclude:
        remaining = [a for a in areas if a not in exclude]
        if remaining:
            areas = remaining
    return rng.choice(areas)


@dataclass(frozen=True)
class NextQuestionPlan:
    topic: str
    focus: str
    difficulty: str
    time_limit_seconds: int | None
    topic_switched: bool
    difficulty_bumped: bool

    @property
    def condition_type(self) -> str:
        if self.topic == "scenario_based":
            return "ambiguous_question"
        if self.difficulty_bumped:
            return "difficult_question"
        if self.topic_switched:
            return "topic_switch"
        if self.time_limit_seconds is not None:
            return "time_pressure"
        return "none"


def plan_next_question(
    *,
    config: PressureConfig,
    interview_type: str,
    difficulty: str,
    planned_topic: str,
    planned_focus: str,
    rng: random.Random,
) -> NextQuestionPlan:
    """
    Decide the topic/focus/difficulty/time-limit for the next main question.
    Starts from the plan (`planned_topic`/`planned_focus`, from
    `question_service.plan_questions`) and may override the topic (a
    "topic switch") or the difficulty (an "unexpected/difficult question").
    """
    topic = planned_topic
    focus = planned_focus
    switched = False
    if config.topic_switch_frequency > 0 and rng.random() < config.topic_switch_frequency:
        switched_topic = pick_topic_switch(interview_type=interview_type, current_topic=planned_topic, rng=rng)
        if switched_topic is not None:
            topic = switched_topic
            focus = pick_focus(topic, rng)
            switched = True

    bumped = False
    effective_difficulty = difficulty
    if config.difficulty_modifier > 0 and rng.random() < config.unexpected_question_frequency:
        effective_difficulty = bump_difficulty(difficulty, config.difficulty_modifier)
        bumped = effective_difficulty != difficulty

    time_limit = config.time_limit_seconds
    if bumped and time_limit is not None:
        time_limit = max(15, round(time_limit * DIFFICULT_TIME_LIMIT_FACTOR))

    return NextQuestionPlan(
        topic=topic,
        focus=focus,
        difficulty=effective_difficulty,
        time_limit_seconds=time_limit,
        topic_switched=switched,
        difficulty_bumped=bumped,
    )


def roll_interruption(
    *, config: PressureConfig, question_number: int, interruptions_used: int, rng: random.Random
) -> str | None:
    """An interruption line, or None. Never on question 1; capped per session."""
    if question_number <= 1:
        return None
    if interruptions_used >= MAX_INTERRUPTIONS_PER_SESSION:
        return None
    if config.interruption_frequency <= 0 or rng.random() >= config.interruption_frequency:
        return None
    return rng.choice(INTERRUPTIONS)


def roll_rapid_follow_up(
    *, config: PressureConfig, used_follow_ups: list[str], rng: random.Random
) -> str | None:
    """A rapid follow-up line, or None. Avoids repeating one already used in this session."""
    if config.follow_up_frequency <= 0 or rng.random() >= config.follow_up_frequency:
        return None
    remaining = [f for f in RAPID_FOLLOW_UPS if f not in used_follow_ups]
    pool = remaining or list(RAPID_FOLLOW_UPS)
    return rng.choice(pool)
