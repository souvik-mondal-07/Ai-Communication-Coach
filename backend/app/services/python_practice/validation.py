"""
Question validation: the gate every question must pass before it can be served (Phase 26). `validate_question` returns problems (empty = valid).

Beyond structure it enforces:
  * four distinct options, exactly one correct; no "all of the above";
  * every active question carries a verification block that matches how it is graded:
      execution   the stored hash must match `verified.json` written by tools.verify_python_bank, which ran the snippet in the isolated runner;
      reference   expected outputs came from a reference solution AND an independent solution agreed on every case;
      manual      allowed for theory questions; reported separately and never counted as verified;
  * debug/completion starters were shown to fail; reference sources compile and define the entry point;
  * version-sensitive statements declare `python_version`;
  * nothing claims to come from a real company exam;
  * SAFE BY CONSTRUCTION: executable questions (output, trace, coding, debug, complete) never touch the network, subprocesses, eval/exec,
    or the real filesystem outside /tmp -- cybersecurity exercises use offline sample data only.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re

from pydantic import ValidationError

from app.schemas.python_practice import QuestionContent
from app.services.python_practice.content.build import exec_hash, load_manifest, norm
from app.services.python_practice.syllabus import TOPIC_TO_UNIT

_AMBIGUOUS = re.compile(r"\b(all|none|both)\s+of\s+the\s+above\b|\bany\s+of\s+the\s+above\b", re.I)
_REAL_EXAM = re.compile(r"\b(asked in|appeared in|previous year|actual exam|from (tcs|infosys|wipro|accenture|cognizant|google|amazon|microsoft|meta))\b", re.I)
_VERSION_WORDS = re.compile(r"\bPython\s*3\.\d+|\b3\.(8|9|1\d)\+|free-threaded|walrus|match\s+statement|structural pattern|ExceptionGroup|except\*|\btomllib\b|removeprefix|\bTaskGroup\b")
_UNSAFE_EXEC = re.compile(r"\b(socket|requests|urllib\.request|http\.client|subprocess|os\.system|os\.popen|eval|exec|__import__|ctypes|shutil\.rmtree|os\.remove|os\.unlink)\b|open\(\s*['\"]/(?!tmp)")
_EXECUTABLE = {"output", "trace", "coding", "debug", "complete"}


def fingerprint(doc: dict) -> str:
    basis = "|".join([norm(doc["statement"]), norm(doc.get("code") or ""), norm(doc.get("title") or ""), ",".join(sorted(norm(o) for o in doc.get("options", [])))])
    return hashlib.sha1(basis.encode()).hexdigest()


def content_hash(doc: dict) -> str:
    keys = ("statement", "code", "options", "correct_index", "short", "spec", "explanation", "difficulty", "hints", "est_time_seconds", "python_version", "format", "title")
    return hashlib.sha1(json.dumps({k: doc.get(k) for k in keys}, sort_keys=True, default=str).encode()).hexdigest()


def verify_question(doc: dict) -> str:
    """The review status a question has earned (never read from the seed itself)."""
    ver = doc.get("verification") or {}
    method = ver.get("method")
    if method == "execution":
        rec = load_manifest().get(doc["question_id"])
        want = exec_hash(doc.get("code") or "", ver.get("expected_stdout"), ver.get("expected_exception"))
        if rec and rec.get("hash") == want == ver.get("hash") and rec.get("ok") is True:
            return "execution_verified"
        return "unverified"
    if method == "reference":
        if ver.get("independent_solution") and ver.get("tests", 0) >= 6:
            if doc["format"] in ("debug", "complete"):
                rec = load_manifest().get(doc["question_id"])
                if not (rec and rec.get("starter_fails") is True and rec.get("starter_hash") == ver.get("starter_hash") and rec.get("reference_passes") is True):
                    return "unverified"
            return "reference_verified"
        return "unverified"
    if method == "manual_review":
        return "manual_review"
    return "unverified"


def validate_question(doc: dict) -> list[str]:
    problems: list[str] = []
    try:
        q = QuestionContent(**{k: v for k, v in doc.items() if k not in ("fingerprint", "content_hash")})
    except ValidationError as exc:
        return [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()][:6]
    if q.topic_id not in TOPIC_TO_UNIT or TOPIC_TO_UNIT[q.topic_id] != q.unit_id:
        problems.append("topic and unit do not match the syllabus")
    if (ver := doc.get("verification") or {}).get("method") == "failed":
        problems.extend(ver.get("problems", ["build verification failed"]))
    if doc.get("review_status") in (None, "unverified"):
        problems.append("question is not verified (run tools.verify_python_bank for execution-checked questions)")
    text = " ".join([q.statement, q.explanation, *q.options])
    if _REAL_EXAM.search(text):
        problems.append("claims to come from a real company or exam")
    if (_VERSION_WORDS.search(text) or re.search(r":=|\bmatch\s+\w+:|\bexcept\*", q.code or "")) and not q.python_version:
        problems.append("mentions a version-sensitive feature but declares no python_version")
    if q.interaction == "mcq":
        opts = [norm(o) for o in q.options]
        if len(set(opts)) != 4:
            problems.append("options are not distinct")
        if any(_AMBIGUOUS.search(o) for o in q.options):
            problems.append("ambiguous 'of the above' option")
        if q.correct_index is not None and norm(q.explanation) == opts[q.correct_index]:
            problems.append("explanation only repeats the answer")
    if q.format in _EXECUTABLE:
        blob = " ".join([q.code or "", q.spec.starter if q.spec else "", q.spec.reference_source if q.spec else ""])
        if _UNSAFE_EXEC.search(blob):
            problems.append("executable question uses a forbidden facility (network, subprocess, eval/exec, or real filesystem)")
    if q.spec:
        for name, src in (("reference", q.spec.reference_source), ("starter", q.spec.starter if q.format == "debug" else None)):
            if src:
                try:
                    ast.parse(src, filename=f"<{name}>")  # syntax check only: nothing is compiled to code or run
                except SyntaxError:
                    problems.append(f"{name} source does not compile")
        if not re.search(rf"\b(def|class)\s+{re.escape(q.spec.entry)}\b", q.spec.reference_source):
            problems.append("reference source does not define the entry point")
        if q.format in ("coding",) and q.spec.entry not in q.spec.starter:
            problems.append("starter does not mention the entry point")
    if q.format == "output" and q.interaction != "code" and not q.code:
        problems.append("output question without code")
    if len(q.hints) < (1 if q.interaction == "code" else 0):
        problems.append("coding questions need at least one hint")
    return problems
