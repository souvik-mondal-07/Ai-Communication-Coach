"""
DBMS & SQL question bank: indexes, validated idempotent seeding, public (answer-free) shapes, syllabus and coverage (Phase 25).

Seeding follows the DSA/aptitude convention and is fail-closed:
  * every seed is validated (re-running SQL in the sandbox and re-deriving reference answers) before it is stored;
  * failures are logged and skipped; duplicate ids/fingerprints are rejected;
  * seeds that vanish from the code become `inactive` (never deleted) so old results still resolve;
  * an edited seed gets its `version` bumped. Re-running the seed never creates duplicates.
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
from app.services.dbms_sql import sandbox
from app.services.dbms_sql.content import all_seed_questions
from app.services.dbms_sql.syllabus import MIN_QUESTIONS_PER_TOPIC, UNITS
from app.services.dbms_sql.validation import content_hash, fingerprint, validate_question, verify_question

logger = logging.getLogger(__name__)

FORMATS = ("concept", "scenario", "output", "debug", "complete", "query", "design", "transaction")

# Practice mode -> extra question filter. Modes absent here (topic, mixed, timed_mock, weak) select by topic/unit instead.
MODE_FILTERS: dict[str, dict[str, Any]] = {
    "interview": {"format": {"$in": ["concept", "scenario"]}},
    "sql_lab": {"format": "query"},
    "predict_output": {"format": "output"},
    "debug": {"format": "debug"},
    "complete": {"format": "complete"},
    "design_lab": {"$or": [{"unit_id": "unit-d"}, {"format": "design"}]},
    "transaction_lab": {"$or": [{"unit_id": "unit-f"}, {"format": "transaction"}]},
    "nosql_lab": {"unit_id": "unit-g"},
}

# Nothing outside this whitelist ever reaches a client before submission.
LIST_PROJECTION = {
    "_id": 0, "question_id": 1, "unit_id": 1, "topic_id": 1, "format": 1, "interaction": 1, "dialect": 1, "difficulty": 1, "statement": 1,
    "code": 1, "options": 1, "dataset_id": 1, "est_time_seconds": 1, "tags": 1,
    "short.kind": 1, "short.help": 1,
    "sql.dataset_id": 1, "sql.starter": 1, "sql.ordered": 1, "sql.check_column_names": 1, "sql.expected.columns": 1,
}


def to_public(doc: dict, *, options_order: list[int] | None = None) -> dict:
    """Whitelist conversion. Never copies correct_index, explanation, hints, reference SQL, expected rows or short answers."""
    options = doc.get("options") or []
    if options_order is not None:
        options = [options[i] for i in options_order]
    short = doc.get("short")
    sql = doc.get("sql")
    return {
        "question_id": doc["question_id"], "unit_id": doc["unit_id"], "topic_id": doc["topic_id"], "format": doc["format"], "interaction": doc["interaction"],
        "dialect": doc.get("dialect", "standard"), "difficulty": doc["difficulty"], "statement": doc["statement"], "code": doc.get("code"), "options": options,
        "dataset_id": doc.get("dataset_id"), "est_time_seconds": doc["est_time_seconds"], "tags": list(doc.get("tags") or []),
        "short": None if not short else {"kind": short["kind"], "help": short["help"]},
        "sql": None if not sql else {
            "dataset_id": sql["dataset_id"], "starter": sql.get("starter"), "ordered": sql["ordered"], "check_column_names": sql["check_column_names"],
            "expected_columns": list(sql["expected"]["columns"]),
        },
    }


def ensure_indexes(db: Database) -> None:
    q = db[Collections.DBMS_SQL_QUESTIONS]
    q.create_index("question_id", unique=True)
    q.create_index("fingerprint", unique=True)
    q.create_index([("status", ASCENDING), ("unit_id", ASCENDING), ("topic_id", ASCENDING), ("difficulty", ASCENDING)])
    q.create_index([("status", ASCENDING), ("format", ASCENDING), ("interaction", ASCENDING)])
    s = db[Collections.DBMS_SQL_SESSIONS]
    s.create_index([("user_id", ASCENDING), ("started_at", -1)])
    s.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
    a = db[Collections.DBMS_SQL_ATTEMPTS]
    a.create_index([("session_id", ASCENDING), ("question_id", ASCENDING)], unique=True)
    a.create_index([("user_id", ASCENDING), ("topic_id", ASCENDING)])
    a.create_index([("user_id", ASCENDING), ("created_at", -1)])


@lru_cache(maxsize=1)
def _validated_seed_bank() -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    return _build_valid_seed_bank()


def build_valid_seed_bank() -> tuple[list[dict], list[dict]]:
    """Cached per process (validation re-runs every SQL reference). Returns deep copies."""
    valid, rejected = _validated_seed_bank()
    return copy.deepcopy(list(valid)), copy.deepcopy(list(rejected))


def _build_valid_seed_bank() -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    valid: list[dict] = []
    rejected: list[dict] = []
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
        logger.error("Rejected DBMS/SQL seed %s (%s): %s", r["question_id"], r["statement"], r["problems"])
    coll = db[Collections.DBMS_SQL_QUESTIONS]
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
    """{topic_id: {total, easy/medium/hard, formats, interactions, verification}} over active questions."""
    counts: dict[str, dict[str, Any]] = {}
    for row in db[Collections.DBMS_SQL_QUESTIONS].aggregate([
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
        units.append({
            "id": u.id, "code": u.code, "title": u.title, "summary": u.summary, "question_count": sum(x["question_count"] for x in topics), "topics": topics,
            "topics_implemented": sum(1 for x in topics if x["status"] == "implemented"), "topics_total": len(topics),
        })
    total = sum(u["question_count"] for u in units)
    return {
        "units": units, "question_total": total, "min_questions_per_topic": MIN_QUESTIONS_PER_TOPIC,
        "topics_implemented": sum(u["topics_implemented"] for u in units), "topics_total": sum(u["topics_total"] for u in units),
        "sql_engine": sandbox.capabilities(),
    }


def coverage_report(db: Database) -> dict[str, Any]:
    """Per-topic coverage plus honest gaps and a verification breakdown (manual review is never counted as machine-verified)."""
    counts = active_counts(db)
    rows, gaps = [], []
    totals: dict[str, int] = {}
    for u in UNITS:
        for t in u.topics:
            c = counts.get(t.id, _empty_counts())
            for k, n in c["verification"].items():
                totals[k] = totals.get(k, 0) + n
            missing_levels = [d for d in ("easy", "medium", "hard") if c[d] == 0]
            rows.append({"unit": u.code, "topic_id": t.id, "topic": t.title, "count": c["total"], "easy": c["easy"], "medium": c["medium"], "hard": c["hard"],
                         "formats": dict(sorted(c["formats"].items())), "interactions": dict(sorted(c["interactions"].items())), "status": status_for(c["total"]),
                         "machine_verified": sum(c["verification"].get(k, 0) for k in ("reference_checked", "sql_checked", "sql_output_checked")),
                         "manual_review": c["verification"].get("manual_review", 0)})
            if c["total"] < MIN_QUESTIONS_PER_TOPIC:
                gaps.append(f"{t.title}: only {c['total']} question(s); at least {MIN_QUESTIONS_PER_TOPIC} are required.")
            elif missing_levels:
                gaps.append(f"{t.title}: no {'/'.join(missing_levels)} question yet.")
            if "sql" not in c["interactions"] and c["total"] and u.code in ("B", "C"):
                gaps.append(f"{t.title}: no hands-on SQL exercise (theory/prediction only).")
    machine = sum(totals.get(k, 0) for k in ("reference_checked", "sql_checked", "sql_output_checked"))
    return {
        "rows": rows, "gaps": gaps, "total_questions": sum(r["count"] for r in rows), "machine_verified": machine, "manual_review": totals.get("manual_review", 0),
        "topics_implemented": sum(1 for r in rows if r["status"] == "implemented"), "topics_total": len(rows),
    }


def list_public_questions(db: Database, *, unit_id=None, topic_id=None, difficulty=None, fmt=None, interaction=None, page=1, limit=20) -> dict[str, Any]:
    """Answer-free listing. Only whitelisted filter fields reach the query; documents go through `to_public`."""
    query: dict[str, Any] = {"status": "active"}
    for key, value in (("unit_id", unit_id), ("topic_id", topic_id), ("difficulty", difficulty), ("format", fmt), ("interaction", interaction)):
        if value:
            query[key] = value
    coll = db[Collections.DBMS_SQL_QUESTIONS]
    total = coll.count_documents(query)
    rows = list(coll.find(query, LIST_PROJECTION).sort([("unit_id", 1), ("topic_id", 1), ("question_id", 1)]).skip((page - 1) * limit).limit(limit))
    return {"items": [to_public(r) for r in rows], "page": page, "limit": limit, "total": total, "has_next": page * limit < total}
