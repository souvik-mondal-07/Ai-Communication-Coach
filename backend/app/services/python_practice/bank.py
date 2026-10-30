"""
Python practice question bank: indexes, validated idempotent seeding, public (answer-free) shapes, syllabus and coverage (Phase 26).

Seeding follows the DSA / DBMS convention and is fail-closed: every seed is validated before it is stored (execution-checked outputs
must match `content/verified.json`, coding problems must have had a reference solution and an independent solution agree on every
test); failures are logged and skipped; duplicates are rejected; seeds that vanish from the code become `inactive` (never deleted, so old
results still resolve); an edited seed gets its `version` bumped. Re-running the seed never creates duplicates.
"""

from __future__ import annotations

import copy
import logging
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from pymongo import ASCENDING, UpdateOne
from pymongo.database import Database

from app.db.collections import Collections
from app.services.python_practice import compare
from app.services.python_practice.content import all_seed_questions
from app.services.python_practice.sandbox import runner
from app.services.python_practice.syllabus import MIN_QUESTIONS_PER_TOPIC, UNITS
from app.services.python_practice.validation import content_hash, fingerprint, validate_question, verify_question

logger = logging.getLogger(__name__)

FORMATS = ("concept", "output", "trace", "debug", "complete", "coding", "complexity", "scenario")
HANDS_ON = ("code",)
MODE_FILTERS: dict[str, dict[str, Any]] = {
    "interview": {"format": {"$in": ["concept", "scenario"]}},
    "predict_output": {"format": "output"},
    "trace": {"format": "trace"},
    "debug": {"format": "debug"},
    "complete": {"format": "complete"},
    "coding": {"interaction": "code"},
    "complexity": {"format": "complexity"},
    "oop": {"unit_id": "unit-d"},
    "advanced": {"unit_id": "unit-f"},
    "security": {"unit_id": "unit-h"},
}

LIST_PROJECTION = {
    "_id": 0, "question_id": 1, "unit_id": 1, "topic_id": 1, "format": 1, "interaction": 1, "difficulty": 1, "title": 1, "statement": 1, "code": 1, "options": 1,
    "est_time_seconds": 1, "tags": 1, "python_version": 1, "short.kind": 1, "short.help": 1,
    "spec.mode": 1, "spec.entry": 1, "spec.signature": 1, "spec.starter": 1, "spec.constraints": 1,
    "spec.tests.id": 1, "spec.tests.label": 1, "spec.tests.visible": 1, "spec.tests.input_repr": 1, "spec.tests.expected": 1,
}


def to_public(doc: dict, *, options_order: list[int] | None = None) -> dict:
    """Whitelist conversion. Never copies correct_index, explanation, hints, reference source, hidden tests or short answers."""
    options = doc.get("options") or []
    if options_order is not None:
        options = [options[i] for i in options_order]
    short, spec = doc.get("short"), doc.get("spec")
    code_spec = None
    if spec:
        tests = spec.get("tests", [])
        examples = [{"id": t["id"], "label": t["label"], "input": t.get("input_repr", ""), "expected": compare.describe(t.get("expected"))} for t in tests if t.get("visible")]
        code_spec = {"mode": spec["mode"], "entry": spec["entry"], "signature": spec["signature"], "starter": spec["starter"], "constraints": list(spec.get("constraints") or []),
                     "examples": examples, "visible_count": len(examples), "hidden_count": len(tests) - len(examples)}
    return {
        "question_id": doc["question_id"], "unit_id": doc["unit_id"], "topic_id": doc["topic_id"], "format": doc["format"], "interaction": doc["interaction"],
        "difficulty": doc["difficulty"], "title": doc.get("title"), "statement": doc["statement"], "code": doc.get("code"), "options": options,
        "est_time_seconds": doc["est_time_seconds"], "tags": list(doc.get("tags") or []), "python_version": doc.get("python_version"),
        "short": None if not short else {"kind": short["kind"], "help": short["help"]}, "code_spec": code_spec,
    }


