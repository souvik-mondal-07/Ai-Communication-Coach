"""
Pressure & Nervousness Training request schemas.

Requests forbid unknown fields, so a client can never smuggle in a `user_id`
or the internal pressure-engine probabilities -- the user always comes from
the JWT, and the pressure configuration is always computed server-side from
`pressure_level` (see `app.services.pressure.pressure_config`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.voice import AudioMetadata
from app.services.interview.topics import ALLOWED_QUESTION_COUNTS
from app.services.pressure.pressure_config import PRESSURE_LEVELS

PressureMode = Literal["interview", "communication"]
InterviewType = Literal["hr", "technical", "cybersecurity", "scenario_based", "mixed"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
InputMode = Literal["text", "voice"]
SelfReportedDifficulty = Literal["easy", "manageable", "challenging", "very_difficult"]

MAX_ANSWER_LENGTH = 10_000


class StartPressureSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pressure_level: int
    mode: PressureMode = "interview"
    # Only meaningful for mode="interview"; "communication" always uses the
    # HR/behavioral topic pool. Defaults to a mixed interview.
    interview_type: InterviewType = "mixed"
    difficulty: Difficulty = "intermediate"
    question_count: int = 10
    input_mode: InputMode = "text"

    @field_validator("pressure_level")
    @classmethod
    def level_allowed(cls, value: int) -> int:
        if value not in PRESSURE_LEVELS:
            allowed = ", ".join(str(n) for n in PRESSURE_LEVELS)
            raise ValueError(f"pressure_level must be one of: {allowed}")
        return value

    @field_validator("question_count")
    @classmethod
    def question_count_allowed(cls, value: int) -> int:
        if value not in ALLOWED_QUESTION_COUNTS:
            allowed = ", ".join(str(n) for n in ALLOWED_QUESTION_COUNTS)
            raise ValueError(f"question_count must be one of: {allowed}")
        return value

    @model_validator(mode="after")
    def resolve_interview_type(self) -> "StartPressureSessionRequest":
        # "communication" mode is always behavioral/HR-style pressure practice.
        if self.mode == "communication":
            self.interview_type = "hr"
        return self


class SubmitPressureResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(default="", max_length=MAX_ANSWER_LENGTH)
    input_type: InputMode = "text"
    audio_metadata: AudioMetadata | None = None
    transcript_edited: bool = False
    # Client-reported elapsed time; the server also measures this independently
    # and never trusts the client value alone (see pressure_service.py).
    response_duration_seconds: float | None = Field(default=None, ge=0, le=3600)
    # Set when the on-screen timer reached zero. When true, a blank answer is
    # accepted (the response is recorded as "no answer" rather than discarded).
    timed_out: bool = False

    @field_validator("answer")
    @classmethod
    def clean_answer(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def answer_required_unless_timed_out(self) -> "SubmitPressureResponseRequest":
        if not self.answer and not self.timed_out:
            raise ValueError("Answer cannot be blank unless the time limit expired")
        return self

    @model_validator(mode="after")
    def audio_metadata_only_for_voice(self) -> "SubmitPressureResponseRequest":
        if self.input_type != "voice" and self.audio_metadata is not None:
            raise ValueError("audio_metadata is only valid for voice answers")
        return self


class SelfReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    difficulty: SelfReportedDifficulty
    note: str | None = Field(default=None, max_length=1000)
