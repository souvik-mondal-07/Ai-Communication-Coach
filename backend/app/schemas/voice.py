"""
Voice request/response schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.voice.text_to_speech import MAX_TTS_CHARS

# Ceiling for any client-supplied duration. The real per-deployment limit is
# `settings.voice_max_audio_seconds`; this just bounds what we'll accept as a
# number at all.
_MAX_DURATION_SECONDS = 3_600.0


class PauseMetrics(BaseModel):
    """Audio-timing based pause statistics (approximate, from word timestamps)."""

    pause_count: int = Field(ge=0, le=5_000)
    long_pauses: int = Field(ge=0, le=5_000)
    average_pause_seconds: float | None = Field(default=None, ge=0, le=_MAX_DURATION_SECONDS)
    longest_pause_seconds: float | None = Field(default=None, ge=0, le=_MAX_DURATION_SECONDS)
    total_pause_seconds: float = Field(default=0.0, ge=0, le=_MAX_DURATION_SECONDS)
    granularity: str = Field(default="word", pattern="^(word|segment)$")

    @model_validator(mode="after")
    def long_within_total(self) -> "PauseMetrics":
        if self.long_pauses > self.pause_count:
            raise ValueError("long_pauses cannot exceed pause_count")
        return self


class TranscribeData(BaseModel):
    text: str
    language: str | None = None
    duration_seconds: float
    # None when the recording had too little timing information to measure.
    pause_metrics: PauseMetrics | None = None


class AudioMetadata(BaseModel):
    """
    What the client sends back alongside a transcript it chooses to submit, so
    audio-based metrics (speaking rate, pauses) can be stored with the message.
    """

    duration_seconds: float = Field(gt=0, le=_MAX_DURATION_SECONDS)
    language: str | None = Field(default=None, max_length=16)
    pause_metrics: PauseMetrics | None = None

    @field_validator("language")
    @classmethod
    def language_is_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned.replace("-", "").isalpha():
            raise ValueError("Invalid language code")
        return cleaned or None


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TTS_CHARS)

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Text cannot be blank")
        return stripped


class VoiceCapabilities(BaseModel):
    """Public, non-secret description of what voice features the server supports."""

    stt_available: bool
    tts_available: bool
    max_audio_seconds: int
    max_audio_bytes: int
