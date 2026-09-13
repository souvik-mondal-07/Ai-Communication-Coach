"""
Communication coach request/response schemas.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Category = Literal[
    "classmates",
    "teachers",
    "seniors",
    "recruiters",
    "teammates",
    "managers",
    "everyday",
    "professional",
]
Mode = Literal["daily_life", "professional", "social", "difficult_conversation", "roleplay"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
SessionStatus = Literal["in_progress", "completed"]

MAX_MESSAGE_LENGTH = 5_000


class ScenarioSummary(BaseModel):
    scenario_id: str
    title: str
    slug: str
    category: Category
    mode: Mode
    difficulty: Difficulty
    description: str
    objective: str
    skills_targeted: list[str] = Field(default_factory=list)


class ScenarioDetail(ScenarioSummary):
    context: str
    ai_role: str
    user_role: str
    opening_message: str
    tips: list[str] = Field(default_factory=list)


class StartSessionRequest(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=200)
    difficulty: Difficulty | None = None


class StartSessionData(BaseModel):
    session_id: str
    scenario: ScenarioDetail
    status: SessionStatus


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message cannot be blank")
        return stripped


class SendMessageData(BaseModel):
    reply: str
    session_id: str
    message_id: str


class BetterResponse(BaseModel):
    original: str
    improved: str
    why: str = ""


class EvaluationOut(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    clarity_score: int = Field(ge=0, le=100)
    grammar_score: int = Field(ge=0, le=100)
    vocabulary_score: int = Field(ge=0, le=100)
    professionalism_score: int = Field(ge=0, le=100)
    confidence_score: int = Field(ge=0, le=100)
    relevance_score: int = Field(ge=0, le=100)
    conversation_flow_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    better_responses: list[BetterResponse] = Field(default_factory=list)
    summary: str


class CompleteSessionData(BaseModel):
    session_id: str
    evaluation: EvaluationOut


class SessionMessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class SessionSummary(BaseModel):
    session_id: str
    scenario_title: str
    category: Category
    mode: Mode
    difficulty: Difficulty
    status: SessionStatus
    overall_score: int | None = None
    started_at: str
    completed_at: str | None = None


class SessionDetail(SessionSummary):
    ai_role: str
    user_role: str
    objective: str
    messages: list[SessionMessageOut] = Field(default_factory=list)
    evaluation: EvaluationOut | None = None


class SessionHistoryData(BaseModel):
    sessions: list[SessionSummary]
    page: int
    limit: int
    total: int
