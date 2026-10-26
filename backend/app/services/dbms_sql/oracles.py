"""
Independent oracles for SQL questions (Phase 25).

Each SQL exercise or SQL-output question registers a small pure-Python function that derives the expected answer from the
RAW dataset rows (lists of dicts), without SQL. Validation requires the SQL engine's result for the reference query to equal
the oracle's, so an expected result is confirmed by two unrelated derivations (the engine, and hand-written Python).
"""

from __future__ import annotations

import re
from typing import Any, Callable

from app.services.dbms_sql.sql_compare import fmt_value

Tables = dict[str, list[dict[str, Any]]]
ORACLES: dict[str, Callable[[Tables], Any]] = {}


def register(key: str, fn: Callable[[Tables], Any]) -> None:
    ORACLES[key] = fn  # idempotent: the content builders re-run on every call; duplicate questions are rejected by the bank itself


def render(columns: list[str], rows: list[list[Any]], mode: str) -> str:
    """Canonical text of a result, used to compare engine output with a multiple-choice option."""
    if mode == "scalar":
        return fmt_value(rows[0][0]) if rows and rows[0] else "(no rows)"
    if mode == "column":
        return ", ".join(fmt_value(r[0]) for r in rows) if rows else "(no rows)"
    if mode == "count":
        return str(len(rows))
    if mode == "rows":
        return "; ".join("(" + ", ".join(fmt_value(v) for v in r) + ")" for r in rows) if rows else "(no rows)"
    raise ValueError(f"unknown render mode {mode}")


_PLAN_USING = re.compile(r"\b(SEARCH|SCAN)\b.*?(USING (COVERING INDEX|INDEX|INTEGER PRIMARY KEY|PRIMARY KEY))?", re.I)


def plan_kind(details: list[str]) -> str:
    """Classify a one-table EXPLAIN QUERY PLAN into a stable label (SQLite wording differs slightly across versions)."""
    text = " | ".join(details).upper()
    if "SCAN" in text and "USING COVERING INDEX" not in text and "USING INDEX" not in text:
        return "Full table scan"
    if "SEARCH" in text and "USING COVERING INDEX" in text:
        return "Covering index search"
    if "SEARCH" in text and ("INTEGER PRIMARY KEY" in text or "PRIMARY KEY" in text):
        return "Primary key lookup"
    if "SEARCH" in text and "USING INDEX" in text:
        return "Index search"
    if "SCAN" in text and "COVERING INDEX" in text:
        return "Full covering-index scan"
    return "Other plan"
