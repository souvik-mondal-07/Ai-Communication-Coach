"""
Timezone-aware "which day is it for this user" helpers (Step 19).

The server clock is UTC, but a streak day is the *user's* calendar day. Every day
boundary used by daily practice, streaks and reminders goes through this module, so
the rule lives in one place:

* the timezone is the user's ``preferred_timezone`` (an IANA name); an unset or
  invalid value falls back to UTC rather than failing;
* the local date of an instant is ``instant.astimezone(tz).date()``;
* a local day is half-open ``[local midnight, next local midnight)`` converted to UTC,
  so DST days (23/25 hours) are handled correctly.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def resolve_tz(name: str | None) -> tzinfo:
    """
    The user's timezone, never raising. Falls back to UTC, and to the stdlib fixed UTC offset if
    the machine has no IANA database at all (e.g. Windows without the ``tzdata`` package).
    """
    if name and name != "UTC":
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError, OSError):
            pass
    try:
        return ZoneInfo("UTC")
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return timezone.utc


def tz_key(tz: tzinfo) -> str:
    """Stable name for a resolved timezone ('UTC' for the stdlib fallback)."""
    return getattr(tz, "key", None) or "UTC"


def tz_name(name: str | None) -> str:
    return tz_key(resolve_tz(name))


def as_utc(value: datetime) -> datetime:
    """Mongo returns naive UTC datetimes; make them explicit."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def local_date(instant: datetime, tz: tzinfo) -> date:
    return as_utc(instant).astimezone(tz).date()


def local_now(now: datetime, tz: tzinfo) -> datetime:
    return as_utc(now).astimezone(tz)


def day_bounds_utc(day: date, tz: tzinfo) -> tuple[datetime, datetime]:
    """UTC instants of the local day's start (inclusive) and the next local day's start (exclusive)."""
    start = datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc)
    return start, end


def weekday_name(day: date) -> str:
    return WEEKDAYS[day.weekday()]


def parse_hhmm(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))
