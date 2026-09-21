"""
Interview session document shapes (documentation for the `interview_sessions`
collection — MongoDB itself is schemaless).

One document per interview. Questions, answers and evaluations are embedded,
so there is no separate answers collection.

    {
      _id, user_id (ObjectId), interview_type, difficulty, mode,
      question_count, current_question_number, status,
      reveal_feedback, topic_plan, version,
      started_at, updated_at, completed_at, abandoned_at,
      questions: [InterviewQuestionDocument],
      final_evaluation: dict | None
    }
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, NotRequired, TypedDict


class AnswerRecord(TypedDict):
    """One answered prompt — used for the main question and each follow-up."""

    answer: str | None
    answer_input_type: Literal["text", "voice"]
    answered_at: datetime | None
    # Step 8 metrics for spoken answers (reuses analysis_service).
    voice_analysis: NotRequired[dict | None]
    technical_evaluation: dict | None
    communication_evaluation: dict | None
    improved_answer: str | None
    # Never returned to clients (e.g. what the evaluator thought was worth probing).
    internal: NotRequired[dict]


class FollowUpDocument(AnswerRecord):
    question: str
    asked_at: datetime


class InterviewQuestionDocument(AnswerRecord):
    question_number: int
    question: str
    topic: str
    focus: str
    asked_at: datetime
    follow_up_questions: list[FollowUpDocument]
