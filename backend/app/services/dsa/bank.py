"""
DSA question bank: indexes, validated seeding, public (answer-free) shapes, syllabus and coverage.

Seeding is idempotent and fail-closed, exactly like the Phase 23 bank:
  * every seed is validated (re-deriving reference answers) before it is stored; failures are logged and skipped;
  * duplicate ids / fingerprints are rejected;
  * seeds that disappear from the code become `inactive` (never deleted) so old results still resolve;
  * an edited seed gets its `version` bumped.
Questions that are `inactive` or `draft` are never served.
"""

from __future__ import annotations

import copy
import logging
import re
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from pymongo import ASCENDING, UpdateOne
from pymongo.database import Database

from app.db.collections import Collections
from app.services.dsa.content import all_seed_questions
from app.services.dsa.syllabus import MIN_QUESTIONS_PER_SUBTOPIC, SUBTOPIC_TO_TOPIC, TOPICS
from app.services.dsa.validation import content_hash, fingerprint, validate_question, verify_question

logger = logging.getLogger(__name__)

FORMATS = ("conceptual", "scenario", "output", "trace", "complexity", "coding")

# Fields a client may ever see before submission. `coding` is converted by `to_public` (hidden tests stripped).
LIST_PROJECTION = {
    "_id": 0, "question_id": 1, "topic_id": 1, "subtopic_id": 1, "format": 1, "interaction": 1, "coding_type": 1, "difficulty": 1,
    "statement": 1, "code": 1, "options": 1, "constraints": 1, "est_time_seconds": 1,
    "coding.function_name": 1, "coding.template": 1, "coding.sample_io": 1, "coding.test_cases": 1,
}


def to_public(doc: dict, *, options_order: list[int] | None = None) -> dict:
    """Whitelist conversion. Never copies correct_index, explanation, trace, complexity, hints or reference code."""
    options = doc.get("options") or []
    if options_order is not None:
        options = [options[i] for i in options_order]
    coding = None
    if doc.get("coding"):
        tests = doc["coding"]["test_cases"]
        coding = {
            "function_name": doc["coding"]["function_name"], "template": doc["coding"]["template"], "sample_io": doc["coding"].get("sample_io"),
            "visible_tests": [{"label": t["label"], "args": t["args"], "expected": t["expected"]} for t in tests if t["visible"]],
            "hidden_test_count": sum(1 for t in tests if not t["visible"]),
        }
    return {
        "question_id": doc["question_id"], "topic_id": doc["topic_id"], "subtopic_id": doc["subtopic_id"], "format": doc["format"],
        "interaction": doc["interaction"], "coding_type": doc.get("coding_type"), "difficulty": doc["difficulty"], "statement": doc["statement"],
        "code": doc.get("code"), "options": options, "constraints": doc.get("constraints"), "est_time_seconds": doc["est_time_seconds"], "coding": coding,
    }


def ensure_indexes(db: Database) -> None:
    q = db[Collections.DSA_QUESTIONS]
    q.create_index("question_id", unique=True)
    q.create_index("fingerprint", unique=True)
    q.create_index([("status", ASCENDING), ("topic_id", ASCENDING), ("subtopic_id", ASCENDING), ("difficulty", ASCENDING)])
    q.create_index([("status", ASCENDING), ("format", ASCENDING), ("interaction", ASCENDING)])
    s = db[Collections.DSA_SESSIONS]
    s.create_index([("user_id", ASCENDING), ("started_at", -1)])
    s.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
    a = db[Collections.DSA_ATTEMPTS]
    a.create_index([("session_id", ASCENDING), ("question_id", ASCENDING)], unique=True)
    a.create_index([("user_id", ASCENDING), ("topic_id", ASCENDING)])
    a.create_index([("user_id", ASCENDING), ("created_at", -1)])


@lru_cache(maxsize=1)
def _validated_seed_bank() -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    return _build_valid_seed_bank()


def build_valid_seed_bank() -> tuple[list[dict], list[dict]]:
    """Cached per process (validation re-derives every reference answer). Returns deep copies."""
    valid, rejected = _validated_seed_bank()
    return copy.deepcopy(list(valid)), copy.deepcopy(list(rejected))


def _build_valid_seed_bank() -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    valid, rejected = [], []
    seen_ids: set[str] = set()
    seen_fps: set[str] = set()
    for doc in all_seed_questions():
        doc["review_status"], _ = verify_question(doc)
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
        logger.error("Rejected DSA seed %s (%s): %s", r["question_id"], r["statement"], r["problems"])
    coll = db[Collections.DSA_QUESTIONS]
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


