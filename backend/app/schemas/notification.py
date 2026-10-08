"""Notification schemas (Step 19). The type set is closed: clients can never invent one."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class NotificationType(StrEnum):
    DAILY_PRACTICE = "daily_practice"
    PRACTICE_REMINDER = "practice_reminder"
    WEAKNESS = "weakness"
    PROGRESS = "progress"
    STREAK = "streak"
    INTERVIEW = "interview"
    COMMUNICATION = "communication"
    SYSTEM = "system"


class NotificationPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Routes a notification action may point at (in-app only; never an external URL).
ALLOWED_ACTION_TARGETS = frozenset({
    "/practice",
    "/daily-practice", "/cybersecurity", "/cybersecurity/practice", "/communication", "/interview",
    "/pressure-training", "/progress", "/dashboard", "/notifications", "/settings",
})

ReadFilter = Literal["all", "unread", "read"]


class NotificationAction(BaseModel):
    type: Literal["route"] = "route"
    target: str


class NotificationOut(BaseModel):
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    action: NotificationAction | None = None
    is_read: bool
    created_at: datetime
    read_at: datetime | None = None
    expires_at: datetime | None = None
