"""
CTF session document shape.

MongoDB is accessed directly via PyMongo (no ODM), so this module documents
the shape of a `ctf_sessions` document rather than mapping to it
automatically. See `app.services.cybersecurity.ctf_service` for the code
that reads/writes these documents.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict

from bson import ObjectId

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


class CtfMessageDocument(TypedDict):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class CtfHintDocument(TypedDict):
    level: HintLevel
    content: str
    requested_at: datetime


class CtfSessionDocument(TypedDict):
    """Shape of a document in the `ctf_sessions` collection."""

    _id: ObjectId
    user_id: ObjectId
    platform: Platform
    category: ChallengeCategory
    difficulty: CtfDifficulty
    title: str
    description: str
    user_notes: str
    status: SessionStatus
    messages: list[CtfMessageDocument]
    hint_history: list[CtfHintDocument]
    hints_used: int
    flag: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
