"""
DSA schemas (Phase 24).

`QuestionContent` is the stored shape, validated before anything enters the bank. `PublicQuestion`
deliberately has no answer, explanation, trace, complexity or reference-solution field, so none of
those can leak before submission even by accident.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Difficulty = Literal["easy", "medium", "hard"]
QFormat = Literal["conceptual", "scenario", "output", "trace", "complexity", "coding"]
Interaction = Literal["mcq", "code"]
CodingType = Literal["fill_line", "fix_bug", "write_function"]
QuestionStatus = Literal["active", "inactive", "draft"]
SessionMode = Literal["topic", "interview", "tracing", "complexity", "coding", "timed_mock", "weak"]
SessionStatus = Literal["in_progress", "completed"]
ReviewStatus = Literal["reference_checked", "snippet_test_checked", "tests_checked", "manual_review", "unverified"]
Outcome = Literal["correct", "incorrect", "unanswered", "ungraded"]

MAX_QUESTIONS_PER_SESSION = 50
MAX_TIMER_MINUTES = 180
MAX_CODE_CHARS = 8000
_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,59}$"
QUESTION_ID_PATTERN = r"^dsa-[a-f0-9]{10}$"


class TestCase(BaseModel):
    __test__ = False  # not a pytest class

    label: str = Field(min_length=1, max_length=80)
    args: list[Any]
    expected: Any
    visible: bool = True
    edge: bool = False


class CodingSpec(BaseModel):
    function_name: str = Field(pattern=r"^[a-z_][a-z0-9_]{0,40}$")
    template: str = Field(min_length=10, max_length=2000)
    reference_solution: str = Field(min_length=20, max_length=4000)
    test_cases: list[TestCase] = Field(min_length=3, max_length=12)
    sample_io: str | None = Field(default=None, max_length=500)


class QuestionContent(BaseModel):
    question_id: str = Field(pattern=QUESTION_ID_PATTERN)
    topic_id: str = Field(pattern=_ID_PATTERN)
    subtopic_id: str = Field(pattern=_ID_PATTERN)
    format: QFormat
    interaction: Interaction = "mcq"
    coding_type: CodingType | None = None
    difficulty: Difficulty
    statement: str = Field(min_length=15, max_length=1800)
    code: str | None = Field(default=None, max_length=2500)
    options: list[str] = Field(default_factory=list, max_length=4)
    correct_index: int | None = Field(default=None, ge=0, le=3)
    explanation: str = Field(min_length=10, max_length=2500)
    complexity: dict[str, str] | None = None
    trace: list[dict[str, str]] | None = None
    constraints: str | None = Field(default=None, max_length=400)
    hints: list[str] = Field(default_factory=list, max_length=3)
    coding: CodingSpec | None = None
    est_time_seconds: int = Field(ge=10, le=1800)
    status: QuestionStatus = "active"
    version: int = Field(default=1, ge=1)
    source: Literal["seed", "generated", "imported"] = "seed"
    review_status: ReviewStatus = "unverified"
    verification: dict[str, Any] | None = None

    @field_validator("options")
    @classmethod
    def _options_text(cls, value: list[str]) -> list[str]:
        for option in value:
            if not isinstance(option, str) or not option.strip() or len(option) > 220:
                raise ValueError("each option must be 1-220 characters")
        return value

    @model_validator(mode="after")
    def _shape(self) -> "QuestionContent":
        if self.interaction == "mcq":
            if len(self.options) != 4 or self.correct_index is None:
                raise ValueError("an MCQ needs exactly four options and a correct_index")
            if self.coding is not None:
                raise ValueError("an MCQ cannot carry a coding spec")
        else:
            if self.options or self.correct_index is not None:
                raise ValueError("a code question has no options or correct_index")
            if self.coding is None or self.coding_type != "write_function":
                raise ValueError("a code question needs a coding spec and coding_type 'write_function'")
        if (self.format == "coding") != (self.coding_type is not None):
            raise ValueError("coding_type is required for (and only for) coding-format questions")
        if self.format == "trace" and not self.trace:
            raise ValueError("trace questions need trace steps")
        for step in self.trace or []:
            if set(step) != {"label", "state"}:
                raise ValueError("each trace step needs exactly 'label' and 'state'")
        return self


# --- Public (answer-free) models --------------------------------------------------------------


class PublicTest(BaseModel):
    label: str
    args: list[Any]
    expected: Any


class PublicCoding(BaseModel):
    function_name: str
    template: str
    sample_io: str | None = None
    visible_tests: list[PublicTest]
    hidden_test_count: int


class PublicQuestion(BaseModel):
    question_id: str
    topic_id: str
    subtopic_id: str
    format: QFormat
    interaction: Interaction
    coding_type: CodingType | None = None
    difficulty: Difficulty
    statement: str
    code: str | None = None
    options: list[str]
    constraints: str | None = None
    est_time_seconds: int
    coding: PublicCoding | None = None


class QuestionListResponse(BaseModel):
    items: list[PublicQuestion]
    page: int
    limit: int
    total: int
    has_next: bool


# --- Sessions ---------------------------------------------------------------------------------


class SessionCreateRequest(BaseModel):
    mode: SessionMode
    topic_ids: list[str] = Field(default_factory=list, max_length=10)
    subtopic_ids: list[str] = Field(default_factory=list, max_length=60)
    difficulty: Difficulty | None = None
    question_count: int = Field(default=10, ge=1, le=MAX_QUESTIONS_PER_SESSION)
    timer_minutes: int | None = Field(default=None, ge=1, le=MAX_TIMER_MINUTES)
    immediate_feedback: bool | None = None

    @field_validator("topic_ids", "subtopic_ids")
    @classmethod
    def _ids(cls, value: list[str]) -> list[str]:
        for item in value:
            if not re.match(_ID_PATTERN, item):
                raise ValueError("invalid identifier")
        return list(dict.fromkeys(value))


class AnswerRequest(BaseModel):
    """Only a displayed option position (MCQ) or submitted code text is trusted -- never a correctness flag or score."""

    selected_index: int | None = Field(default=None, ge=0, le=3)
    code: str | None = Field(default=None, max_length=MAX_CODE_CHARS)
    marked_for_review: bool = False
    reveal: bool = False  # code questions in practice sessions only: lock the answer and show the reference solution
    time_spent_seconds: int = Field(default=0, ge=0, le=3600)


class SelfAssessmentRequest(BaseModel):
    verdict: Literal["passed", "failed", "partial"]


class SessionQuestion(PublicQuestion):
    selected_index: int | None = None
    code_answer: str | None = None
    marked_for_review: bool = False
    locked: bool = False
    hints: list[str] = Field(default_factory=list)
    feedback: dict[str, Any] | None = None


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
    format: QFormat
    interaction: Interaction
    coding_type: CodingType | None = None
    difficulty: Difficulty
    statement: str
    code: str | None = None
    options: list[str]
    selected_index: int | None
    correct_index: int | None
    code_answer: str | None = None
    outcome: Outcome
    explanation: str
    complexity: dict[str, str] | None = None
    trace: list[dict[str, str]] | None = None
    reference_solution: str | None = None
    test_cases: list[dict[str, Any]] | None = None
    self_assessment: str | None = None
    execution_note: str | None = None
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
    graded_questions: int
    ungraded_questions: int
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
    complexity_summary: list[dict[str, Any]]
    questions: list[ResultQuestion]
    scoring_policy: str
