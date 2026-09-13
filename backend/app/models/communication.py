"""
Communication scenario and session document shapes.

MongoDB is accessed directly via PyMongo (no ODM), so this module documents
the shape of documents in `communication_scenarios` and
`communication_sessions` rather than mapping to them automatically. See
`app.services.communication.communication_service` and
`...evaluation_service` for the code that reads/writes these documents.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict

from bson import ObjectId

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


class CommunicationScenarioDocument(TypedDict):
    """Shape of a document in the `communication_scenarios` collection."""

    _id: ObjectId
    title: str
    slug: str
    category: Category
    mode: Mode
    difficulty: Difficulty
    description: str
    objective: str
    context: str
    ai_role: str
    user_role: str
    opening_message: str
    skills_targeted: list[str]
    tips: list[str]
    created_at: datetime
    updated_at: datetime


class CommunicationMessageDocument(TypedDict):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime


class BetterResponseDocument(TypedDict):
    original: str
    improved: str
    why: str


class CommunicationEvaluationDocument(TypedDict):
    overall_score: int
    clarity_score: int
    grammar_score: int
    vocabulary_score: int
    professionalism_score: int
    confidence_score: int
    relevance_score: int
    conversation_flow_score: int
    strengths: list[str]
    weaknesses: list[str]
    improvements: list[str]
    better_responses: list[BetterResponseDocument]
    summary: str


class CommunicationSessionDocument(TypedDict):
    """Shape of a document in the `communication_sessions` collection."""

    _id: ObjectId
    user_id: ObjectId
    scenario_id: ObjectId
    scenario_title: str
    category: Category
    mode: Mode
    difficulty: Difficulty
    # Denormalized from the scenario at session-start time, so a session can
    # be reopened and continued without a second scenario lookup.
    ai_role: str
    user_role: str
    objective: str
    status: SessionStatus
    messages: list[CommunicationMessageDocument]
    evaluation: CommunicationEvaluationDocument | None
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None
