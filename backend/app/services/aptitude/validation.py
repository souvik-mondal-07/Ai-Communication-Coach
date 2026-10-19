"""
Question validation: the gate every question must pass before it can be served.

`validate_question` returns a list of problems (empty means valid). It checks structure, four
distinct options, the answer key, explanation/answer consistency, ambiguity red flags and --
most importantly -- re-derives the answer independently (`verify_question`).
"""

from __future__ import annotations

import hashlib
import json
import re

from pydantic import ValidationError

from app.schemas.aptitude import QuestionContent
from app.services.aptitude.safe_eval import UnsafeExpressionError, parse_number, safe_eval
from app.services.aptitude.syllabus import SUBTOPIC_TO_TOPIC
from app.services.aptitude.verifiers import VerificationError, run_verifier

_AMBIGUOUS_OPTIONS = re.compile(r"\b(all|none|both)\s+of\s+the\s+above\b|\bany\s+of\s+the\s+above\b", re.I)
_NEGATIVE_WORDS = re.compile(r"\b(decrease|decrement|loss|fall|reduction|lower|less)\b", re.I)
_REAL_EXAM_CLAIM = re.compile(r"\b(asked in|appeared in|previous year|actual exam|from (tcs|infosys|wipro|accenture|cognizant))\b", re.I)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().casefold())


def question_id_for(subtopic_id: str, statement: str, data: dict | None = None) -> str:
    """Stable identifier: the same question always gets the same id, across seeds and restarts."""
    basis = f"{subtopic_id}|{normalize(statement)}|{json.dumps(data, sort_keys=True) if data else ''}"
    return "apt-" + hashlib.sha1(basis.encode()).hexdigest()[:10]


def fingerprint(doc: dict) -> str:
    """Content fingerprint used to block duplicates (same statement + same option set + same data)."""
    basis = "|".join([
        normalize(doc["statement"]),
        ",".join(sorted(normalize(o) for o in doc["options"])),
        json.dumps(doc.get("data"), sort_keys=True) if doc.get("data") else "",
    ])
    return hashlib.sha1(basis.encode()).hexdigest()


def content_hash(doc: dict) -> str:
    """Detects an edited seed so its version can be bumped."""
    keys = ("statement", "options", "correct_index", "explanation", "formula", "difficulty", "data", "est_time_seconds")
    return hashlib.sha1(json.dumps({k: doc.get(k) for k in keys}, sort_keys=True, default=str).encode()).hexdigest()


def _decimal_tolerance(value: float) -> float:
    """Rounding allowance for a displayed decimal: 2 places, but never coarser than 0.5% of the value."""
    return min(0.0051, 0.005 * abs(value))


def _matches(option: str, expected) -> bool:
    if isinstance(expected, bool):
        return False
    if isinstance(expected, (int, float)):
        value = parse_number(option)
        if value is None:
            return False
        if _NEGATIVE_WORDS.search(option):
            value = -abs(value)  # "4% loss" / "1% decrease" denote negative change
        exp = float(expected)
        if exp == int(exp):
            return value == exp  # integer answers must match exactly
        return abs(value - exp) <= _decimal_tolerance(exp)  # decimals are shown rounded to 2 places
    return normalize(option) == normalize(str(expected))


def verify_question(doc: dict) -> tuple[str, list[str]]:
    """
    Returns (review_status, problems). `verified` means an independent computation reproduced the
    answer key; `manual_review` means no machine check exists (a human must vouch for it).
    """
    ver = doc.get("verification")
    if not isinstance(ver, dict) or "method" not in ver:
        return "unverified", ["missing verification block"]
    method = ver["method"]
    if method == "manual_review":
        if not str(ver.get("note", "")).strip():
            return "unverified", ["manual review needs a note explaining the reasoning"]
        return "manual_review", []
    expected = ver.get("expected")
    try:
        if method == "expression":
            computed = safe_eval(str(ver.get("expression", "")))
        elif method == "enumeration":
            computed = run_verifier(str(ver.get("kind", "")), ver.get("params") or {})
        else:
            return "unverified", [f"unknown verification method '{method}'"]
    except (UnsafeExpressionError, VerificationError, KeyError, TypeError, ValueError) as exc:
        return "unverified", [f"verification failed: {exc}"]

    problems: list[str] = []
    if isinstance(computed, (int, float)) and not isinstance(computed, bool) and isinstance(expected, (int, float)):
        tol = 1e-6 if float(expected) == int(float(expected)) else _decimal_tolerance(float(expected))
        if abs(float(computed) - float(expected)) > tol:
            problems.append(f"independent result {computed} does not equal the declared answer {expected}")
    elif normalize(str(computed)) != normalize(str(expected)):
        problems.append(f"independent result '{computed}' does not equal the declared answer '{expected}'")

    options, idx = doc["options"], doc["correct_index"]
    if not _matches(options[idx], computed):
        problems.append(f"the marked correct option '{options[idx]}' does not match the independent result '{computed}'")
    clashes = [o for i, o in enumerate(options) if i != idx and _matches(o, computed)]
    if clashes:
        problems.append(f"ambiguous: other option(s) {clashes} also equal the correct value")
    return ("verified" if not problems else "unverified"), problems


def validate_question(doc: dict) -> list[str]:
    """Full validation. Mutates nothing; returns human-readable problems."""
    try:
        q = QuestionContent.model_validate(doc)
    except ValidationError as exc:
        return [f"schema: {e['loc']} {e['msg']}" for e in exc.errors()[:5]]

    problems: list[str] = []
    if SUBTOPIC_TO_TOPIC.get(q.subtopic_id) != q.topic_id:
        problems.append("subtopic does not belong to the topic (or is unknown)")
    if len({normalize(o) for o in q.options}) != 4:
        problems.append("options must be four distinct values")
    if any(_AMBIGUOUS_OPTIONS.search(o) for o in q.options):
        problems.append("'all/none of the above' options are not allowed")
    if normalize(q.options[q.correct_index]) not in normalize(q.explanation):
        problems.append("explanation does not state the correct answer")
    if _REAL_EXAM_CLAIM.search(q.statement + " " + q.explanation):
        problems.append("must not claim the question appeared in a real exam")
    if q.question_type == "data_interpretation" and not q.data:
        problems.append("data interpretation questions need chart/table data")
    if q.question_id != question_id_for(q.subtopic_id, q.statement, q.data):
        problems.append("question_id is not the stable id for this content")

    review, vproblems = verify_question(doc)
    problems.extend(vproblems)
    if q.status == "active" and review == "unverified":
        problems.append("an active question must be verified or manually reviewed")
    return problems
