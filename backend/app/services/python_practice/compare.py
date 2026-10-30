"""
Deterministic grading helpers for Python practice (Phase 26). Pure functions: no I/O, no submitted code.

Raw sandbox outputs arrive as tagged JSON (see sandbox/harness.py `to_jsonable`). Expected values are produced by the SAME function
from trusted reference solutions, so both sides use one canonical form. Comparison policy:

  * bool is never equal to an int (True != 1); int and float compare by numeric value;
  * tuples and lists are interchangeable unless the problem says otherwise (`strict_types`);
  * `unordered` treats the top-level list as a multiset; `set_like` ignores order and duplicates; `float` uses an absolute+relative tolerance;
  * `text` ignores trailing whitespace on each line and surrounding blank lines (for stdio programs);
  * `validator` calls a named, trusted checker on (inputs, actual) for problems with many valid answers.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Callable

CompareMode = str  # exact | unordered | set_like | float | text | validator

VALIDATORS: dict[str, Callable[[dict, Any], bool]] = {}


def register_validator(name: str):
    def deco(fn):
        VALIDATORS[name] = fn
        return fn
    return deco


def _plain(v: Any) -> Any:
    """Strip the tuple tag so lists and tuples compare alike."""
    if isinstance(v, dict):
        if set(v) == {"__tuple__"}:
            return [_plain(x) for x in v["__tuple__"]]
        return {k: _plain(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_plain(x) for x in v]
    return v


def _key(v: Any) -> str:
    return json.dumps(_plain(v), sort_keys=True, default=str)


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _eq(a: Any, b: Any, tol: float | None, strict_types: bool) -> bool:
    if not strict_types:
        a, b = _plain(a), _plain(b)
    if _num(a) and _num(b):
        if tol is not None:
            return math.isclose(a, b, rel_tol=tol, abs_tol=tol)
        if strict_types and type(a) is not type(b):
            return False
        return a == b
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_eq(x, y, tol, strict_types) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(_eq(a[k], b[k], tol, strict_types) for k in a)
    return type(a) is type(b) and a == b


def normalize_text(text: str) -> str:
    lines = [ln.rstrip() for ln in str(text).replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return "\n".join(lines)


def values_match(actual: Any, expected: Any, mode: CompareMode = "exact", tolerance: float | None = None, strict_types: bool = False) -> bool:
    if mode == "text":
        return normalize_text(actual if isinstance(actual, str) else "") == normalize_text(expected)
    if mode == "unordered":
        a, e = _plain(actual), _plain(expected)
        if not isinstance(a, list) or not isinstance(e, list):
            return _eq(a, e, tolerance, strict_types)
        return sorted(map(_key, a)) == sorted(map(_key, e))
    if mode == "set_like":
        a, e = _plain(actual), _plain(expected)
        ua = a["__set__"] if isinstance(a, dict) and "__set__" in a else a
        ue = e["__set__"] if isinstance(e, dict) and "__set__" in e else e
        if not isinstance(ua, list) or not isinstance(ue, list):
            return False
        return {_key(x) for x in ua} == {_key(x) for x in ue}
    if mode == "float":
        return _eq(actual, expected, tolerance if tolerance is not None else 1e-6, strict_types)
    return _eq(actual, expected, None, strict_types)


def describe(value: Any, limit: int = 160) -> str:
    """Short human rendering of a tagged value for failure messages (visible cases only)."""
    def render(v: Any) -> Any:
        if isinstance(v, dict):
            if set(v) == {"__tuple__"}:
                return tuple(render(x) for x in v["__tuple__"])
            if set(v) == {"__set__"}:
                return {json.dumps(render(x)) for x in v["__set__"]}
            if set(v) == {"__dict__"}:
                return {json.dumps(render(k)): render(x) for k, x in v["__dict__"]}
            if set(v) == {"__repr__"}:
                return v["__repr__"]
            return {k: render(x) for k, x in v.items()}
        if isinstance(v, list):
            return [render(x) for x in v]
        return v
    text = repr(render(value))
    return text if len(text) <= limit else text[: limit - 1] + "…"


# --- short answers ----------------------------------------------------------------------------------------------------------

def normalize_short(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().casefold())


def grade_short(spec: dict, given: str) -> bool:
    """`spec`: {"kind": "text"|"number"|"output", "value": [accepted...]}. Deterministic; never calls an AI."""
    given = str(given or "")
    if not given.strip():
        return False
    kind = spec["kind"]
    accepted = [str(v) for v in spec["value"]]
    if kind == "number":
        try:
            g = float(given.strip().replace(",", ""))
        except ValueError:
            return False
        return any(abs(g - float(a)) < 1e-9 for a in accepted)
    if kind == "output":
        def lines(t: str) -> list[str]:
            return [ln.strip() for ln in normalize_text(t).split("\n")]  # stray spaces around a typed line are not a wrong answer
        g = lines(given)
        return any(g == lines(a) for a in accepted)
    return normalize_short(given) in {normalize_short(a) for a in accepted}


def canonical_short(spec: dict) -> str:
    return str(spec["value"][0])
