"""
Question validation: the gate every question must pass before it can be served.

`validate_question` returns a list of problems (empty = valid). Beyond structure it enforces:
  * four distinct options and an unambiguous key (a reference computation must reproduce the key and
    must not match any distractor);
  * every active question carries a verification block;
  * coding questions have parseable template and reference code, at least one hidden test and one edge-case test;
  * nothing claims to come from a real company exam.
Verification methods and what they actually prove:
  reference  - an in-process reference implementation reproduces the answer (checked here, every startup);
  snippet    - the question's `code` prints the expected output; EXECUTED only by the test suite / CLI, never at runtime;
  tests      - the reference solution passes every test case; EXECUTED only by the test suite / CLI;
  manual_review - a human-written justification, no machine check.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re

from pydantic import ValidationError

from app.schemas.dsa import QuestionContent
from app.services.dsa.references import UnknownReference, run_reference
from app.services.dsa.syllabus import SUBTOPIC_TO_TOPIC

_AMBIGUOUS = re.compile(r"\b(all|none|both)\s+of\s+the\s+above\b|\bany\s+of\s+the\s+above\b", re.I)
_REAL_EXAM_CLAIM = re.compile(r"\b(asked in|appeared in|previous year|actual exam|from (tcs|infosys|wipro|accenture|cognizant|google|amazon|microsoft|meta))\b", re.I)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().casefold())


def question_id_for(subtopic_id: str, statement: str, code: str | None = None) -> str:
    """Stable identifier: the same question always gets the same id across seeds and restarts."""
    basis = f"{subtopic_id}|{normalize(statement)}|{normalize(code) if code else ''}"
    return "dsa-" + hashlib.sha1(basis.encode()).hexdigest()[:10]


def fingerprint(doc: dict) -> str:
    basis = "|".join([normalize(doc["statement"]), normalize(doc.get("code") or ""), ",".join(sorted(normalize(o) for o in doc.get("options", [])))])
    return hashlib.sha1(basis.encode()).hexdigest()


def content_hash(doc: dict) -> str:
    keys = ("statement", "code", "options", "correct_index", "explanation", "complexity", "trace", "difficulty", "coding", "hints", "constraints", "est_time_seconds")
    return hashlib.sha1(json.dumps({k: doc.get(k) for k in keys}, sort_keys=True, default=str).encode()).hexdigest()


def verify_question(doc: dict) -> tuple[str, list[str]]:
    """(review_status, problems). Only the machine checks that can run in-process are run here."""
    ver = doc.get("verification")
    if not isinstance(ver, dict) or "method" not in ver:
        return "unverified", ["missing verification block"]
    method = ver["method"]
    if method == "manual_review":
        if len(str(ver.get("note", "")).strip()) < 15:
            return "unverified", ["manual review needs a note explaining the reasoning"]
        return "manual_review", []
    if method == "tests":
        return ("tests_checked", []) if doc.get("interaction") == "code" else ("unverified", ["'tests' verification is only for code questions"])
    if doc.get("interaction") != "mcq":
        return "unverified", [f"method '{method}' applies to MCQs only"]
    options, idx = doc["options"], doc["correct_index"]
    if method == "snippet":
        if not doc.get("code"):
            return "unverified", ["snippet verification needs a code snippet"]
        expected = str(ver.get("expected", ""))
        problems = [] if normalize(options[idx]) == normalize(expected) else [f"marked option '{options[idx]}' is not the declared snippet output '{expected}'"]
        problems += [f"ambiguous: option {i} also equals the snippet output" for i, o in enumerate(options) if i != idx and normalize(o) == normalize(expected)]
        return ("snippet_test_checked" if not problems else "unverified"), problems
    if method == "reference":
        try:
            computed = run_reference(str(ver.get("kind", "")), ver.get("params") or {})
        except UnknownReference as exc:
            return "unverified", [str(exc)]
        problems = []
        if normalize(computed) != normalize(options[idx]):
            problems.append(f"reference result '{computed}' does not equal the marked option '{options[idx]}'")
        problems += [f"ambiguous: option {i} also equals the reference result" for i, o in enumerate(options) if i != idx and normalize(o) == normalize(computed)]
        if "expected" in ver and normalize(ver["expected"]) != normalize(computed):
            problems.append("declared expected value differs from the reference result")
        return ("reference_checked" if not problems else "unverified"), problems
    return "unverified", [f"unknown verification method '{method}'"]


def _validate_coding(doc: dict) -> list[str]:
    spec, problems = doc["coding"], []
    name = spec["function_name"]
    for label, src in (("template", spec["template"]), ("reference solution", spec["reference_solution"])):
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            problems.append(f"{label} is not valid Python: {exc.msg}")
            continue
        if not any(isinstance(n, ast.FunctionDef) and n.name == name for n in ast.walk(tree)):
            problems.append(f"{label} does not define {name}()")
    tests = spec["test_cases"]
    if not any(not t["visible"] for t in tests):
        problems.append("needs at least one hidden test case")
    if not any(t["visible"] for t in tests):
        problems.append("needs at least one visible sample test case")
    if not any(t["edge"] for t in tests):
        problems.append("needs at least one edge-case test (empty / single / duplicate / boundary input)")
    if len({t["label"] for t in tests}) != len(tests):
        problems.append("test case labels must be unique")
    return problems


def validate_question(doc: dict) -> list[str]:
    try:
        q = QuestionContent.model_validate(doc)
    except ValidationError as exc:
        return [f"schema: {e['loc']} {e['msg']}" for e in exc.errors()[:5]]

    problems: list[str] = []
    if SUBTOPIC_TO_TOPIC.get(q.subtopic_id) != q.topic_id:
        problems.append("subtopic does not belong to the topic (or is unknown)")
    if q.question_id != question_id_for(q.subtopic_id, q.statement, q.code):
        problems.append("question_id is not the stable id for this content")
    if _REAL_EXAM_CLAIM.search(" ".join([q.statement, q.explanation, q.code or ""])):
        problems.append("must not claim the question appeared in a real exam")
    if q.format == "complexity" and not (q.complexity and q.complexity.get("time")):
        problems.append("complexity questions need a complexity block with at least 'time'")
    if q.format == "output" and not q.code:
        problems.append("output-prediction questions need a code snippet")

    if q.interaction == "mcq":
        if len({normalize(o) for o in q.options}) != 4:
            problems.append("options must be four distinct values")
        if any(_AMBIGUOUS.search(o) for o in q.options):
            problems.append("'all/none of the above' options are not allowed")
        if normalize(q.options[q.correct_index]) not in normalize(q.explanation):
            problems.append("explanation does not state the correct answer")
    else:
        problems.extend(_validate_coding(doc))

    review, vproblems = verify_question(doc)
    problems.extend(vproblems)
    if q.status == "active" and review == "unverified":
        problems.append("an active question must carry a passing verification")
    return problems
