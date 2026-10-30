"""
Builders for Python practice seed questions. They only assemble dicts; `validation` decides whether each one may be served.

Verification, by question kind:
  mcq (theory)     manual_review: written by maintainers, no executable check. Reported separately; never counted as verified.
  out / trace      execution_verified: `tools.verify_python_bank` ran the snippet in the isolated runner and recorded what it printed
                   (or the exception it raised) in `verified.json`; the stored hash must match, so editing a snippet un-verifies it.
  code             reference_verified: expected outputs are COMPUTED by running a trusted reference solution (a real function in this
                   repo), and an independent brute-force/alternative solution must agree on every test case, or the build records
                   a failed verification and the question is rejected. Debug and completion starters must be shown to fail.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import re
import textwrap
from pathlib import Path
from typing import Any, Callable

from app.services.python_practice import compare
from app.services.python_practice.sandbox.harness import to_jsonable
from app.services.python_practice.syllabus import TOPIC_TO_UNIT

MANIFEST_PATH = Path(__file__).with_name("verified.json")
MANUAL_NOTE = "Written by the maintainers; no executable check exists. Needs subject-expert sign-off before it is treated as authoritative."


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().casefold())


def question_id_for(topic_id: str, statement: str, code: str | None = None) -> str:
    return "pyq-" + hashlib.sha1(f"{topic_id}|{norm(statement)}|{norm(code) if code else ''}".encode()).hexdigest()[:10]


def exec_hash(code: str, expected_stdout: str | None, exc: str | None, starter: str | None = None) -> str:
    return hashlib.sha1(json.dumps([code, expected_stdout, exc, starter], sort_keys=True).encode()).hexdigest()


def _place(statement: str, correct: str, wrong: list[str]) -> tuple[list[str], int]:
    """Put the correct option at a position derived from the statement, so the stored order does not leak the key."""
    pos = int(hashlib.sha1(statement.encode()).hexdigest(), 16) % 4
    options = list(wrong)
    options.insert(pos, correct)
    return options, pos


def _base(topic: str, diff: str, fmt: str, stmt: str, expl: str, *, code=None, hints=(), est=45, tags=(), py=None, title=None) -> dict[str, Any]:
    return {
        "question_id": question_id_for(topic, stmt, code), "unit_id": TOPIC_TO_UNIT[topic], "topic_id": topic, "format": fmt, "difficulty": diff, "title": title,
        "statement": stmt, "code": code, "explanation": expl, "hints": list(hints), "est_time_seconds": est, "tags": list(tags), "python_version": py,
        "status": "active", "version": 1, "source": "seed", "review_status": "unverified",
    }


def mcq(topic: str, diff: str, stmt: str, correct: str, wrong: list[str], expl: str, *, fmt: str = "concept", code: str | None = None,
        hints: tuple[str, ...] = (), est: int = 45, tags: tuple[str, ...] = (), py: str | None = None) -> dict[str, Any]:
    assert len(wrong) == 3, stmt
    options, idx = _place(stmt, correct, wrong)
    doc = _base(topic, diff, fmt, stmt, expl, code=code, hints=hints, est=est, tags=tags, py=py)
    doc.update({"interaction": "mcq", "options": options, "correct_index": idx, "verification": {"method": "manual_review", "note": MANUAL_NOTE}})
    return doc


def render_output(stdout: str) -> str:
    """How printed output appears as an option: lines joined with ' | '."""
    lines = stdout.rstrip("\n").split("\n")
    return " | ".join(lines)


def out(topic: str, diff: str, stmt: str, code: str, expected: str, wrong: list[str], expl: str, *, fmt: str = "output", exc: str | None = None,
        hints: tuple[str, ...] = (), est: int = 60, tags: tuple[str, ...] = (), py: str | None = None, typed: bool = False) -> dict[str, Any]:
    """Predict-the-output question. `expected` is what the snippet prints (or, with `exc`, the exception class it raises uncaught).
    Verified by execution: the runner must reproduce it exactly (see tools.verify_python_bank)."""
    code = textwrap.dedent(code).strip("\n")
    doc = _base(topic, diff, fmt, stmt, expl, code=code, hints=hints, est=est, tags=tags, py=py)
    shown = exc if exc else render_output(expected)
    ver = {"method": "execution", "expected_stdout": None if exc else expected, "expected_exception": exc, "hash": exec_hash(code, None if exc else expected, exc)}
    if typed:
        doc.update({"interaction": "short", "short": {"kind": "output" if not exc else "text", "value": [shown if exc else expected.rstrip("\n")],
                                                      "help": "Type exactly what is printed (one line per line)." if not exc else "Type the exception class name."}, "verification": ver})
    else:
        assert len(wrong) == 3, stmt
        options, idx = _place(stmt, shown, wrong)
        doc.update({"interaction": "mcq", "options": options, "correct_index": idx, "verification": ver})
    return doc


# --- Coding challenges -------------------------------------------------------------------------------------------------------


def _ref_source(fn: Callable | type, entry: str, imports: tuple[str, ...]) -> str:
    src = textwrap.dedent(inspect.getsource(fn)).rstrip() + "\n"
    src = re.sub(rf"\b{re.escape(fn.__name__)}\b", entry, src)
    return ("\n".join(imports) + "\n\n" if imports else "") + src


class BuildError(Exception):
    pass


def _in_process(ref: Callable, mode: str, case: Any) -> Any:
    """Trusted reference code run in the build process to compute expected values. Never receives user input."""
    if mode == "function":
        args, kwargs = case
        return to_jsonable(ref(*copy.deepcopy(args), **copy.deepcopy(kwargs)))
    if mode == "class":
        ctor, ops = case
        obj = ref(*copy.deepcopy(ctor))
        return to_jsonable([getattr(obj, name)(*copy.deepcopy(a)) for name, a in ops])
    return ref(case)  # stdio: ref(stdin_text) -> stdout text


def code_q(topic: str, diff: str, fmt: str, title: str, stmt: str, entry: str, signature: str, starter: str, ref: Callable | type, alt: Callable | type | None,
           cases: list, *, mode: str = "function", visible: int = 2, compare_mode: str = "exact", tolerance: float | None = None, strict_types: bool = False,
           validator: str | None = None, constraints: tuple[str, ...] = (), time_c: str, space_c: str, expl: str, hints: tuple[str, ...] = (),
           imports: tuple[str, ...] = (), est: int = 600, tags: tuple[str, ...] = (), py: str | None = None, labels: tuple[str, ...] = ()) -> dict[str, Any]:
    """A coding / debug / completion exercise graded by running tests in the sandbox.
    `cases`: function mode -> an args tuple, or {"args": (...), "kwargs": {...}}; class mode -> (ctor_list, ops); stdio mode -> stdin text.
    The first `visible` cases are the shown examples; the rest are hidden (edge and larger cases)."""
    starter = textwrap.dedent(starter).strip("\n") + "\n"
    stmt_code = None
    tests, failures = [], []
    for i, raw in enumerate(cases):
        if mode == "function":
            args, kwargs = (raw["args"], raw.get("kwargs", {})) if isinstance(raw, dict) else (raw, {})
            case = (list(args), kwargs)
            shown = f"{entry}({', '.join([repr(a) for a in args] + [f'{k}={v!r}' for k, v in kwargs.items()])})"
            t = {"id": i, "args": list(args), "kwargs": kwargs, "input_repr": shown[:300]}
        elif mode == "class":
            ctor, ops = raw
            case = (ctor, ops)
            shown = f"{entry}({', '.join(map(repr, ctor))}) then " + ", ".join(f"{n}({', '.join(map(repr, a))})" for n, a in ops)
            t = {"id": i, "ctor": list(ctor), "ops": [[n, list(a)] for n, a in ops], "input_repr": shown[:300]}
        else:
            case = raw
            t = {"id": i, "stdin": raw, "input_repr": raw.replace("\n", "\\n")[:300]}
        expected = _in_process(ref, mode, case)
        if alt is not None and compare_mode != "validator":
            other = _in_process(alt, mode, case)
            same = compare.normalize_text(other) == compare.normalize_text(expected) if mode == "stdio" else compare.values_match(other, expected, compare_mode, tolerance, strict_types)
            if not same:
                failures.append(f"case {i}: reference and independent solution disagree")
        if compare_mode == "validator":
            checker = compare.VALIDATORS[validator or ""]
            if not checker({"args": t.get("args", []), "kwargs": t.get("kwargs", {})}, expected):
                failures.append(f"case {i}: validator rejects the reference output")
        t.update({"expected": expected, "visible": i < visible, "label": (labels[i] if i < len(labels) else (f"Example {i + 1}" if i < visible else f"Case {i + 1}"))})
        tests.append(t)
    spec = {"mode": mode, "entry": entry, "signature": signature, "starter": starter, "constraints": list(constraints), "compare": compare_mode, "tolerance": tolerance,
            "strict_types": strict_types, "validator": validator, "tests": tests, "reference_source": _ref_source(ref, entry, imports), "time_complexity": time_c, "space_complexity": space_c}
    doc = _base(topic, diff, fmt, stmt, expl, code=stmt_code, hints=hints, est=est, tags=tags, py=py, title=title)
    doc["question_id"] = question_id_for(topic, stmt + "|" + title)
    ver: dict[str, Any] = {"method": "reference", "tests": len(tests), "independent_solution": alt is not None or compare_mode == "validator"}
    if alt is None and compare_mode != "validator":
        failures.append("no independent solution to cross-check the reference")
    if failures:
        ver = {"method": "failed", "problems": failures[:5]}
    elif fmt in ("debug", "complete"):
        ver["starter_hash"] = exec_hash("", None, None, starter)
    doc.update({"interaction": "code", "spec": spec, "verification": ver})
    return doc


def load_manifest() -> dict[str, Any]:
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
