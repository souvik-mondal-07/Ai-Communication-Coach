"""
Practice streaks (Step 19).

COMPLETION RULE (documented, single definition -- ``qualifies``):
    A day counts as an *active day* when at least one practice activity was
    **completed** on that local day with a real result: a finished, scored session
    (cybersecurity practice, communication, interview, pressure training, voice
    conversation) or a finished CTF/lab. Opening the dashboard, starting a session
    or abandoning one never counts. Several sessions on one day count once.

The streak is derived from the user's real sessions. ``practice_streaks`` only
caches the set of active local dates (plus how far the sessions were scanned), so
it can always be rebuilt and can never drift from history: if the user's timezone
changes the cache is discarded and rebuilt from the sessions.

Pure functions (``compute_streak``) hold all the date arithmetic and are tested
without a database.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from datetime import tzinfo

from bson import ObjectId
from pymongo.database import Database

from app.db.collections import Collections
from app.schemas.history import HistoryActivity
from app.services.daily_practice import timeutil
from app.services.history.history_service import HistoryService, history_service

MAX_STORED_DAYS = 3_700  # ~10 years of ISO dates; bounds the cached document


def qualifies(activity: HistoryActivity) -> bool:
    """The one streak rule: completed, and it produced a result (CTFs have no score)."""
    if activity.status != "completed" or activity.completed_at is None:
        return False
    return activity.score is not None or activity.type == "ctf"


def compute_streak(
    active_dates: set[date],
    *,
    today: date,
    practice_weekdays: frozenset[int] | None = None,
) -> dict:
    """
    Current/longest streak from a set of active local dates.

    * Dates after ``today`` (clock skew, bad data) are ignored.
    * The current streak is still alive if the user has not practiced *yet today*:
      it is counted back from yesterday. Missing a whole (counted) day resets it.
    * ``practice_weekdays`` (Mon=0): a day that is not a practice day neither breaks
      nor extends a streak, so someone who practices Mon-Fri keeps it over a weekend.
      Practicing on a rest day still counts as active.
    """
    days = sorted(d for d in active_dates if d <= today)
    expected = practice_weekdays if practice_weekdays else frozenset(range(7))
    all_days = set(days)

    def previous_counted(day: date) -> date:
        """Closest earlier day that would have to be practiced to keep a streak."""
        cursor = day - timedelta(days=1)
        for _ in range(7):
            if cursor.weekday() in expected or cursor in all_days:
                return cursor
            cursor -= timedelta(days=1)
        return cursor

    # Longest: walk active days, a run continues when the previous counted day is active.
    longest = run = 0
    for d in days:
        prev = previous_counted(d)
        run = run + 1 if prev in all_days else 1
        longest = max(longest, run)

    current = 0
    if days:
        practiced_today = today in all_days
        anchor = today if practiced_today else previous_counted(today)
        # Walk back from the anchor while consecutive counted days are active.
        if anchor in all_days:
            cursor = anchor
            while cursor in all_days:
                current += 1
                cursor = previous_counted(cursor)
    practiced_today = today in all_days
    return {
        "current_streak": current,
        "longest_streak": max(longest, current),
        "last_practice_date": days[-1].isoformat() if days else None,
        "total_active_days": len(days),
        "practiced_today": practiced_today,
        "at_risk": current > 0 and not practiced_today,
    }


class StreakService:
    def __init__(self, history: HistoryService = history_service) -> None:
        self._history = history

    def ensure_indexes(self, db: Database) -> None:
        db[Collections.PRACTICE_STREAKS].create_index("user_id", unique=True)

    # ------------------------------------------------------------------ cache sync
    def _active_dates_from(
        self, db: Database, *, user_id: str, since: datetime | None, until: datetime, tz: tzinfo
    ) -> set[date]:
        activities = self._history.list_completed(db, user_id=user_id, since=since, until=until)
        return {timeutil.local_date(a.completed_at, tz) for a in activities if qualifies(a)}

    def sync(self, db: Database, *, user_id: str, tz_name: str | None, now: datetime | None = None) -> set[date]:
        """Bring the cached active-date set up to date and return it. Idempotent."""
        now = timeutil.as_utc(now or datetime.now(timezone.utc))
        tz = timeutil.resolve_tz(tz_name)
        uid = ObjectId(user_id)
        collection = db[Collections.PRACTICE_STREAKS]
        doc = collection.find_one({"user_id": uid})

        rebuild = doc is None or doc.get("timezone") != timeutil.tz_key(tz)
        # Re-scan one day behind the last sync: cheap, idempotent (set union), and immune to a
        # session whose completed_at was stamped just before a sync that ran before it was written.
        since = None if rebuild else timeutil.as_utc(doc["synced_through"]) - timedelta(days=1)
        stored: set[date] = set() if rebuild else {date.fromisoformat(s) for s in doc.get("active_dates", [])}

        stored |= self._active_dates_from(db, user_id=user_id, since=since, until=now, tz=tz)
        newest = sorted(stored)[-MAX_STORED_DAYS:]
        collection.update_one(
            {"user_id": uid},
            {"$set": {
                "user_id": uid,
                "timezone": timeutil.tz_key(tz),
                "active_dates": [d.isoformat() for d in newest],
                "synced_through": now,
                "updated_at": now,
            }},
            upsert=True,
        )
        return set(newest)

    def get_streak(
        self, db: Database, *, user_id: str, tz_name: str | None,
        practice_weekdays: frozenset[int] | None = None, now: datetime | None = None,
    ) -> dict:
        now = timeutil.as_utc(now or datetime.now(timezone.utc))
        tz = timeutil.resolve_tz(tz_name)
        active = self.sync(db, user_id=user_id, tz_name=tz_name, now=now)
        result = compute_streak(active, today=timeutil.local_date(now, tz), practice_weekdays=practice_weekdays)
        result["timezone"] = timeutil.tz_key(tz)
        return result


streak_service = StreakService()
