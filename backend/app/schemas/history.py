"""
History & Activity Center response schemas (Step 15).

The History Center is a read layer over the existing session collections, so
these models are only an *allow-list* of what a normalized activity may expose.
Anything not declared here (user ids, lock tokens, system prompts, evaluator
notes, raw documents) can never reach the client through the list endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ActivityType = Literal[
    "cybersecurity_practice",
    "ctf",
    "communication",
    "interview",
    "pressure_training",
    "voice_conversation",
]

# Normalized across every collection (voice "created"/"active" -> in_progress).
ActivityStatus = Literal["completed", "in_progress", "abandoned"]

MetadataValue = str | int | float | bool | None


class HistoryActivity(BaseModel):
    id: str
    type: ActivityType
    type_label: str
    title: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    # Elapsed wall-clock time from start to finish; None while unfinished or
    # when it is not trustworthy (see HistoryService.MAX_ELAPSED_SECONDS).
    duration_seconds: int | None = None
    score: int | None = None
    status: ActivityStatus
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)


class HistoryListResponse(BaseModel):
    items: list[HistoryActivity]
    page: int
    limit: int
    total: int
    has_next: bool


class HistoryTypeCount(BaseModel):
    type: ActivityType
    label: str
    count: int


class HistorySummaryResponse(BaseModel):
    total: int
    types: list[HistoryTypeCount]


class HistoryDetailResponse(BaseModel):
    activity: HistoryActivity
    # The existing, already client-safe session payload for this activity type.
    detail: dict
