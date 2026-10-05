"""
Shared practice types: service-level errors and the answer result (Steps 5 + 17).

Defined here (rather than in `practice_service`) so the advanced-practice mixin
and the original service can share them without a circular import.
`practice_service` re-exports every name, so existing imports keep working.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class PracticeError(Exception):
    """Base class for all practice-service-level errors."""


class TopicNotFoundError(PracticeError):
    pass


class PracticeGenerationError(PracticeError):
    """Gemini failed, or never returned validatable question data."""


class SessionNotFoundError(PracticeError):
    pass


class SessionForbiddenError(PracticeError):
    """The session exists but doesn't belong to the requesting user."""


class QuestionNotFoundError(PracticeError):
    pass


class AnswerEvaluationError(PracticeError):
    """Gemini failed, or never returned validatable evaluation data."""


# --- Step 17 -------------------------------------------------------------------


class InvalidPracticeConfigError(PracticeError):
    """The requested session configuration can't be satisfied."""


class AnswerAlreadySubmittedError(PracticeError):
    """This question was already answered (or is being evaluated right now)."""


class SessionClosedError(PracticeError):
    """The session is completed, or its timer ran out."""

    def __init__(self, message: str = "", *, expired: bool = False) -> None:
        super().__init__(message)
        self.expired = expired


class HintLimitError(PracticeError):
    """No more hints are available for this question (or hints aren't allowed right now)."""

    def __init__(self, message: str = "", *, code: str = "HINT_LIMIT_REACHED") -> None:
        super().__init__(message)
        self.code = code


class QuestionNotReadyError(PracticeError):
    """The next question was requested too early, or the session has no more questions."""

    def __init__(self, message: str = "", *, code: str = "QUESTION_NOT_READY") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AnswerResult:
    score: int
    correct: bool
    feedback: str
    ideal_answer: str | None
    missing_points: list[str] = field(default_factory=list)
    # Step 17 additions -- all optional so Step 5 callers/fakes are unaffected.
    raw_score: int | None = None
    hints_used: int = 0
    hint_penalty: int = 0
    dimension_scores: dict | None = None
    strengths: list[str] = field(default_factory=list)
    improvement: str | None = None
    explanation: str | None = None
    ideal_steps: list[str] | None = None
    revealed: bool = False

    def to_public_dict(self) -> dict:
        return {
            "score": self.score,
            "correct": self.correct,
            "feedback": self.feedback,
            "ideal_answer": self.ideal_answer,
            "missing_points": self.missing_points,
            "raw_score": self.raw_score,
            "hints_used": self.hints_used,
            "hint_penalty": self.hint_penalty,
            "dimension_scores": self.dimension_scores,
            "strengths": self.strengths,
            "improvement": self.improvement,
            "explanation": self.explanation,
            "ideal_steps": self.ideal_steps,
            "revealed": self.revealed,
        }