def ensure_indexes(db: Database) -> None:
    q = db[Collections.PYTHON_QUESTIONS]
    q.create_index("question_id", unique=True)
    q.create_index("fingerprint", unique=True)
    q.create_index([("status", ASCENDING), ("unit_id", ASCENDING), ("topic_id", ASCENDING), ("difficulty", ASCENDING)])
    q.create_index([("status", ASCENDING), ("format", ASCENDING), ("interaction", ASCENDING)])
    s = db[Collections.PYTHON_SESSIONS]
    s.create_index([("user_id", ASCENDING), ("started_at", -1)])
    s.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
    a = db[Collections.PYTHON_ATTEMPTS]
    a.create_index([("session_id", ASCENDING), ("question_id", ASCENDING)], unique=True)
    a.create_index([("user_id", ASCENDING), ("topic_id", ASCENDING)])
    a.create_index([("user_id", ASCENDING), ("created_at", -1)])


@lru_cache(maxsize=1)
def _validated_seed_bank() -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    return _build_valid_seed_bank()


def build_valid_seed_bank() -> tuple[list[dict], list[dict]]:
    """Cached per process. Returns deep copies."""
    valid, rejected = _validated_seed_bank()
    return copy.deepcopy(list(valid)), copy.deepcopy(list(rejected))


def _build_valid_seed_bank() -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    valid: list[dict] = []
    rejected: list[dict] = []
    seen_ids: set[str] = set()
    seen_fps: set[str] = set()
    for doc in all_seed_questions():
        doc["review_status"] = verify_question(doc)
        problems = validate_question(doc)
        fp = fingerprint(doc)
        if doc["question_id"] in seen_ids or fp in seen_fps:
            problems.append("duplicate question")
        if problems:
            rejected.append({"question_id": doc["question_id"], "statement": doc["statement"][:90], "problems": problems})
            continue
        seen_ids.add(doc["question_id"])
        seen_fps.add(fp)
        doc["fingerprint"] = fp
        doc["content_hash"] = content_hash(doc)
        valid.append(doc)
    return tuple(valid), tuple(rejected)


def ensure_seeded(db: Database) -> dict[str, int]:
    valid, rejected = build_valid_seed_bank()
    for r in rejected:
        logger.error("Rejected Python practice seed %s (%s): %s", r["question_id"], r["statement"], r["problems"])
    coll = db[Collections.PYTHON_QUESTIONS]
    now = datetime.now(UTC)
    existing = {d["question_id"]: d for d in coll.find({"source": "seed"}, {"question_id": 1, "content_hash": 1, "version": 1, "status": 1})}
    ops: list[UpdateOne] = []
    added = updated = 0
    for doc in valid:
        prev = existing.get(doc["question_id"])
        if prev is None:
            added += 1
            ops.append(UpdateOne({"question_id": doc["question_id"]}, {"$set": {**doc, "created_at": now, "updated_at": now}}, upsert=True))
        elif prev.get("content_hash") != doc["content_hash"] or prev.get("status") != "active":
            updated += 1
            ops.append(UpdateOne({"question_id": doc["question_id"]}, {"$set": {**doc, "version": int(prev.get("version", 1)) + 1, "updated_at": now}}))
    current_ids = {d["question_id"] for d in valid}
    retired = [qid for qid in existing if qid not in current_ids]
    if retired:
        coll.update_many({"question_id": {"$in": retired}, "source": "seed"}, {"$set": {"status": "inactive", "updated_at": now}})
    if ops:
        coll.bulk_write(ops, ordered=False)
    return {"added": added, "updated": updated, "retired": len(retired), "rejected": len(rejected), "active_seed_total": len(valid)}


def _empty_counts() -> dict[str, Any]:
    return {"total": 0, "easy": 0, "medium": 0, "hard": 0, "formats": {}, "interactions": {}, "verification": {}}


