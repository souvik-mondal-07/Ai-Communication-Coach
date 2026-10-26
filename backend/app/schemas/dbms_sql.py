"""
DBMS & SQL Interview Lab schemas (Phase 25).

`QuestionContent` is the stored shape, validated before anything enters the bank. Public (answer-free) shapes are built by
`bank.to_public` from an explicit whitelist, so no answer key, explanation, reference query or expected row can leak
before submission even by accident.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Difficulty = Literal["easy", "medium", "hard"]
QFormat = Literal["concept", "scenario", "output", "debug", "complete", "query", "design", "transaction"]
Interaction = Literal["mcq", "short", "sql"]
Dialect = Literal["standard", "sqlite", "mysql", "postgresql", "oracle", "sqlserver", "mongodb", "dynamodb"]
AnswerKind = Literal["attrs", "keys", "number"]
QuestionStatus = Literal["active", "inactive", "draft"]
SessionMode = Literal[
    "topic", "mixed", "interview", "sql_lab", "predict_output", "debug", "complete",
    "design_lab", "transaction_lab", "nosql_lab", "timed_mock", "weak",
]
SessionStatus = Literal["in_progress", "completed"]
ReviewStatus = Literal["reference_checked", "sql_checked", "sql_output_checked", "manual_review", "unverified"]
Outcome = Literal["correct", "incorrect", "unanswered"]

MAX_QUESTIONS_PER_SESSION = 50
MAX_TIMER_MINUTES = 180
MAX_SQL_CHARS = 4000
MAX_SHORT_CHARS = 200
_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,59}$"
QUESTION_ID_PATTERN = r"^dbq-[a-f0-9]{10}$"


class ExpectedResult(BaseModel):
    columns: list[str] = Field(min_length=1, max_length=20)
    rows: list[list[Any]] = Field(max_length=200)


class SqlSpec(BaseModel):
    dataset_id: str = Field(pattern=_ID_PATTERN)
    starter: str | None = Field(default=None, max_length=1500)
    reference_sql: str = Field(min_length=10, max_length=1500)
    expected: ExpectedResult
    ordered: bool = False
    check_column_names: bool = False
    precision: int = Field(default=2, ge=0, le=6)


class ShortSpec(BaseModel):
    kind: AnswerKind
    value: list[str] | float
    help: str = Field(min_length=5, max_length=200)


class QuestionContent(BaseModel):
    question_id: str = Field(pattern=QUESTION_ID_PATTERN)
    unit_id: str = Field(pattern=_ID_PATTERN)
    topic_id: str = Field(pattern=_ID_PATTERN)
    format: QFormat
    interaction: Interaction = "mcq"
    dialect: Dialect = "standard"
    difficulty: Difficulty
    statement: str = Field(min_length=15, max_length=1500)
    code: str | None = Field(default=None, max_length=2000)
    dataset_id: str | None = Field(default=None, pattern=_ID_PATTERN)
    options: list[str] = Field(default_factory=list, max_length=4)
    correct_index: int | None = Field(default=None, ge=0, le=3)
    short: ShortSpec | None = None
    sql: SqlSpec | None = None
    explanation: str = Field(min_length=10, max_length=2500)
    hints: list[str] = Field(default_factory=list, max_length=3)
    est_time_seconds: int = Field(ge=10, le=1800)
    tags: list[str] = Field(default_factory=list, max_length=6)
    requires: list[str] = Field(default_factory=list, max_length=3)
    status: QuestionStatus = "active"
    version: int = Field(default=1, ge=1)
    source: Literal["seed", "generated", "imported"] = "seed"
    review_status: ReviewStatus = "unverified"
    verification: dict[str, Any] | None = None

    @field_validator("options")
    @classmethod
    def _options_text(cls, value: list[str]) -> list[str]:
        for option in value:
            if not isinstance(option, str) or not option.strip() or len(option) > 240:
                raise ValueError("each option must be 1-240 characters")
        return value

    @field_validator("hints")
    @classmethod
    def _hints_text(cls, value: list[str]) -> list[str]:
        for hint in value:
            if not hint.strip() or len(hint) > 300:
                raise ValueError("each hint must be 1-300 characters")
        return value

    @model_validator(mode="after")
    def _shape(self) -> "QuestionContent":
        if self.interaction == "mcq":
            if len(self.options) != 4 or self.correct_index is None:
                raise ValueError("an MCQ needs exactly four options and a correct_index")
            if self.short is not None or self.sql is not None:
                raise ValueError("an MCQ cannot carry a short or sql spec")
        elif self.interaction == "short":
            if self.short is None or self.options or self.correct_index is not None or self.sql is not None:
                raise ValueError("a short-answer question needs only a short spec")
        else:
            if self.sql is None or self.options or self.correct_index is not None or self.short is not None:
                raise ValueError("a SQL question needs only a sql spec")
            if self.dataset_id != self.sql.dataset_id:
                raise ValueError("dataset_id must match the sql spec's dataset")
            if self.format not in ("query", "debug", "complete", "output"):
                raise ValueError("SQL questions use the query, debug, complete or output format")
        return self


# --- Requests --------------------------------------------------------------------------------


class SessionCreateRequest(BaseModel):
    mode: SessionMode
    unit_ids: list[str] = Field(default_factory=list, max_length=7)
    topic_ids: list[str] = Field(default_factory=list, max_length=70)
    difficulty: Difficulty | None = None
    question_count: int = Field(default=10, ge=1, le=MAX_QUESTIONS_PER_SESSION)
    timer_minutes: int | None = Field(default=None, ge=1, le=MAX_TIMER_MINUTES)
    immediate_feedback: bool | None = None

    @field_validator("unit_ids", "topic_ids")
    @classmethod
    def _ids(cls, value: list[str]) -> list[str]:
        for item in value:
            if not re.match(_ID_PATTERN, item):
                raise ValueError("invalid identifier")
        return list(dict.fromkeys(value))


class AnswerRequest(BaseModel):
    """Only a displayed option position, short text or SQL text is trusted -- never a correctness flag or score."""

    selected_index: int | None = Field(default=None, ge=0, le=3)
    text: str | None = Field(default=None, max_length=MAX_SHORT_CHARS)
    sql: str | None = Field(default=None, max_length=MAX_SQL_CHARS)
    marked_for_review: bool = False
    time_spent_seconds: int = Field(default=0, ge=0, le=3600)


class CheckRequest(BaseModel):
    text: str | None = Field(default=None, max_length=MAX_SHORT_CHARS)
    sql: str | None = Field(default=None, max_length=MAX_SQL_CHARS)
    time_spent_seconds: int = Field(default=0, ge=0, le=3600)


class SandboxRunRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=MAX_SQL_CHARS)
    dataset_id: str = Field(default="practice", pattern=_ID_PATTERN)
