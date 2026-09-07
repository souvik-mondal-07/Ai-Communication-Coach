"""
Cybersecurity topic and practice-session document shapes.

MongoDB is accessed directly via PyMongo (no ODM), so this module documents
the shape of documents in `cybersecurity_topics` and `practice_sessions`
rather than mapping to them automatically. See
`app.services.cybersecurity.learning_service` and `...practice_service` for
the code that reads/writes these documents.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict

from bson import ObjectId

Difficulty = Literal["beginner", "intermediate", "advanced"]
QuestionType = Literal["multiple_choice", "short_answer"]


class TopicDocument(TypedDict):
    """Shape of a document in the `cybersecurity_topics` collection."""

    _id: ObjectId
    slug: str
    title: str
    category: str
    difficulty: Difficulty
    description: str
    learning_objectives: list[str]
    content: str
    examples: list[str]
    key_points: list[str]
    practice_enabled: bool


class PracticeQuestionDocument(TypedDict):
    """
    A single question embedded in a practice session document.

    `correct_answer` / `ideal_answer` / `explanation` are internal-only —
    never sent to the client until after the question is answered.
    """

    question_id: str
    question: str
    type: QuestionType
    options: list[str] | None
    correct_answer: str | None
    ideal_answer: str | None
    explanation: str


class PracticeAnswerDocument(TypedDict):
    answer: str
    score: int
    correct: bool
    feedback: str
    missing_points: list[str]
    answered_at: datetime


class PracticeSessionDocument(TypedDict):
    """Shape of a document in the `practice_sessions` collection."""

    _id: ObjectId
    user_id: ObjectId
    topic_slug: str
    topic_title: str
    category: str
    difficulty: Difficulty
    started_at: datetime
    completed_at: datetime | None
    status: Literal["in_progress", "completed"]
    questions: list[PracticeQuestionDocument]
    answers: dict[str, PracticeAnswerDocument]
    score: int | None
    questions_answered: int | None
    correct_answers: int | None
    weak_areas: list[str]
    recommendations: list[str]
