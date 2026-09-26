"""
Pressure & Nervousness Training session document shapes (documentation for
the `pressure_sessions` collection -- MongoDB itself is schemaless).

This is a training system, NOT a medical or psychological diagnostic system.
Nothing here claims to diagnose anxiety, nervousness or any mental-health
condition -- only observable, approximate communication/performance
indicators (see `app.services.pressure.evaluation_service`).

Deliberately reuses the same question/follow-up/evaluation record shape as
`app.models.interview` (technical_evaluation, communication_evaluation,
answer, follow_up_questions, topic, question, question_number) so the
existing interview evaluation helpers (`question_scores`, `answered_records`,
`build_digest`, `build_final_evaluation`) work on a pressure session
unmodified -- the pressure system is a layer on top of the interview engine,
not a second implementation of it.

    {
      _id, user_id (ObjectId),
      pressure_level (1-5), mode ("interview" | "communication"),
      interview_type,            # topic pool + scoring weights (reuses Step 9)
      difficulty, input_mode, question_count,
      status, version,
      config: PressureConfigDocument,
      topic_plan, current_question_number,
      questions: [PressureQuestionDocument],
      self_reported_difficulty, self_report_note,
      final_evaluation: dict | None,
      started_at, updated_at, completed_at, abandoned_at,
    }
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, NotRequired, TypedDict


class PressureConfigDocument(TypedDict):
    """Server-computed configuration for one pressure level (never taken from the client)."""

    time_limit_seconds: int | None
    allow_hints: bool
    follow_up_frequency: float
    topic_switch_frequency: float
    difficulty_modifier: int
    interruption_frequency: float
    unexpected_question_frequency: float


class PressureCondition(TypedDict):
    """Which pressure condition (if any) was applied when this prompt was asked."""

    type: Literal[
        "none", "time_pressure", "topic_switch", "difficult_question", "ambiguous_question"
    ]
    time_limit_seconds: int | None
    topic_switched: bool
    difficulty_bumped: bool


class PressureAnswerRecord(TypedDict):
    """One answered prompt -- the main question or a rapid follow-up/interruption."""

    answer: str | None
    answer_input_type: Literal["text", "voice"]
    answered_at: datetime | None
    response_duration_seconds: float | None  # server-measured (asked_at -> answered_at)
    timed_out: bool
    # Step 8 metrics for spoken answers; text-mode indicators for typed ones.
    voice_analysis: NotRequired[dict | None]
    text_metrics: NotRequired[dict | None]
    technical_evaluation: dict | None
    communication_evaluation: dict | None
    improved_answer: str | None
    internal: NotRequired[dict]  # never returned to clients


class PressureFollowUpDocument(PressureAnswerRecord):
    question: str
    kind: Literal["rapid", "interruption", "technical"]
    asked_at: datetime


class PressureQuestionDocument(PressureAnswerRecord):
    question_number: int
    question: str
    topic: str
    focus: str
    condition: PressureCondition
    asked_at: datetime
    follow_up_questions: list[PressureFollowUpDocument]
