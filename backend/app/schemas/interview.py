"""
Interview simulator request schemas.

Requests forbid unknown fields, so a client can never smuggle in a `user_id`
(or anything else) — the user always comes from the JWT.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.voice import AudioMetadata
from app.services.interview.topics import ALLOWED_QUESTION_COUNTS

InterviewType = Literal["hr", "technical", "cybersecurity", "scenario_based", "mixed"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
InputType = Literal["text", "voice"]
SessionStatus = Literal["in_progress", "completed", "abandoned"]

MAX_ANSWER_LENGTH = 10_000


class StartInterviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interview_type: InterviewType
    difficulty: Difficulty
    question_count: int
    # "text" or "voice": how the user prefers to answer (voice reuses Step 8).
    mode: InputType = "text"
    # Interviewers don't grade you mid-interview. Set true for a practice-style
    # run that shows a short evaluation after every answer.
    reveal_feedback: bool = False

    @field_validator("question_count")
    @classmethod
    def question_count_allowed(cls, value: int) -> int:
        if value not in ALLOWED_QUESTION_COUNTS:
            allowed = ", ".join(str(n) for n in ALLOWED_QUESTION_COUNTS)
            raise ValueError(f"question_count must be one of: {allowed}")
        return value


class SubmitAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=MAX_ANSWER_LENGTH)
    # Voice answers are a (possibly edited) transcript from the Step 8
    # /voice/transcribe endpoint plus its audio metadata.
    input_type: InputType = "text"
    audio_metadata: AudioMetadata | None = None
    transcript_edited: bool = False

    @field_validator("answer")
    @classmethod
    def answer_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Answer cannot be blank")
        return stripped

    @model_validator(mode="after")
    def audio_metadata_only_for_voice(self) -> "SubmitAnswerRequest":
        if self.input_type != "voice" and self.audio_metadata is not None:
            raise ValueError("audio_metadata is only valid for voice answers")
        return self
