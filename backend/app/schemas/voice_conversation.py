"""
Voice conversation request schemas (Step 13).

Requests forbid unknown fields, so a client can never smuggle in a `user_id`
(ownership always comes from the JWT) or internal engine settings. Options
that only make sense for one mode are rejected for the others, so the stored
configuration is always coherent.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.interview.topics import ALLOWED_QUESTION_COUNTS
from app.services.pressure.pressure_config import PRESSURE_LEVELS

VoiceConversationMode = Literal[
    "general", "cybersecurity", "communication", "interview", "practice", "pressure"
]
Difficulty = Literal["beginner", "intermediate", "advanced"]
InterviewType = Literal["hr", "technical", "cybersecurity", "scenario_based", "mixed"]

MAX_TOPIC_LENGTH = 120
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

# Modes that run on top of an existing structured session (Steps 9 / 10).
_QUESTION_MODES = ("interview", "pressure")


class CreateVoiceSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: VoiceConversationMode
    difficulty: Difficulty = "intermediate"
    # Free-text subject. Required for "practice"; optional flavour elsewhere.
    topic: str | None = None

    # --- Optional, mode-specific settings ---
    interview_type: InterviewType | None = None  # interview / pressure
    question_count: int | None = None  # interview / pressure
    pressure_level: int | None = None  # pressure
    scenario_slug: str | None = None  # communication

    @field_validator("topic")
    @classmethod
    def clean_topic(cls, value: str | None) -> str | None:
        if value is None:
            return None
        # Single line, no control characters: the topic is interpolated into a prompt.
        cleaned = " ".join(_CONTROL_CHARS.sub(" ", value).split())
        if len(cleaned) > MAX_TOPIC_LENGTH:
            raise ValueError(f"topic must be at most {MAX_TOPIC_LENGTH} characters")
        return cleaned or None

    @field_validator("question_count")
    @classmethod
    def question_count_allowed(cls, value: int | None) -> int | None:
        if value is not None and value not in ALLOWED_QUESTION_COUNTS:
            allowed = ", ".join(str(n) for n in ALLOWED_QUESTION_COUNTS)
            raise ValueError(f"question_count must be one of: {allowed}")
        return value

    @field_validator("pressure_level")
    @classmethod
    def pressure_level_allowed(cls, value: int | None) -> int | None:
        if value is not None and value not in PRESSURE_LEVELS:
            allowed = ", ".join(str(n) for n in PRESSURE_LEVELS)
            raise ValueError(f"pressure_level must be one of: {allowed}")
        return value

    @field_validator("scenario_slug")
    @classmethod
    def slug_is_safe(cls, value: str | None) -> str | None:
        if value is not None and not _SLUG_RE.match(value):
            raise ValueError("Invalid scenario_slug")
        return value

    @model_validator(mode="after")
    def options_match_mode(self) -> "CreateVoiceSessionRequest":
        if self.mode == "practice" and not self.topic:
            raise ValueError("A topic is required for practice conversations")
        if self.mode not in _QUESTION_MODES:
            for name in ("interview_type", "question_count"):
                if getattr(self, name) is not None:
                    raise ValueError(f"{name} is only valid for interview and pressure conversations")
        if self.mode != "pressure" and self.pressure_level is not None:
            raise ValueError("pressure_level is only valid for pressure conversations")
        if self.mode != "communication" and self.scenario_slug is not None:
            raise ValueError("scenario_slug is only valid for communication conversations")
        return self


# --- Separated flow: transcript in, AI turn out -------------------------------------------------------

# Longest transcript we accept for one spoken answer. Whisper output for a 2-minute answer is a
# few thousand characters; this only stops absurd payloads from reaching the model.
MAX_TRANSCRIPT_CHARS = 12_000
_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")


class PauseMetricsPayload(BaseModel):
    """
    The pause statistics `/transcribe` returned, echoed back by the client.
    Strictly typed and bounded so a client can't push arbitrary structures
    into the stored speaking analysis.
    """

    model_config = ConfigDict(extra="forbid")

    pause_count: int = Field(ge=0, le=10_000)
    long_pauses: int = Field(ge=0, le=10_000)
    average_pause_seconds: float | None = Field(default=None, ge=0, le=3_600)
    longest_pause_seconds: float | None = Field(default=None, ge=0, le=3_600)
    total_pause_seconds: float = Field(ge=0, le=3_600)
    granularity: Literal["word", "segment"]


class ProcessTranscriptRequest(BaseModel):
    """
    One already-transcribed spoken answer, ready for the AI.

    Carries no audio: this is also what "Retry response" sends, so a failed
    AI step can be retried without any speech-to-text running again.
    """

    model_config = ConfigDict(extra="forbid")

    transcript: str = Field(max_length=MAX_TRANSCRIPT_CHARS)
    # Answers already given; the server rejects a stale or duplicate submission.
    expected_turn: int = Field(ge=0, le=10_000)
    # Seconds from the AI finishing to the answer starting (pressure mode only).
    response_seconds: float | None = Field(default=None, ge=0, le=3_600)
    # Measured by the server during transcription and echoed back for the speaking analysis.
    duration_seconds: float | None = Field(default=None, ge=0, le=3_600)
    language: str | None = None
    pause_metrics: PauseMetricsPayload | None = None

    @field_validator("language")
    @classmethod
    def language_is_a_code(cls, value: str | None) -> str | None:
        if value is not None and not _LANGUAGE_RE.match(value):
            raise ValueError("Invalid language code")
        return value

    @field_validator("transcript")
    @classmethod
    def trim_transcript(cls, value: str) -> str:
        # Emptiness is judged by the service (so it can answer with a specific error code).
        return value.strip()
