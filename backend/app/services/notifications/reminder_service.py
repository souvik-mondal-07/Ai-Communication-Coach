"""
Reminder orchestration (Step 19) -- there is no background scheduler.

Evaluation is *lazy and idempotent*: the signed-in client calls ``POST /notifications/sync``
on load and periodically while the app is open. Because every reminder has a period-scoped
``dedupe_key`` protected by a unique index, running it 10 times creates each reminder once.
Reminders are therefore only generated while the user has the app open (no push or
cron infrastructure; see the Step 19 notes).

    settings -> ReminderConfig -> facts (real data) -> reminder_rules.detect_due
             -> daily cap -> NotificationService.create_if_absent
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo.database import Database

from app.db.collections import Collections
from app.models.user import UserDocument
from app.schemas.notification import NotificationType
from app.services.auth.profile_service import to_profile_response
from app.services.daily_practice import timeutil
from app.services.daily_practice.daily_practice_service import DailyPracticeService, daily_practice_service
from app.services.daily_practice.streak import qualifies
from app.services.history.history_service import HistoryService, history_service
from app.services.notifications.notification_service import NotificationService, notification_service
from app.services.notifications.reminder_config import MAX_DAILY_NOTIFICATIONS, ReminderConfig
from app.services.notifications.reminder_rules import Facts, detect_due
from app.services.personalization.personalization_service import PersonalizationService, personalization_service

LOOKBACK_DAYS = 30


class ReminderService:
    def __init__(
        self, *, notifications: NotificationService = notification_service,
        daily: DailyPracticeService = daily_practice_service, history: HistoryService = history_service,
        personalization: PersonalizationService = personalization_service,
    ) -> None:
        self._notifications = notifications
        self._daily = daily
        self._history = history
        self._personalization = personalization

    def evaluate(self, db: Database, *, user: UserDocument, now: datetime | None = None) -> dict:
        now = timeutil.as_utc(now or datetime.now(timezone.utc))
        user_id = str(user["_id"])
        settings = to_profile_response(user)
        prefs = settings.preferences
        cfg = ReminderConfig.from_preferences(prefs)
        if not cfg.reminders_enabled:
            return {"created": [], "unread_count": self._notifications.unread_count(db, user_id=user_id, now=now)}

        tz = timeutil.resolve_tz(prefs.preferred_timezone)
        local = timeutil.local_now(now, tz)
        today = local.date()
        day_start, day_end = timeutil.day_bounds_utc(today, tz)

        state = self._daily.get_today(db, user=user, now=now)
        streak = state["streak"]
        in_window = (not state["rest_day"]) and local.strftime("%H:%M") >= cfg.preferred_time
        needs_scan = in_window or streak["practiced_today"]

        weakness = comm_weakness = None
        days_comm = days_interview = None
        has_comm = has_interview = False
        if needs_scan:
            recent = self._history.list_completed(db, user_id=user_id, since=now - timedelta(days=LOOKBACK_DAYS), until=now)
            last = {}
            for a in recent:
                if qualifies(a):
                    last[a.type] = max(last.get(a.type, a.completed_at), a.completed_at)
            def gap(kind):
                if kind not in last:
                    return None
                return max(0, (today - timeutil.local_date(last[kind], tz)).days)
            days_comm, days_interview = gap("communication"), gap("interview")
            has_comm = days_comm is not None or db[Collections.COMMUNICATION_SESSIONS].count_documents({"user_id": user["_id"]}, limit=1) > 0
            has_interview = days_interview is not None or db[Collections.INTERVIEW_SESSIONS].count_documents({"user_id": user["_id"]}, limit=1) > 0
            if has_comm and days_comm is None:
                days_comm = LOOKBACK_DAYS + 1
            if has_interview and days_interview is None:
                days_interview = LOOKBACK_DAYS + 1

            week_ago = now - timedelta(days=7)
            weakness_recent = db[Collections.NOTIFICATIONS].count_documents(
                {"user_id": user["_id"], "type": NotificationType.WEAKNESS.value,
                 "created_at": {"$gte": week_ago.replace(tzinfo=None)}}, limit=1) > 0
            if in_window and ((cfg.cybersecurity_reminders_enabled and not weakness_recent) or cfg.communication_reminders_enabled):
                recs = self._personalization.get_recommendations(db, user=user).get("recommendations") or []
                if not weakness_recent:
                    weakness = next((r for r in recs if r["type"] == "practice" and r["basis"] == "performance"
                                     and r["priority"] in ("high", "medium")), None)
                comm_weakness = next((r for r in recs if r["type"] == "communication" and r["basis"] == "performance"), None)
                if comm_weakness:
                    has_comm = True

        facts = Facts(
            today=today, local_time_hhmm=local.strftime("%H:%M"), end_of_day_utc=day_end, now_utc=now,
            is_practice_day=not state["rest_day"], streak=streak, plan=state["plan"],
            goal_minutes=prefs.daily_practice_minutes, days_since_communication=days_comm,
            days_since_interview=days_interview, has_communication_history=has_comm,
            has_interview_history=has_interview,
            learning_goals=[g.value if hasattr(g, "value") else g for g in settings.profile.learning_goals],
            interview_focus=[f.value if hasattr(f, "value") else f for f in prefs.interview_focus],
            weakness=weakness, comm_weakness=comm_weakness,
        )

        candidates = [c for c in detect_due(facts, cfg)
                      if not self._notifications.exists(db, user_id=user_id, dedupe_key=c.dedupe_key)]
        budget = MAX_DAILY_NOTIFICATIONS - self._notifications.count_created_between(
            db, user_id=user_id, start=day_start, end=day_end)
        created = []
        for c in candidates[: max(budget, 0)]:
            made = self._notifications.create_if_absent(
                db, user_id=user_id, type=c.type, priority=c.priority, title=c.title, message=c.message,
                action_target=c.action_target, dedupe_key=c.dedupe_key, expires_at=c.expires_at, now=now,
            )
            if made:
                created.append(made)
        return {"created": created, "unread_count": self._notifications.unread_count(db, user_id=user_id, now=now)}


reminder_service = ReminderService()
