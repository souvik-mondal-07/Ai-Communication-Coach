"""
Progress & Personal AI Profile request schemas (Step 11).

Every progress endpoint is either a plain GET (query params only, validated
inline via FastAPI's `Query`, matching the rest of the project's convention
-- see `app.api.routes.pressure`) or a POST with no client-supplied body:
the user always comes from the JWT (`current_user.id`), never from a
request field, so there is nothing here a client could use to read or
modify another user's data.
"""

from __future__ import annotations

from typing import Literal

TrendPeriod = Literal["7d", "30d", "90d"]

ALLOWED_TREND_PERIODS: tuple[TrendPeriod, ...] = ("7d", "30d", "90d")

TrendDimension = Literal["technical", "communication", "interview", "pressure", "overall"]
