"""Helpers the content modules use to build question dicts. Nothing here is served until it passes validation."""

from __future__ import annotations

import hashlib

from app.services.dsa.references import run_reference
from app.services.dsa.syllabus import SUBTOPIC_TO_TOPIC
from app.services.dsa.validation import question_id_for

FORMATS = ("conceptual", "scenario", "output", "trace", "complexity", "coding")


def ref(kind: str, **params):
    """(answer text, verification block) for a reference computation."""
    return run_reference(kind, params), {"method": "reference", "kind": kind, "params": params}


def S(expected: str) -> dict:
    """The snippet in the question's `code` field prints `expected`; the test-suite and CLI execute it to confirm."""
    return {"method": "snippet", "expected": expected}


def M(note: str) -> dict:
    return {"method": "manual_review", "note": note}


def _place(stem: str, answer: str, wrong: list[str]):
    options, seen = [], {answer.casefold()}
    for w in wrong:
        if w.casefold() not in seen:
            seen.add(w.casefold())
            options.append(w)
        if len(options) == 3:
            break
    if len(options) < 3:
        raise ValueError(f"not enough distinct distractors for: {stem[:60]}")
    idx = int(hashlib.sha1(stem.encode()).hexdigest(), 16) % 4
    options.insert(idx, answer)
    return options, idx


def mk(sub, fmt, stem, answer, wrong, expl, *, d, ver, code=None, complexity=None, trace=None, t=60,
       hints=None, constraints=None, coding_type=None):
    """One MCQ-style question. `wrong` are plausible distractors; the correct option's position is a stable function of the stem."""
    options, idx = _place(stem, answer, wrong)
    return {
        "question_id": question_id_for(sub, stem, code),
        "topic_id": SUBTOPIC_TO_TOPIC[sub], "subtopic_id": sub, "format": fmt, "interaction": "mcq", "coding_type": coding_type,
        "difficulty": d, "statement": stem, "code": code, "options": options, "correct_index": idx,
        "explanation": f"{expl} Answer: {answer}.", "complexity": complexity, "trace": trace,
        "constraints": constraints, "hints": hints or [], "coding": None, "est_time_seconds": t,
        "status": "active", "version": 1, "source": "seed", "review_status": "unverified", "verification": ver,
    }


def mk_ref(sub, fmt, stem, kind, params, wrong, expl, *, d, **kw):
    """MCQ whose correct answer is computed by a named reference computation."""
    answer, ver = ref(kind, **params)
    return mk(sub, fmt, stem, answer, wrong, expl, d=d, ver=ver, **kw)


def mk_code(sub, stem, spec, expl, *, d, t=420, hints=None, constraints=None, code=None, complexity=None):
    """A write-the-function question (answered with code, self-assessed after submission)."""
    return {
        "question_id": question_id_for(sub, stem, code),
        "topic_id": SUBTOPIC_TO_TOPIC[sub], "subtopic_id": sub, "format": "coding", "interaction": "code", "coding_type": "write_function",
        "difficulty": d, "statement": stem, "code": code, "options": [], "correct_index": None, "explanation": expl,
        "complexity": complexity, "trace": None, "constraints": constraints, "hints": hints or [], "coding": spec,
        "est_time_seconds": t, "status": "active", "version": 1, "source": "seed", "review_status": "unverified",
        "verification": {"method": "tests", "note": "reference solution is executed against every test case by the test suite / CLI"},
    }


def trace_steps(*pairs) -> list[dict]:
    return [{"label": a, "state": b} for a, b in pairs]


def states_trace(states, prefix="After pass"):
    return [{"label": f"{prefix} {i + 1}", "state": str(s)} for i, s in enumerate(states)]