def active_counts(db: Database) -> dict[str, dict[str, Any]]:
    """{subtopic_id: {total, easy, medium, hard, formats:{...}, gradable, code}} over active questions."""
    counts: dict[str, dict[str, Any]] = {}
    for row in db[Collections.DSA_QUESTIONS].aggregate([
        {"$match": {"status": "active"}},
        {"$group": {"_id": {"s": "$subtopic_id", "d": "$difficulty", "f": "$format", "i": "$interaction"}, "n": {"$sum": 1}}},
    ]):
        k = row["_id"]
        e = counts.setdefault(k["s"], {"total": 0, "easy": 0, "medium": 0, "hard": 0, "formats": {}, "gradable": 0, "code": 0})
        e[k["d"]] += row["n"]
        e["total"] += row["n"]
        e["formats"][k["f"]] = e["formats"].get(k["f"], 0) + row["n"]
        e["code" if k["i"] == "code" else "gradable"] += row["n"]
    return counts


def status_for(count: int) -> str:
    if count >= MIN_QUESTIONS_PER_SUBTOPIC:
        return "implemented"
    return "partial" if count > 0 else "missing"


def syllabus_payload(db: Database) -> dict[str, Any]:
    """Topic hierarchy with completion computed from the questions that actually exist."""
    counts = active_counts(db)
    topics = []
    for t in TOPICS:
        subs = []
        for s in t.subtopics:
            c = counts.get(s.id, {"total": 0, "easy": 0, "medium": 0, "hard": 0, "formats": {}, "gradable": 0, "code": 0})
            subs.append({"id": s.id, "title": s.title, "question_count": c["total"], "by_difficulty": {k: c[k] for k in ("easy", "medium", "hard")},
                         "by_format": c["formats"], "auto_graded": c["gradable"], "self_assessed_code": c["code"], "status": status_for(c["total"])})
        implemented = sum(1 for s in subs if s["status"] == "implemented")
        topics.append({
            "id": t.id, "code": t.code, "title": t.title, "summary": t.summary, "question_count": sum(s["question_count"] for s in subs), "subtopics": subs,
            "items": [{"text": i.text, "subtopic_ids": list(i.subtopic_ids), "question_count": sum(counts.get(x, {}).get("total", 0) for x in i.subtopic_ids)} for i in t.items],
            "subtopics_implemented": implemented, "subtopics_total": len(subs),
            "status": "implemented" if implemented == len(subs) else ("partial" if any(s["question_count"] for s in subs) else "missing"),
        })
    total_subs = sum(t["subtopics_total"] for t in topics)
    done = sum(t["subtopics_implemented"] for t in topics)
    fmt_totals = {f: sum(c["formats"].get(f, 0) for c in counts.values()) for f in FORMATS}
    return {
        "topics": topics,
        "totals": {"topics": len(topics), "subtopics": total_subs, "subtopics_implemented": done, "questions": sum(t["question_count"] for t in topics),
                   "by_format": fmt_totals, "min_questions_per_subtopic": MIN_QUESTIONS_PER_SUBTOPIC},
        "execution": execution_status(),
    }


def execution_status() -> dict[str, Any]:
    """Honest capability statement surfaced to the UI: no automated execution of submitted code exists."""
    return {"automated_code_execution": False, "mode": "self_assessed",
            "message": "Code answers are saved but not run automatically. After submitting you see the reference solution and the test cases, and you can mark your own result."}


_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,59}$")


def list_public_questions(db: Database, *, topic_id=None, subtopic_id=None, difficulty=None, fmt=None, page=1, limit=20) -> dict[str, Any]:
    """Answer-free listing. Only whitelisted filter fields reach the query; documents go through `to_public`."""
    query: dict[str, Any] = {"status": "active"}
    if topic_id:
        query["topic_id"] = topic_id
    if subtopic_id:
        query["subtopic_id"] = subtopic_id
    if difficulty:
        query["difficulty"] = difficulty
    if fmt:
        query["format"] = fmt
    coll = db[Collections.DSA_QUESTIONS]
    total = coll.count_documents(query)
    rows = list(coll.find(query, LIST_PROJECTION).sort([("topic_id", 1), ("subtopic_id", 1), ("question_id", 1)]).skip((page - 1) * limit).limit(limit))
    return {"items": [to_public(r) for r in rows], "page": page, "limit": limit, "total": total, "has_next": page * limit < total}


def is_valid_subtopic(subtopic_id: str) -> bool:
    return subtopic_id in SUBTOPIC_TO_TOPIC