def active_counts(db: Database) -> dict[str, dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = {}
    for row in db[Collections.PYTHON_QUESTIONS].aggregate([
        {"$match": {"status": "active"}},
        {"$group": {"_id": {"t": "$topic_id", "d": "$difficulty", "f": "$format", "i": "$interaction", "v": "$review_status"}, "n": {"$sum": 1}}},
    ]):
        k = row["_id"]
        e = counts.setdefault(k["t"], _empty_counts())
        e[k["d"]] += row["n"]
        e["total"] += row["n"]
        e["formats"][k["f"]] = e["formats"].get(k["f"], 0) + row["n"]
        e["interactions"][k["i"]] = e["interactions"].get(k["i"], 0) + row["n"]
        e["verification"][k["v"]] = e["verification"].get(k["v"], 0) + row["n"]
    return counts


def status_for(count: int) -> str:
    if count >= MIN_QUESTIONS_PER_TOPIC:
        return "implemented"
    return "partial" if count > 0 else "missing"


def syllabus_payload(db: Database) -> dict[str, Any]:
    """Units and topics with completion computed from the questions that actually exist. Nothing is hardcoded as 'done'."""
    counts = active_counts(db)
    units = []
    for u in UNITS:
        topics = []
        for t in u.topics:
            c = counts.get(t.id, _empty_counts())
            topics.append({"id": t.id, "title": t.title, "question_count": c["total"], "by_difficulty": {k: c[k] for k in ("easy", "medium", "hard")},
                           "by_format": c["formats"], "by_interaction": c["interactions"], "status": status_for(c["total"])})
        units.append({"id": u.id, "code": u.code, "title": u.title, "summary": u.summary, "question_count": sum(x["question_count"] for x in topics), "topics": topics,
                      "topics_implemented": sum(1 for x in topics if x["status"] == "implemented"), "topics_total": len(topics)})
    return {"units": units, "question_total": sum(u["question_count"] for u in units), "min_questions_per_topic": MIN_QUESTIONS_PER_TOPIC,
            "topics_implemented": sum(u["topics_implemented"] for u in units), "topics_total": sum(u["topics_total"] for u in units), "runner": runner.capabilities()}


def coverage_report(db: Database) -> dict[str, Any]:
    """Per-topic coverage plus honest gaps and a verification breakdown (manual review is never counted as machine-verified)."""
    counts = active_counts(db)
    rows, gaps = [], []
    totals: dict[str, int] = {}
    verified_kinds = ("execution_verified", "reference_verified")
    for u in UNITS:
        unit_levels = {"easy": 0, "medium": 0, "hard": 0}
        for t in u.topics:
            c = counts.get(t.id, _empty_counts())
            for k, n in c["verification"].items():
                totals[k] = totals.get(k, 0) + n
            for d in unit_levels:
                unit_levels[d] += c[d]
            rows.append({"unit": u.code, "topic_id": t.id, "topic": t.title, "covers": t.covers or t.title, "count": c["total"], "easy": c["easy"], "medium": c["medium"], "hard": c["hard"],
                         "formats": dict(sorted(c["formats"].items())), "interactions": dict(sorted(c["interactions"].items())), "status": status_for(c["total"]),
                         "machine_verified": sum(c["verification"].get(k, 0) for k in verified_kinds), "manual_review": c["verification"].get("manual_review", 0)})
            if c["total"] < MIN_QUESTIONS_PER_TOPIC:
                gaps.append(f"{t.title}: only {c['total']} question(s); at least {MIN_QUESTIONS_PER_TOPIC} are required.")
        for d, n in unit_levels.items():
            if n == 0:
                gaps.append(f"Unit {u.code}: no {d} questions at all.")
    machine = sum(totals.get(k, 0) for k in verified_kinds)
    return {"rows": rows, "gaps": gaps, "total_questions": sum(r["count"] for r in rows), "machine_verified": machine, "manual_review": totals.get("manual_review", 0),
            "topics_implemented": sum(1 for r in rows if r["status"] == "implemented"), "topics_total": len(rows), "runner": runner.capabilities()}


def list_public_questions(db: Database, *, unit_id=None, topic_id=None, difficulty=None, fmt=None, interaction=None, page=1, limit=20) -> dict[str, Any]:
    query: dict[str, Any] = {"status": "active"}
    for key, value in (("unit_id", unit_id), ("topic_id", topic_id), ("difficulty", difficulty), ("format", fmt), ("interaction", interaction)):
        if value:
            query[key] = value
    coll = db[Collections.PYTHON_QUESTIONS]
    total = coll.count_documents(query)
    rows = list(coll.find(query, LIST_PROJECTION).sort([("unit_id", 1), ("topic_id", 1), ("question_id", 1)]).skip((page - 1) * limit).limit(limit))
    return {"items": [to_public(r) for r in rows], "page": page, "limit": limit, "total": total, "has_next": page * limit < total}
