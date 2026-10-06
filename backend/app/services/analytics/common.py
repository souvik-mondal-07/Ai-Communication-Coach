"""Small shared helpers: date ranges, means, change labels."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable, Sequence

from app.services.analytics import config

RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "all": None}


class InvalidRangeError(ValueError):
    """A client-supplied date range is not acceptable."""


@dataclass(frozen=True)
class DateRange:
    start: datetime | None      # None = all time
    end: datetime
    label: str                  # "7d" | "30d" | "90d" | "all" | "custom"

    @property
    def days(self) -> int | None:
        return None if self.start is None else max(1, round((self.end - self.start).total_seconds() / 86400))

    def previous(self) -> "DateRange | None":
        """The equally long window immediately before this one (None for all-time)."""
        if self.start is None:
            return None
        return DateRange(self.start - (self.end - self.start), self.start, "previous")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def resolve_range(
    range_: str = "30d", start_date: date | None = None, end_date: date | None = None, *, now: datetime | None = None
) -> DateRange:
    """Validate and resolve query parameters into a DateRange. Raises InvalidRangeError."""
    now = now or utcnow()
    if start_date is not None or end_date is not None:
        end = (
            datetime.combine(end_date, time.max, tzinfo=timezone.utc) if end_date is not None else now
        )
        start = (
            datetime.combine(start_date, time.min, tzinfo=timezone.utc)
            if start_date is not None else end - timedelta(days=30)
        )
        if end > now + timedelta(days=1):
            raise InvalidRangeError("end_date cannot be in the future.")
        if start > end:
            raise InvalidRangeError("start_date must be on or before end_date.")
        if (end - start).days > config.MAX_RANGE_DAYS:
            raise InvalidRangeError(f"Date range cannot exceed {config.MAX_RANGE_DAYS} days.")
        return DateRange(start, min(end, now), "custom")
    if range_ not in RANGE_DAYS:
        raise InvalidRangeError("range must be one of: 7d, 30d, 90d, all.")
    days = RANGE_DAYS[range_]
    return DateRange(None if days is None else now - timedelta(days=days), now, range_)


def mean(values: Iterable[float | int | None], digits: int | None = 0) -> float | int | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    m = sum(nums) / len(nums)
    if digits is None:
        return m
    return round(m) if digits == 0 else round(m, digits)


def stdev(values: Sequence[float]) -> float | None:
    return statistics.pstdev(values) if len(values) >= 2 else None


def change_label(delta: float | None, *, higher_is_better: bool = True) -> str | None:
    """Plain label for a score change. Small differences are 'Stable', never exaggerated."""
    if delta is None:
        return None
    effective = delta if higher_is_better else -delta
    if effective >= config.SIGNIFICANT_DELTA:
        return "Significant improvement"
    if effective >= config.IMPROVING_DELTA:
        return "Improving"
    if effective > -config.IMPROVING_DELTA:
        return "Stable"
    if effective > -config.SIGNIFICANT_DELTA:
        return "Slight decline"
    return "Needs attention"


def compare(
    previous: Sequence[float | None], current: Sequence[float | None], *,
    higher_is_better: bool = True, digits: int = 0,
) -> dict:
    """Previous-vs-current comparison; `available: False` unless both sides have enough samples."""
    prev = [v for v in previous if v is not None]
    cur = [v for v in current if v is not None]
    base = {"previous_samples": len(prev), "current_samples": len(cur), "higher_is_better": higher_is_better}
    if len(prev) < config.MIN_COMPARE_SAMPLES or len(cur) < config.MIN_COMPARE_SAMPLES:
        return {**base, "available": False, "previous": None, "current": None, "change": None, "label": None}
    p, c = mean(prev, digits), mean(cur, digits)
    delta = round(c - p, digits or 0) if digits else round(c - p)
    return {**base, "available": True, "previous": p, "current": c, "change": delta,
            "label": change_label(c - p, higher_is_better=higher_is_better)}


def score_band(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= config.STRONG_SCORE:
        return "strong"
    if score < config.WEAK_SCORE:
        return "weak"
    return "developing"


def fmt_dt(value: datetime | None) -> str | None:
    value = as_utc(value)
    return value.isoformat() if value else None
