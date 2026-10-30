"""
Python Interview Practice schemas (Phase 26).

`QuestionContent` is the stored shape, validated before anything enters the bank. Client-facing shapes are built by
`bank.to_public` from an explicit whitelist, so no answer key, explanation, reference solution, hidden test or expected value can
leak before it is earned.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Difficulty = Literal["easy", "medium", "hard"]
QFormat = Literal["concept", "output", "trace", "debug", "complete", "coding", "complexity", "scenario"]
Interaction = Literal["mcq", "short", "code"]
QuestionStatus = Literal["active", "inactive", "draft"]
SessionMode = Literal["topic", "mixed", "interview", "predict_output", "trace", "debug", "complete", "coding", "complexity", "oop", "advanced", "security", "timed_mock", "weak"]
ReviewStatus = Literal["execution_verified", "reference_verified", "manual_review", "unverified"]
CodeMode = Literal["function", "class", "stdio"]
CompareName = Literal["exact", "unordered", "set_like", "float", "text", "validator"]

MAX_QUESTIONS_PER_SESSION = 40
MAX_TIMER_MINUTES = 180
MAX_CODE_CHARS = 10_000
MAX_SHORT_CHARS = 400
_ID = r"^[a-z0-9][a-z0-9-]{0,59}$"
QUESTION_ID_PATTERN = r"^pyq-[a-f0-9]{10}$"


class CodeTest(BaseModel):
    id: int = Field(ge=0, le=59)
    label: str = Field(min_length=1, max_length=60)
    visible: bool = False
    args: list[Any] = Field(default_factory=list)  # JSON-safe inputs (function mode)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    ctor: list[Any] = Field(default_factory=list)  # class mode
    ops: list[list[Any]] = Field(default_factory=list)
    stdin: str | None = Field(default=None, max_length=2000)
    expected: Any = None  # canonical tagged JSON, produced by the reference solution
    input_repr: str = Field(default="", max_length=300)  # how the input is shown for visible tests


class CodeSpec(BaseModel):
    mode: CodeMode = "function"
    entry: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,40}$")
    signature: str = Field(min_length=3, max_length=200)
    starter: str = Field(min_length=1, max_length=2500)
    constraints: list[str] = Field(default_factory=list, max_length=6)
    compare: CompareName = "exact"
    tolerance: float | None = Field(default=None, ge=0, le=1)
    strict_types: bool = False
    validator: str | None = Field(default=None, max_length=60)
    tests: list[CodeTest] = Field(min_length=4, max_length=40)
    reference_source: str = Field(min_length=10, max_length=4000)
    time_complexity: str = Field(min_length=2, max_length=60)
    space_complexity: str = Field(min_length=2, max_length=60)

    @model_validator(mode="after")
    def _tests(self) -> "CodeSpec":
        ids = [t.id for t in self.tests]
        if len(set(ids)) != len(ids):
            raise ValueError("test ids must be unique")
        if not any(t.visible for t in self.tests) or all(t.visible for t in self.tests):
            raise ValueError("a coding problem needs both visible and hidden tests")
        if len(self.tests) < 6:
            raise ValueError("a coding problem needs at least six tests (examples, edge cases and hidden cases)")
        if self.compare == "validator" and not self.validator:
            raise ValueError("compare=validator needs a validator name")
        return self


class ShortSpec(BaseModel):
    kind: Literal["text", "number", "output"]
    value: list[str] = Field(min_length=1, max_length=6)
    help: str = Field(min_length=5, max_length=200)


class QuestionContent(BaseModel):
    question_id: str = Field(pattern=QUESTION_ID_PATTERN)
    unit_id: str = Field(pattern=_ID)
    topic_id: str = Field(pattern=_ID)
    format: QFormat
    interaction: Interaction = "mcq"
    difficulty: Difficulty
    title: str | None = Field(default=None, max_length=80)
    statement: str = Field(min_length=15, max_length=1800)
    code: str | None = Field(default=None, max_length=2200)
    options: list[str] = Field(default_factory=list, max_length=4)
    correct_index: int | None = Field(default=None, ge=0, le=3)
    short: ShortSpec | None = None
    spec: CodeSpec | None = None
    explanation: str = Field(min_length=10, max_length=2500)
    hints: list[str] = Field(default_factory=list, max_length=3)
    est_time_seconds: int = Field(ge=10, le=2400)
    tags: list[str] = Field(default_factory=list, max_length=6)
    python_version: str | None = Field(default=None, max_length=30)
    status: QuestionStatus = "active"
    version: int = Field(default=1, ge=1)
    source: Literal["seed", "generated", "imported"] = "seed"
    review_status: ReviewStatus = "unverified"
    verification: dict[str, Any] | None = None

    @field_validator("options")
    @classmethod
    def _options_text(cls, value: list[str]) -> list[str]:
        for option in value:
            if not isinstance(option, str) or not option.strip() or len(option) > 260:
                raise ValueError("each option must be 1-260 characters")
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
            if len(self.options) != 4 or self.correct_index is None or self.short is not None or self.spec is not None:
                raise ValueError("an MCQ needs exactly four options, a correct_index and nothing else")
        elif self.interaction == "short":
            if self.short is None or self.options or self.correct_index is not None or self.spec is not None:
                raise ValueError("a short-answer question needs only a short spec")
        else:
            if self.spec is None or self.options or self.correct_index is not None or self.short is not None:
                raise ValueError("a coding question needs only a code spec")
            if self.format not in ("coding", "debug", "complete"):
                raise ValueError("code questions use the coding, debug or complete format")
        return self


# --- Requests --------------------------------------------------------------------------------------------------------------------


class SessionCreateRequest(BaseModel):
    mode: SessionMode
    unit_ids: list[str] = Field(default_factory=list, max_length=9)
    topic_ids: list[str] = Field(default_factory=list, max_length=144)
    difficulty: Difficulty | None = None
    question_count: int = Field(default=10, ge=1, le=MAX_QUESTIONS_PER_SESSION)
    timer_minutes: int | None = Field(default=None, ge=1, le=MAX_TIMER_MINUTES)
    immediate_feedback: bool | None = None

    @field_validator("unit_ids", "topic_ids")
    @classmethod
    def _ids(cls, value: list[str]) -> list[str]:
        for item in value:
            if not re.match(_ID, item):
                raise ValueError("invalid identifier")
        return list(dict.fromkeys(value))


class AnswerRequest(BaseModel):
    """Only a displayed option position, short text or source code is trusted -- never a correctness flag, score or test result."""

    selected_index: int | None = Field(default=None, ge=0, le=3)
    text: str | None = Field(default=None, max_length=MAX_SHORT_CHARS)
    code: str | None = Field(default=None, max_length=MAX_CODE_CHARS)
    marked_for_review: bool = False
    time_spent_seconds: int = Field(default=0, ge=0, le=3600)


class CheckRequest(BaseModel):
    text: str | None = Field(default=None, max_length=MAX_SHORT_CHARS)
    code: str | None = Field(default=None, max_length=MAX_CODE_CHARS)
    time_spent_seconds: int = Field(default=0, ge=0, le=3600)


class RunRequest(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)
