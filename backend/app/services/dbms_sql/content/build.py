"""Builders for DBMS & SQL seed questions. They only assemble dicts; `validation` decides whether each one may be served."""

from __future__ import annotations

import hashlib
from typing import Any, Callable

from app.services.dbms_sql import datasets, oracles, sandbox
from app.services.dbms_sql.syllabus import TOPIC_TO_UNIT
from app.services.dbms_sql.validation import question_id_for

MANUAL_NOTE = "Definition-level fact written by the maintainers; no executable check exists. Needs subject-expert sign-off before it is treated as authoritative."


def _place(statement: str, correct: str, wrong: list[str]) -> tuple[list[str], int]:
    """Put the correct option at a position derived from the statement so stored order does not leak the key."""
    pos = int(hashlib.sha1(statement.encode()).hexdigest(), 16) % 4
    options = list(wrong)
    options.insert(pos, correct)
    return options, pos


def _base(topic: str, diff: str, fmt: str, stmt: str, expl: str, *, code=None, dialect="standard", hints=(), est=45, tags=(), requires=(), dataset=None) -> dict[str, Any]:
    return {
        "question_id": question_id_for(topic, stmt, code), "unit_id": TOPIC_TO_UNIT[topic], "topic_id": topic, "format": fmt, "dialect": dialect,
        "difficulty": diff, "statement": stmt, "code": code, "dataset_id": dataset, "explanation": expl, "hints": list(hints), "est_time_seconds": est,
        "tags": list(tags), "requires": list(requires), "status": "active", "version": 1, "source": "seed", "review_status": "unverified",
    }


def mcq(topic: str, diff: str, stmt: str, correct: str, wrong: list[str], expl: str, *, fmt: str = "concept", dialect: str = "standard", code: str | None = None,
        hints: tuple[str, ...] = (), est: int = 45, tags: tuple[str, ...] = (), ref: tuple[str, dict] | None = None, note: str | None = None,
        verify: dict[str, Any] | None = None, requires: tuple[str, ...] = (), extra: dict[str, Any] | None = None) -> dict[str, Any]:
    assert len(wrong) == 3, stmt
    options, idx = _place(stmt, correct, wrong)
    doc = _base(topic, diff, fmt, stmt, expl, code=code, dialect=dialect, hints=hints, est=est, tags=tags, requires=requires)
    doc.update({"interaction": "mcq", "options": options, "correct_index": idx})
    if verify is not None:
        doc["verification"] = verify
    elif ref is not None:
        doc["verification"] = {"method": "reference", "kind": ref[0], "params": ref[1]}
    else:
        doc["verification"] = {"method": "manual_review", "note": note or MANUAL_NOTE, **(extra or {})}
    return doc


def short(topic: str, diff: str, stmt: str, kind: str, value: Any, help_text: str, expl: str, ref: tuple[str, dict], *, fmt: str = "design",
          hints: tuple[str, ...] = (), est: int = 90, tags: tuple[str, ...] = ()) -> dict[str, Any]:
    doc = _base(topic, diff, fmt, stmt, expl, hints=hints, est=est, tags=tags)
    doc.update({"interaction": "short", "short": {"kind": kind, "value": value, "help": help_text},
                "verification": {"method": "reference", "kind": ref[0], "params": ref[1]}})
    return doc


def outq(topic: str, diff: str, stmt: str, sql: str, render: str, oracle: Callable[[oracles.Tables], str], wrong: list[str], expl: str, *,
         hints: tuple[str, ...] = (), est: int = 60, tags: tuple[str, ...] = (), requires: tuple[str, ...] = ()) -> dict[str, Any]:
    """Predict-the-output MCQ. The correct option is derived by the Python oracle; validation checks the engine agrees."""
    qid = question_id_for(topic, stmt, sql)
    oracles.register(qid, oracle)
    correct = str(oracle(datasets.python_tables()))
    options, idx = _place(stmt, correct, wrong)
    doc = _base(topic, diff, "output", stmt, expl, code=sql, dialect="sqlite", hints=hints, est=est, tags=tags, requires=requires, dataset=datasets.DEFAULT_DATASET)
    doc.update({"interaction": "mcq", "options": options, "correct_index": idx, "verification": {"method": "sql_output", "render": render, "oracle": qid}})
    return doc


def planq(topic: str, diff: str, stmt: str, sql: str, expected: str, wrong: list[str], expl: str, *, hints: tuple[str, ...] = (), est: int = 60) -> dict[str, Any]:
    options, idx = _place(stmt, expected, wrong)
    doc = _base(topic, diff, "output", stmt, expl, code=sql, dialect="sqlite", hints=hints, est=est, dataset=datasets.DEFAULT_DATASET)
    doc.update({"interaction": "mcq", "options": options, "correct_index": idx, "verification": {"method": "sql_output", "render": "plan", "expected": expected}})
    return doc


def sqlq(topic: str, diff: str, fmt: str, stmt: str, ref_sql: str, oracle: Callable[[oracles.Tables], list], expl: str, *, hints: tuple[str, ...],
         starter: str | None = None, ordered: bool = False, names: bool = False, est: int = 150, tags: tuple[str, ...] = (), requires: tuple[str, ...] = ()) -> dict[str, Any]:
    """SQL exercise graded by result comparison. `expected` is computed once from the reference query; validation re-derives it
    with the engine and the independent Python oracle and rejects the question on any disagreement."""
    qid = question_id_for(topic, stmt, None)
    oracles.register(qid, oracle)
    res = sandbox.run_query(ref_sql, datasets.DEFAULT_DATASET)
    expected = {"columns": res.columns, "rows": res.rows} if res.ok else {"columns": ["error"], "rows": []}
    doc = _base(topic, diff, fmt, stmt, expl, dialect="sqlite", hints=hints, est=est, tags=tags, requires=requires, dataset=datasets.DEFAULT_DATASET)
    doc.update({"interaction": "sql", "sql": {"dataset_id": datasets.DEFAULT_DATASET, "starter": starter, "reference_sql": ref_sql, "expected": expected,
                                              "ordered": ordered, "check_column_names": names, "precision": 2},
                "verification": {"method": "sql", "oracle": qid}})
    return doc
