"""
Cybersecurity learning/practice request and response schemas.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Difficulty = Literal["beginner", "intermediate", "advanced"]
# Step 17 widened the question types; Step 5 clients only ever see the first two.
QuestionType = Literal["multiple_choice", "short_answer", "scenario", "troubleshooting", "command"]
PracticeMode = Literal[
    "personalized", "topic", "random", "weakness", "scenario", "troubleshooting", "interview"
]
PracticeDifficulty = Literal["beginner", "intermediate", "advanced", "adaptive"]
QuestionTypeChoice = Literal[
    "mixed", "multiple_choice", "short_answer", "scenario", "troubleshooting", "command"
]

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
    # Step 17 (all optional; Step 5 sessions leave them empty)
    raw_score: int | None = None
    hints_used: int = 0
    hint_penalty: int = 0
    dimension_scores: dict[str, int] | None = None
    strengths: list[str] = Field(default_factory=list)
    improvement: str | None = None
    explanation: str | None = None
    ideal_steps: list[str] | None = None
    revealed: bool = False


class RecommendedNext(BaseModel):
    """Step 16's top practice recommendation (or, failing that, this session's weakest topic)."""

    title: str
    topic: str | None = None
    topic_slug: str | None = None
    difficulty: Difficulty | None = None
    reasons: list[str] = Field(default_factory=list)
    basis: str | None = None
    source: Literal["personalization", "session"] = "personalization"


class PracticeCompleteData(BaseModel):
    session_id: str
    score: int = Field(ge=0, le=100)
    questions_answered: int
    correct_answers: int
    topic_title: str
    category: str
    weak_areas: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    # Step 17 summary (all optional; absent for Step 5 sessions)
    mode: str | None = None
    scored: bool = True
    questions_total: int | None = None
    needs_improvement: int | None = None
    hints_used: int | None = None
    categories: list[str] = Field(default_factory=list)
    difficulty: Difficulty | None = None
    difficulty_mode: Literal["fixed", "adaptive"] | None = None
    strong_areas: list[str] = Field(default_factory=list)
    needs_work: list[str] = Field(default_factory=list)
    recommended_next: RecommendedNext | None = None
    duration_seconds: int | None = None
    timed_out: bool = False
    unanswered: int | None = None


class PracticeHistoryItem(BaseModel):
    session_id: str
    topic_slug: str
    topic_title: str
    category: str
    difficulty: Difficulty
    status: Literal["in_progress", "completed"]
    score: int | None = None
    questions_answered: int
    mode: str | None = None
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


# --- Step 17: advanced practice sessions ---------------------------------------

MAX_CATEGORY_LENGTH = 80
MIN_TIME_LIMIT_MINUTES = 5
MAX_TIME_LIMIT_MINUTES = 60


class PracticeSessionCreate(BaseModel):
    """
    Session configuration. The owner always comes from the JWT; there is deliberately
    no user id here. Cross-field rules (a category for topic practice, question types a
    category supports) are enforced by the engine against the live topic catalogue.
    """

    mode: PracticeMode = "personalized"
    category: str | None = Field(default=None, max_length=MAX_CATEGORY_LENGTH)
    topic_slug: str | None = Field(default=None, max_length=200)
    difficulty: PracticeDifficulty = "adaptive"
    question_type: QuestionTypeChoice = "mixed"
    question_count: int = Field(
        default=DEFAULT_QUESTION_COUNT, ge=MIN_QUESTION_COUNT, le=MAX_QUESTION_COUNT
    )
    time_limit_minutes: int | None = Field(
        default=None, ge=MIN_TIME_LIMIT_MINUTES, le=MAX_TIME_LIMIT_MINUTES
    )

    @field_validator("category", "topic_slug")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None


class HintRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=200)
    # False -> the next hint (max 3). True -> the full explanation (needs >= 1 hint first);
    # it ends the question with a score of 0.
    reveal: bool = False
