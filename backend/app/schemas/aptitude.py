"""
Aptitude schemas (Phase 23).

Two families live here:
  * the *stored* question shape (`QuestionContent`), validated before anything enters the bank;
  * request/response models. `PublicQuestion` deliberately has no answer, explanation or formula
    field, so an answer cannot leak before submission even by accident.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Difficulty = Literal["easy", "medium", "hard"]
QuestionType = Literal["direct", "scenario", "multi_step", "data_interpretation", "time_pressure"]
QuestionStatus = Literal["active", "inactive", "draft"]
SessionMode = Literal["topic", "scenario", "timed_mock", "mixed", "weak"]
SessionStatus = Literal["in_progress", "completed"]
ReviewStatus = Literal["verified", "manual_review", "unverified"]

MAX_QUESTIONS_PER_SESSION = 60
MAX_TIMER_MINUTES = 180
MAX_ID_LENGTH = 60
_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,59}$"


class QuestionContent(BaseModel):
    """What a question looks like in the bank. Used to validate seeds and any imported candidates."""

    question_id: str = Field(pattern=r"^apt-[a-f0-9]{10}$")
    topic_id: str = Field(pattern=_ID_PATTERN)
    subtopic_id: str = Field(pattern=_ID_PATTERN)
    question_type: QuestionType
    difficulty: Difficulty
    statement: str = Field(min_length=15, max_length=1500)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=10, max_length=2000)
    formula: str | None = Field(default=None, max_length=400)
    est_time_seconds: int = Field(ge=10, le=600)
    data: dict[str, Any] | None = None
    status: QuestionStatus = "active"
    version: int = Field(default=1, ge=1)
    source: Literal["seed", "generated", "imported"] = "seed"
    review_status: ReviewStatus = "unverified"
    verification: dict[str, Any] | None = None

    @field_validator("options")
    @classmethod
    def _options_text(cls, value: list[str]) -> list[str]:
        for option in value:
            if not isinstance(option, str) or not option.strip() or len(option) > 200:
                raise ValueError("each option must be 1-200 characters")
        return value


# --- Public (answer-free) models --------------------------------------------------------------


class PublicQuestion(BaseModel):
    question_id: str
    topic_id: str
    subtopic_id: str
    question_type: QuestionType
    difficulty: Difficulty
    statement: str
    options: list[str]
    est_time_seconds: int
    data: dict[str, Any] | None = None


class QuestionListResponse(BaseModel):
    items: list[PublicQuestion]
    page: int
    limit: int
    total: int
    has_next: bool


# --- Sessions ---------------------------------------------------------------------------------


class SessionCreateRequest(BaseModel):
    mode: SessionMode
    topic_ids: list[str] = Field(default_factory=list, max_length=26)
    subtopic_ids: list[str] = Field(default_factory=list, max_length=40)
    difficulty: Difficulty | None = None
    question_count: int = Field(default=10, ge=1, le=MAX_QUESTIONS_PER_SESSION)
    timer_minutes: int | None = Field(default=None, ge=1, le=MAX_TIMER_MINUTES)
    immediate_feedback: bool | None = None

    @field_validator("topic_ids", "subtopic_ids")
    @classmethod
    def _ids(cls, value: list[str]) -> list[str]:
        import re

        for item in value:
            if not re.match(_ID_PATTERN, item):
                raise ValueError("invalid identifier")
        return list(dict.fromkeys(value))


class AnswerRequest(BaseModel):
    """Only the displayed position is trusted as input -- never a correctness flag or a score."""

    selected_index: int | None = Field(default=None, ge=0, le=3)
    marked_for_review: bool = False
    time_spent_seconds: int = Field(default=0, ge=0, le=3600)


class SessionQuestion(PublicQuestion):
    selected_index: int | None = None
    marked_for_review: bool = False
    locked: bool = False
    feedback: dict[str, Any] | None = None  # only present for immediate-feedback sessions once answered


class SessionOut(BaseModel):
    session_id: str
    mode: SessionMode
    status: SessionStatus
    difficulty: Difficulty | None = None
    question_count: int
    requested_count: int
    topic_ids: list[str]
    immediate_feedback: bool
    exam_mode: bool
    started_at: datetime
    expires_at: datetime | None = None
    server_time: datetime
    remaining_seconds: int | None = None
    timer_minutes: int | None = None
    questions: list[SessionQuestion]
    scoring_policy: str


class ResultQuestion(BaseModel):
    question_id: str
    topic_id: str
    subtopic_id: str
    difficulty: Difficulty
    statement: str
    options: list[str]
    data: dict[str, Any] | None = None
    selected_index: int | None
    correct_index: int
    outcome: Literal["correct", "incorrect", "unanswered"]
    explanation: str
    formula: str | None = None
    marked_for_review: bool = False
    time_spent_seconds: int = 0


class TopicPerformance(BaseModel):
    topic_id: str
    topic_title: str
    total: int
    correct: int
    incorrect: int
    unanswered: int
    accuracy: float


class ResultOut(BaseModel):
    session_id: str
    mode: SessionMode
    status: SessionStatus
    total_questions: int
    correct: int
    incorrect: int
    unanswered: int
    score: int
    accuracy: float
    time_taken_seconds: int
    average_seconds_per_question: float
    auto_submitted: bool
    started_at: datetime
    finished_at: datetime | None
    topic_performance: list[TopicPerformance]
    revision_topics: list[dict[str, Any]]
    questions: list[ResultQuestion]
    scoring_policy: str
