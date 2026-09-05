"""
Central registry of MongoDB collection names.

Reserving names here now means future features reference a single source of
truth (`Collections.USERS`, etc.) instead of scattering string literals
across the codebase. No CRUD logic lives here yet — that arrives with each
feature.
"""

from enum import StrEnum


class Collections(StrEnum):
    USERS = "users"
    CONVERSATIONS = "conversations"
    INTERVIEW_SESSIONS = "interview_sessions"
    INTERVIEW_ANSWERS = "interview_answers"
    COMMUNICATION_SESSIONS = "communication_sessions"
    LEARNING_PROGRESS = "learning_progress"
    CYBERSECURITY_TOPICS = "cybersecurity_topics"
    PRACTICE_SESSIONS = "practice_sessions"
    USER_WEAKNESSES = "user_weaknesses"
    RECOMMENDATIONS = "recommendations"
    UPLOADED_DOCUMENTS = "uploaded_documents"
