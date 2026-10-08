"""Reminder configuration (Step 19): what the user's own settings allow. Never overridden."""

from __future__ import annotations

from dataclasses import dataclass

MAX_DAILY_NOTIFICATIONS = 3  # per local day; keeps reminders helpful rather than noisy


@dataclass(frozen=True)
class ReminderConfig:
    reminders_enabled: bool
    daily_practice_enabled: bool
    interview_reminders_enabled: bool
    communication_reminders_enabled: bool
    cybersecurity_reminders_enabled: bool
    preferred_time: str  # "HH:MM", local

    @classmethod
    def from_preferences(cls, prefs) -> "ReminderConfig":
        return cls(
            reminders_enabled=prefs.reminders_enabled,
            daily_practice_enabled=prefs.daily_practice_enabled,
            interview_reminders_enabled=prefs.interview_reminders_enabled,
            communication_reminders_enabled=prefs.communication_reminders_enabled,
            cybersecurity_reminders_enabled=prefs.cybersecurity_reminders_enabled,
            preferred_time=prefs.preferred_practice_time,
        )
