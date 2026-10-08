"""
Due-reminder detection (Step 19) -- pure functions over real facts, no I/O.

Reminder pipeline (each stage is its own module):

    reminder_config  : which reminder kinds the user's settings allow
    reminder_rules   : (this file) which of those are *due* right now, from real facts
    notification_service.create_if_absent : creation, deduplicated by ``dedupe_key``
    API / browser notification service    : delivery

Every candidate carries a ``dedupe_key`` that encodes its intended period, so the same
reminder can never be created twice for that period however often evaluation runs.
Nothing here invents activity: each message is built from the supplied facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.schemas.notification import NotificationPriority as P
from app.schemas.notification import NotificationType as T

STREAK_MILESTONES = (3, 7, 14, 30, 60, 100, 200, 365)
LAPSE_DAYS = 3
INTERVIEW_GAP_DAYS = 7
COMMUNICATION_GAP_DAYS = 5
PRIORITY_ORDER = {P.HIGH: 0, P.MEDIUM: 1, P.LOW: 2}


@dataclass(frozen=True)
class Candidate:
    type: T
    priority: P
    title: str
    message: str
    action_target: str
    dedupe_key: str
    expires_at: datetime


@dataclass
class Facts:
    today: object                  # local date
    local_time_hhmm: str           # "HH:MM"
    end_of_day_utc: datetime
    now_utc: datetime
    is_practice_day: bool
    streak: dict                   # from streak service
    plan: dict | None              # today's plan (None when disabled / rest day)
    goal_minutes: int
    days_since_communication: int | None
    days_since_interview: int | None
    has_communication_history: bool
    has_interview_history: bool
    learning_goals: list[str]
    interview_focus: list[str]
    weakness: dict | None          # top performance-based practice recommendation, if any
    comm_weakness: dict | None


def _week(today) -> str:
    year, week, _ = today.isocalendar()
    return f"{year}-W{week:02d}"


def detect_due(f: Facts, cfg) -> list[Candidate]:
    """Candidates ordered by priority. ``cfg`` is a ``ReminderConfig`` (what the user allows)."""
    out: list[Candidate] = []
    if not cfg.reminders_enabled:
        return out
    in_window = f.is_practice_day and f.local_time_hhmm >= cfg.preferred_time
    streak = f.streak["current_streak"]
    practiced_today = f.streak["practiced_today"]
    plan_done = bool(f.plan and f.plan["status"] == "completed")
    day = f.today.isoformat()

    # Milestone: a real streak count reached today (not time-gated: it is a result, not a nudge).
    if practiced_today and streak in STREAK_MILESTONES:
        out.append(Candidate(T.STREAK, P.LOW, f"{streak}-day streak!",
                             f"You've practiced {streak} days in a row. Keep it going.",
                             "/progress", f"streak:{streak}:{day}", f.now_utc + timedelta(days=30)))

    if not in_window or practiced_today:
        return sorted(out, key=lambda c: PRIORITY_ORDER[c.priority])

    # 1) Daily practice
    if cfg.daily_practice_enabled and f.plan and not plan_done:
        parts = ["Your daily practice is waiting."]
        if streak > 0:
            parts.append(f"You have a {streak}-day streak. Keep it going!")
        parts.append(f"Today: {f.plan['focus']['title']} (about {f.goal_minutes} min).")
        out.append(Candidate(T.DAILY_PRACTICE, P.MEDIUM, "Today's Practice", " ".join(parts),
                             "/daily-practice", f"daily_practice:{day}", f.end_of_day_utc))

    # 2) Lapse: a real gap since the last completed practice
    last = f.streak.get("last_practice_date")
    if cfg.daily_practice_enabled and last:
        gap = (f.today - type(f.today).fromisoformat(last)).days
        if gap >= LAPSE_DAYS:
            out.append(Candidate(T.PRACTICE_REMINDER, P.MEDIUM, "Time to get back to it",
                                 f"It has been {gap} days since your last practice. "
                                 f"A {min(f.goal_minutes, 10)}-minute session is enough to restart.",
                                 "/daily-practice", f"lapse:{last}", f.now_utc + timedelta(days=3)))

    # 3) Weakness (cybersecurity reminders)
    if cfg.cybersecurity_reminders_enabled and f.weakness:
        w = f.weakness
        priority = P.HIGH if w["priority"] == "high" else P.MEDIUM
        reason = (w.get("reasons") or ["Recent results show room to improve."])[0]
        out.append(Candidate(T.WEAKNESS, priority, f"Needs practice: {w['topic']}", reason,
                             "/cybersecurity/practice", f"weakness:{w['topic_key']}:{_week(f.today)}",
                             f.now_utc + timedelta(days=7)))

    # 4) Interview
    wants_interview = "prepare_for_interviews" in f.learning_goals or bool(f.interview_focus) or f.has_interview_history
    if cfg.interview_reminders_enabled and wants_interview:
        d = f.days_since_interview
        if d is None or d >= INTERVIEW_GAP_DAYS:
            high = "prepare_for_interviews" in f.learning_goals
            msg = ("You haven't completed a mock interview yet. Try one technical question today." if d is None
                   else f"You last practiced an interview {d} days ago. Try one technical question today.")
            out.append(Candidate(T.INTERVIEW, P.HIGH if high else P.MEDIUM, "Interview practice", msg,
                                 "/interview", f"interview:{_week(f.today)}", f.now_utc + timedelta(days=7)))

    # 5) Communication
    wants_comm = "improve_communication" in f.learning_goals or f.has_communication_history or bool(f.comm_weakness)
    if cfg.communication_reminders_enabled and wants_comm:
        d = f.days_since_communication
        if d is None or d >= COMMUNICATION_GAP_DAYS:
            if f.comm_weakness:
                msg = (f.comm_weakness.get("reasons") or ["Spend 5 minutes practicing speaking clearly."])[0]
                title = f.comm_weakness["title"]
            else:
                msg = ("Take 5 minutes to practice speaking clearly." if d is None
                       else f"It has been {d} days since your last communication practice. Take 5 minutes today.")
                title = "Communication practice"
            out.append(Candidate(T.COMMUNICATION, P.MEDIUM, title, msg, "/communication",
                                 f"communication:{_week(f.today)}", f.now_utc + timedelta(days=7)))

    return sorted(out, key=lambda c: PRIORITY_ORDER[c.priority])
