"""
CTF session request/response schemas.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ChallengeCategory = Literal[
    "web_security",
    "cryptography",
    "digital_forensics",
    "steganography",
    "osint",
    "reverse_engineering",
    "binary_exploitation",
    "linux",
    "networking",
    "miscellaneous",
]
Platform = Literal["Hack The Box", "TryHackMe", "CTF", "Custom Lab", "Other"]
CtfDifficulty = Literal["easy", "medium", "hard"]
SessionStatus = Literal["in_progress", "completed", "abandoned"]
HintLevel = Literal["hint_1", "hint_2", "hint_3", "solution"]

MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 5_000
MAX_NOTES_LENGTH = 5_000
MAX_MESSAGE_LENGTH = 5_000


class CreateSessionRequest(BaseModel):
    platform: Platform
    category: ChallengeCategory
    difficulty: CtfDifficulty
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    description: str = Field(min_length=1, max_length=MAX_DESCRIPTION_LENGTH)
    user_notes: str = Field(default="", max_length=MAX_NOTES_LENGTH)

    @field_validator("title", "description")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot be blank")
        return value.strip()


class CreateSessionData(BaseModel):
    session_id: str
    status: SessionStatus


class SessionSummary(BaseModel):
    session_id: str
    platform: Platform
    category: ChallengeCategory
    difficulty: CtfDifficulty
    title: str
    status: SessionStatus
    hints_used: int
    created_at: str
    updated_at: str
    completed_at: str | None = None


class CtfChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class CtfHintOut(BaseModel):
    level: HintLevel
    content: str
    requested_at: str


class SessionDetail(SessionSummary):
    description: str
    user_notes: str
    messages: list[CtfChatMessage] = Field(default_factory=list)
    hints: list[CtfHintOut] = Field(default_factory=list)


class SessionHistoryData(BaseModel):
    sessions: list[SessionSummary]
    page: int
    limit: int
    total: int


class CtfChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message cannot be blank")
        return stripped


class CtfChatResponseData(BaseModel):
    response: str


class HintResponseData(BaseModel):
    level: HintLevel
    content: str
    hints_used: int


class CompleteSessionRequest(BaseModel):
    flag: str | None = Field(default=None, max_length=500)


class CompleteSessionData(BaseModel):
    status: SessionStatus
