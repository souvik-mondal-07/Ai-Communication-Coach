"""
Mentor chat request/response schemas.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_LENGTH = 10_000
# Generous ceiling to reject an absurdly large payload outright. The
# *effective* context sent to the AI provider is bounded much tighter — see
# `app.services.mentor.mentor_service.CONTEXT_WINDOW`.
MAX_HISTORY_ITEMS = 100

MentorMode = Literal["learn", "explain", "practice", "troubleshoot"]
MentorLevel = Literal["beginner", "intermediate", "advanced"]


class MentorHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message content cannot be blank")
        return value


class MentorChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    mode: MentorMode = "learn"
    level: MentorLevel = "intermediate"
    conversation_history: list[MentorHistoryMessage] = Field(
        default_factory=list, max_length=MAX_HISTORY_ITEMS
    )

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message cannot be blank")
        return stripped
