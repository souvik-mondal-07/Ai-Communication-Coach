"""
Deterministic SQL result comparison and feedback (Phase 25).

A submitted query is judged by its RESULT on the supplied dataset, never by its text, so an equivalent query (JOIN vs
subquery, different aliases, extra whitespace) is not marked wrong.

Rules (per exercise, from its sql spec):
  * columns are compared by position; names are compared (case-insensitively) only when `check_column_names` is set;
  * rows are compared as a MULTISET (duplicates matter) unless `ordered` is set, in which case sequence matters;
  * NULL equals NULL only; numbers compare numerically after rounding to `precision` places (so 60000 == 60000.0);
  * strings compare exactly (case-sensitive).
Feedback is produced from the comparison plus light, clearly-worded heuristics about the SQL text. Heuristics say
"possible cause"; they never claim certainty.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

MAX_SHOWN_ROWS = 20
MAX_DIFF_ROWS = 5


def _key(value: Any, precision: int) -> tuple[int, Any]:
    if value is None:
        return (0, "")
    if isinstance(value, bool):
        return (1, float(value))
    if isinstance(value, (int, float)):
        return (1, round(float(value), precision) + 0.0)
    return (2, str(value))


def _row_key(row: list[Any] | tuple[Any, ...], precision: int) -> tuple[tuple[int, Any], ...]:
    return tuple(_key(v, precision) for v in row)


def fmt_value(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, float):
        return f"{value:.6g}" if abs(value) >= 1e6 or (value and abs(value) < 1e-4) else f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def fmt_row(row: list[Any] | tuple[Any, ...]) -> str:
    return "(" + ", ".join(fmt_value(v) for v in row) + ")"


@dataclass
class Verdict:
    correct: bool
    code: str  # correct | column_count | column_names | row_count | values | order
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"correct": self.correct, "code": self.code, "messages": self.messages}


def compare(actual_cols: list[str], actual_rows: list[list[Any]], expected_cols: list[str], expected_rows: list[list[Any]],
            *, ordered: bool = False, check_column_names: bool = False, precision: int = 2, sql: str = "") -> Verdict:
    """Compare a user result with the verified expected result."""
    if len(actual_cols) != len(expected_cols):
        return Verdict(False, "column_count", [
            f"Your query returns {len(actual_cols)} column(s) but the task expects {len(expected_cols)}: {', '.join(expected_cols)}.",
            "Select only the requested columns, in the requested order.",
        ])
    names_ok = [a.lower() for a in actual_cols] == [e.lower() for e in expected_cols]
    a_keys = [_row_key(r, precision) for r in actual_rows]
    e_keys = [_row_key(r, precision) for r in expected_rows]
    same_multiset = Counter(a_keys) == Counter(e_keys)

    if check_column_names and not names_ok:
        msg = [f"Column names differ. Expected: {', '.join(expected_cols)}; yours: {', '.join(actual_cols)}.", "Give each output column the requested name with AS."]
        if same_multiset:
            msg.insert(0, "The values are right, only the column names differ.")
        return Verdict(False, "column_names", msg)

    if same_multiset:
        if ordered and a_keys != e_keys:
            msg = ["The rows are correct but not in the required order."]
            msg.append("Check the ORDER BY columns, their ASC/DESC direction and any tie-breaker." if re.search(r"\border\s+by\b", sql, re.I) else "Your query has no ORDER BY clause.")
            return Verdict(False, "order", msg)
        return Verdict(True, "correct", ["Your result matches the expected result."])

    a_count, e_count = Counter(a_keys), Counter(e_keys)
    extra = list((a_count - e_count).elements())
    missing = list((e_count - a_count).elements())
    msgs: list[str] = []
    if len(actual_rows) != len(expected_rows):
        word = "more" if len(actual_rows) > len(expected_rows) else "fewer"
        msgs.append(f"Your query returned {len(actual_rows)} row(s); the expected result has {len(expected_rows)} ({word} than expected).")
    else:
        msgs.append("The number of rows is right but some values differ.")
    if extra:
        msgs.append("Unexpected rows, e.g. " + "; ".join(_show(k) for k in extra[:MAX_DIFF_ROWS]) + ".")
    if missing:
        msgs.append("Missing rows, e.g. " + "; ".join(_show(k) for k in missing[:MAX_DIFF_ROWS]) + ".")
    msgs.extend(_heuristics(sql, actual_rows, expected_rows, a_keys, len(actual_rows) > len(expected_rows), len(actual_rows) < len(expected_rows)))
    code = "row_count" if len(actual_rows) != len(expected_rows) else "values"
    return Verdict(False, code, msgs)


def _show(key: tuple[tuple[int, Any], ...]) -> str:
    def one(k: tuple[int, Any]) -> str:
        if k[0] == 0:
            return "NULL"
        if k[0] == 1:
            return fmt_value(k[1] if k[1] != int(k[1]) else int(k[1]))
        return str(k[1])
    return "(" + ", ".join(one(k) for k in key) + ")"


def _heuristics(sql: str, actual_rows, expected_rows, a_keys, too_many: bool, too_few: bool) -> list[str]:
    s = sql or ""
    up = re.sub(r"\s+", " ", s.upper())
    out: list[str] = []
    has = lambda pat: re.search(pat, up) is not None  # noqa: E731
    if too_many and len(set(a_keys)) < len(a_keys) and not has(r"\bDISTINCT\b") and not has(r"\bGROUP BY\b"):
        out.append("Possible cause: duplicate rows in your result. DISTINCT or GROUP BY removes them.")
    if too_many and has(r"\bJOIN\b"):
        out.append("Possible cause: a join can repeat a row once per match. Check the join condition and whether a filter is missing.")
    if too_many and not has(r"\bWHERE\b") and not has(r"\bHAVING\b") and not has(r"\bJOIN\b"):
        out.append("Possible cause: no filter. Is a WHERE or HAVING condition needed?")
    if too_few and has(r"\bJOIN\b") and not has(r"\b(LEFT|RIGHT|FULL)\b"):
        out.append("Possible cause: an INNER JOIN drops rows with no match. If unmatched rows should appear, use a LEFT JOIN.")
    if too_few and has(r"\bWHERE\b"):
        out.append("Possible cause: the WHERE filter is too strict. Check > versus >=, AND versus OR, and NULL values (NULL is never equal to anything).")
    if has(r"\bGROUP BY\b") or has(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\("):
        out.append("Check the grouping and aggregate: COUNT(col) ignores NULLs while COUNT(*) does not; every non-aggregated column must be in GROUP BY.")
    if any(v is None for r in list(actual_rows) + list(expected_rows) for v in r):
        out.append("NULL handling matters here: use IS NULL / IS NOT NULL, and COALESCE if a default is required.")
    return out[:4]


def result_payload(columns: list[str], rows: list[list[Any]], limit: int = MAX_SHOWN_ROWS) -> dict[str, Any]:
    return {"columns": list(columns), "rows": [list(r) for r in rows[:limit]], "row_count": len(rows), "truncated": len(rows) > limit}


# --- Short answers ---------------------------------------------------------------------------------------------


def parse_attrs(text: str) -> frozenset[str]:
    """'a, B c' -> {'A','B','C'} (single-letter attributes)."""
    return frozenset(ch for ch in (text or "").upper() if ch.isalpha())


def parse_keys(text: str) -> frozenset[frozenset[str]]:
    """'AB, CD' or 'AB; C' -> {{A,B},{C,D}}."""
    parts = [p for p in re.split(r"[,;]", text or "") if p.strip()]
    return frozenset(frozenset(ch for ch in p.upper() if ch.isalpha()) for p in parts if any(c.isalpha() for c in p))


def parse_number(text: str) -> float | None:
    try:
        return float((text or "").strip().replace(",", ""))
    except ValueError:
        return None


def grade_short(kind: str, expected: Any, given: str | None) -> bool:
    if given is None or not given.strip():
        return False
    if kind == "attrs":
        return parse_attrs(given) == frozenset(str(x).upper() for x in expected) and bool(parse_attrs(given))
    if kind == "keys":
        want = frozenset(frozenset(ch for ch in str(k).upper() if ch.isalpha()) for k in expected)
        return parse_keys(given) == want and bool(want)
    if kind == "number":
        v = parse_number(given)
        return v is not None and abs(v - float(expected)) < 1e-9
    return False


def canonical_short(kind: str, expected: Any) -> str:
    if kind == "attrs":
        return "{" + ", ".join(sorted(str(x).upper() for x in expected)) + "}"
    if kind == "keys":
        return ", ".join("{" + ", ".join(sorted(k)) + "}" for k in sorted(("".join(sorted(str(x).upper())) for x in expected)))
    return fmt_value(float(expected) if float(expected) != int(float(expected)) else int(float(expected)))
