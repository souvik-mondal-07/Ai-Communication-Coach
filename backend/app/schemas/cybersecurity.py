"""
Cybersecurity learning/practice request and response schemas.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Difficulty = Literal["beginner", "intermediate", "advanced"]
QuestionType = Literal["multiple_choice", "short_answer"]

MAX_ANSWER_LENGTH = 5_000
MIN_QUESTION_COUNT = 1
MAX_QUESTION_COUNT = 10
DEFAULT_QUESTION_COUNT = 5


class TopicSummary(BaseModel):
    """Lightweight representation used in the topic listing endpoint."""

    slug: str
    title: str
    category: str
    difficulty: Difficulty
    description: str
    practice_enabled: bool


class TopicDetail(TopicSummary):
    """Full topic representation, including learning content."""

    learning_objectives: list[str] = Field(default_factory=list)
    content: str
    examples: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)


class PracticeStartRequest(BaseModel):
    topic_slug: str = Field(min_length=1, max_length=200)
    difficulty: Difficulty | None = None
    question_count: int = Field(
        default=DEFAULT_QUESTION_COUNT, ge=MIN_QUESTION_COUNT, le=MAX_QUESTION_COUNT
    )


class PublicQuestion(BaseModel):
    """
    Question shape sent to the client. Deliberately excludes the correct
    answer/explanation/ideal answer — those only exist server-side until
    the question is answered.
    """

    question_id: str
    question: str
    type: QuestionType
    options: list[str] | None = None


class PracticeStartData(BaseModel):
    session_id: str
    topic_slug: str
    topic_title: str
    difficulty: Difficulty
    questions: list[PublicQuestion]


class AnswerSubmitRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=MAX_ANSWER_LENGTH)

    @field_validator("answer")
    @classmethod
    def answer_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Answer cannot be blank")
        return value


class AnswerResultData(BaseModel):
    score: int = Field(ge=0, le=100)
    correct: bool
    feedback: str
    ideal_answer: str | None = None
    missing_points: list[str] = Field(default_factory=list)


class PracticeCompleteData(BaseModel):
    session_id: str
    score: int = Field(ge=0, le=100)
    questions_answered: int
    correct_answers: int
    topic_title: str
    category: str
    weak_areas: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class PracticeHistoryItem(BaseModel):
    session_id: str
    topic_slug: str
    topic_title: str
    category: str
    difficulty: Difficulty
    status: Literal["in_progress", "completed"]
    score: int | None = None
    questions_answered: int
    started_at: str
    completed_at: str | None = None


class PracticeHistoryData(BaseModel):
    sessions: list[PracticeHistoryItem]
    page: int
    limit: int
    total: int


class ProgressCategoryData(BaseModel):
    category: str
    average_score: int
    attempts: int
    status: Literal["weak", "developing", "strong"]


class ProgressData(BaseModel):
    categories: list[ProgressCategoryData]
    weak_categories: list[str]
