"""Helpers the content modules use to turn computed answers into validated question dicts."""

from __future__ import annotations

import hashlib
from fractions import Fraction

from app.services.aptitude.syllabus import SUBTOPIC_TO_TOPIC
from app.services.aptitude.validation import question_id_for


def fnum(x) -> str:
    """Plain number text: integers without decimals, otherwise at most 2 decimals."""
    if isinstance(x, str):
        return x
    if isinstance(x, Fraction):
        x = float(x)
    if isinstance(x, float):
        x = round(x, 2)
        if x == int(x):
            x = int(x)
    return f"{x:,}" if isinstance(x, int) and abs(x) >= 10000 else str(x)


def frac(n: int, d: int) -> str:
    f = Fraction(n, d)
    return f"{f.numerator}/{f.denominator}" if f.denominator != 1 else str(f.numerator)


def rupee(x) -> str:
    return f"₹{fnum(x)}"


def pct(x) -> str:
    return f"{fnum(x)}%"


def X(expression: str, expected) -> dict:
    return {"method": "expression", "expression": expression, "expected": float(expected)}


def E(kind: str, expected, **params) -> dict:
    if isinstance(expected, Fraction):
        expected = float(expected)
    return {"method": "enumeration", "kind": kind, "params": params, "expected": expected}


def M(note: str) -> dict:
    return {"method": "manual_review", "note": note}


def mk(sub, stem, answer, wrong, expl, *, d, ver, typ="direct", formula=None, t=60, fmt=fnum, data=None, texts=False):
    """
    Build one question. `wrong` are plausible distractors (the first three distinct ones that
    differ from the answer are used). The correct option's position is a stable function of the
    statement, so the seed never changes between runs; sessions shuffle options again.
    """
    correct = answer if texts else fmt(answer)
    options, seen = [], {correct.casefold()}
    for w in wrong:
        text = w if texts else fmt(w)
        if text.casefold() not in seen:
            seen.add(text.casefold())
            options.append(text)
        if len(options) == 3:
            break
    if len(options) < 3:
        raise ValueError(f"not enough distinct distractors for: {stem[:60]}")
    idx = int(hashlib.sha1(stem.encode()).hexdigest(), 16) % 4
    options.insert(idx, correct)
    return {
        "question_id": question_id_for(sub, stem, data),
        "topic_id": SUBTOPIC_TO_TOPIC[sub],
        "subtopic_id": sub,
        "question_type": typ,
        "difficulty": d,
        "statement": stem,
        "options": options,
        "correct_index": idx,
        "explanation": f"{expl} Answer: {correct}.",
        "formula": formula,
        "est_time_seconds": t,
        "data": data,
        "status": "active",
        "version": 1,
        "source": "seed",
        "review_status": "unverified",  # set by the seeder after verification
        "verification": ver,
    }
