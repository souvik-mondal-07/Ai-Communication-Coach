"""Daily practice schemas (Step 19)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TaskKind = Literal["cybersecurity", "communication", "interview"]
TaskStatus = Literal["pending", "in_progress", "completed"]
PlanStatus = Literal["pending", "in_progress", "completed"]


class LinkSessionRequest(BaseModel):
    """Attach a session the user started through an existing module to a plan task."""

    session_id: str = Field(pattern=r"^[0-9a-fA-F]{24}$")


class TaskOut(BaseModel):
    task_id: TaskKind
    kind: TaskKind
    title: str
    description: str
    why: list[str]
    est_minutes: int
    route: str
    config: dict
    status: TaskStatus
    session_id: str | None = None
    score: int | None = None
    minutes: int | None = None


class FocusOut(BaseModel):
    title: str
    topic: str
    basis: str


class SummaryResult(BaseModel):
    task_id: str
    title: str
    score: int | None = None
    minutes: int | None = None


class SummaryOut(BaseModel):
    technical_score: int | None = None
    communication_score: int | None = None
    topics: list[str]
    minutes_practiced: int
    streak: int
    results: list[SummaryResult]
    recommended_next: str | None = None


class PlanOut(BaseModel):
    date: str
    status: PlanStatus
    goal_minutes: int
    difficulty: str
    focus: FocusOut
    rationale: list[str]
    tasks: list[TaskOut]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completion: Literal["full", "partial"] | None = None
    summary: SummaryOut | None = None


class GoalOut(BaseModel):
    goal_minutes: int
    minutes_done: int
    tasks_total: int
    tasks_done: int


class StreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    last_practice_date: str | None
    total_active_days: int
    practiced_today: bool
    at_risk: bool
    timezone: str


class DailyPracticeOut(BaseModel):
    enabled: bool
    rest_day: bool
    date: str
    timezone: str
    plan: PlanOut | None
    goal: GoalOut | None
    streak: StreakOut
    unread_notifications: int = 0
