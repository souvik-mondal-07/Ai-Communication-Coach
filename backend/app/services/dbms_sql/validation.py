"""
Question validation: the gate every question must pass before it can be served (Phase 25).

`validate_question` returns a list of problems (empty = valid). Beyond structure it enforces:
  * four distinct options and exactly one correct option (a verification must reproduce the key and match no distractor);
  * every active question carries a verification block;
  * SQL questions: the reference query runs in the sandbox, its result equals the stored expected result AND an independent
    pure-Python oracle; debug starters are really broken and completion starters are really incomplete;
  * vendor-specific syntax is never presented as standard SQL (it must declare a dialect);
  * nothing claims to come from a real company exam.

Verification methods and what they prove:
  reference         a deterministic computation (design / transaction algorithms) reproduces the key         [machine-checked]
  sql / sql_output  the SQL engine AND an independent Python oracle agree with the key or expected result   [machine-checked]
  manual_review     a human-written justification; NO machine check. Reported separately, never counted as verified.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import ValidationError

from app.schemas.dbms_sql import QuestionContent
from app.services.dbms_sql import datasets, oracles, sandbox, sql_compare
from app.services.dbms_sql.references import UnknownReference, run_reference
from app.services.dbms_sql.syllabus import TOPIC_TO_UNIT

_AMBIGUOUS = re.compile(r"\b(all|none|both)\s+of\s+the\s+above\b|\bany\s+of\s+the\s+above\b", re.I)
_REAL_EXAM_CLAIM = re.compile(r"\b(asked in|appeared in|previous year|actual exam|from (tcs|infosys|wipro|accenture|cognizant|google|amazon|microsoft|meta))\b", re.I)
_VENDOR_SQL = re.compile(
    r"\b(DELIMITER|PL/SQL|PL/pgSQL|T-SQL|AUTO_INCREMENT|(?-i:\bSERIAL\b)|NVL\(|ROWNUM|SELECT\s+TOP|DECLARE\s+@|DBMS_OUTPUT|RAISE\s+EXCEPTION|EXCEPTION\s+WHEN|"
    r"CREATE\s+(OR\s+REPLACE\s+)?(PROCEDURE|FUNCTION|TRIGGER)|ON\s+DUPLICATE\s+KEY|RETURNING|ILIKE|LIMIT\s+\d)", re.I)
_VENDOR_MONGO = re.compile(r"\bdb\.\w+\.(find|insert\w*|update\w*|delete\w*|aggregate|create\w*|explain|count\w*)\b|\$(gt|gte|lt|lte|set|match|group|in|inc|push|eq|ne|and|or)\b")
_NON_STANDARD_DIALECTS = {"sqlite", "mysql", "postgresql", "oracle", "sqlserver", "mongodb", "dynamodb"}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().casefold())


def question_id_for(topic_id: str, statement: str, code: str | None = None) -> str:
    """Stable identifier: the same question always gets the same id across seeds and restarts."""
    basis = f"{topic_id}|{normalize(statement)}|{normalize(code) if code else ''}"
    return "dbq-" + hashlib.sha1(basis.encode()).hexdigest()[:10]


def fingerprint(doc: dict) -> str:
    basis = "|".join([normalize(doc["statement"]), normalize(doc.get("code") or ""), ",".join(sorted(normalize(o) for o in doc.get("options", [])))])
    return hashlib.sha1(basis.encode()).hexdigest()


def content_hash(doc: dict) -> str:
    keys = ("statement", "code", "options", "correct_index", "short", "sql", "explanation", "difficulty", "hints", "est_time_seconds", "dialect", "dataset_id", "format")
    return hashlib.sha1(json.dumps({k: doc.get(k) for k in keys}, sort_keys=True, default=str).encode()).hexdigest()


def _tables() -> oracles.Tables:
    return datasets.python_tables()


def _marked_text(doc: dict) -> str:
    if doc["interaction"] == "mcq":
        return doc["options"][doc["correct_index"]]
    return sql_compare.canonical_short(doc["short"]["kind"], doc["short"]["value"])


def _verify_reference(doc: dict, ver: dict) -> tuple[str, list[str]]:
    try:
        computed = run_reference(str(ver.get("kind", "")), ver.get("params") or {})
    except UnknownReference as exc:
        return "unverified", [str(exc)]
    problems: list[str] = []
    if doc["interaction"] == "short":
        spec = doc["short"]
        want = sql_compare.canonical_short(spec["kind"], spec["value"])
        if spec["kind"] == "number":
            if sql_compare.parse_number(computed) is None or abs(sql_compare.parse_number(computed) - float(spec["value"])) > 1e-9:
                problems.append(f"reference result '{computed}' does not equal the short answer '{want}'")
        elif spec["kind"] == "attrs":
            if sql_compare.parse_attrs(computed) != frozenset(str(x).upper() for x in spec["value"]):
                problems.append(f"reference result '{computed}' does not equal the short answer '{want}'")
        elif frozenset(frozenset(ch for ch in grp.upper() if ch.isalpha()) for grp in re.findall(r"\{([^}]*)\}", computed)) != frozenset(frozenset(str(k).upper()) for k in spec["value"]):
            problems.append(f"reference result '{computed}' does not equal the short answer '{want}'")
    elif doc["interaction"] == "mcq":
        idx, options = doc["correct_index"], doc["options"]
        if normalize(computed) != normalize(options[idx]):
            problems.append(f"reference result '{computed}' does not equal the marked option '{options[idx]}'")
        problems += [f"ambiguous: option {i} also equals the reference result" for i, o in enumerate(options) if i != idx and normalize(o) == normalize(computed)]
    else:
        problems.append("'reference' verification does not apply to SQL questions")
    return ("reference_checked" if not problems else "unverified"), problems


def _engine(sql: str, dataset_id: str) -> tuple[list[str], list[list[Any]]] | str:
    res = sandbox.run_query(sql, dataset_id, max_rows=sandbox.MAX_ROWS)
    if not res.ok:
        return f"engine error: {res.error.message if res.error else 'unknown'}"
    return res.columns, res.rows


def _verify_sql_output(doc: dict, ver: dict) -> tuple[str, list[str]]:
    if doc["interaction"] != "mcq" or not doc.get("code"):
        return "unverified", ["sql_output verification needs an MCQ with a SQL snippet in `code`"]
    ds = doc.get("dataset_id") or datasets.DEFAULT_DATASET
    mode = str(ver.get("render", "rows"))
    sql = doc["code"]
    if mode == "plan":
        res = _engine("EXPLAIN QUERY PLAN " + sql, ds)
        if isinstance(res, str):
            return "unverified", [res]
        computed = oracles.plan_kind([str(r[3]) for r in res[1]])
    else:
        res = _engine(sql, ds)
        if isinstance(res, str):
            return "unverified", [res]
        try:
            computed = oracles.render(res[0], res[1], mode)
        except ValueError as exc:
            return "unverified", [str(exc)]
    problems: list[str] = []
    idx, options = doc["correct_index"], doc["options"]
    if normalize(computed) != normalize(options[idx]):
        problems.append(f"engine result '{computed}' does not equal the marked option '{options[idx]}'")
    problems += [f"ambiguous: option {i} also equals the engine result" for i, o in enumerate(options) if i != idx and normalize(o) == normalize(computed)]
    independent = ver.get("expected")
    if "oracle" in ver:
        fn = oracles.ORACLES.get(str(ver["oracle"]))
        independent = None if fn is None else str(fn(_tables()))
        if fn is None:
            problems.append("declared oracle is not registered")
    if independent is None:
        problems.append("sql_output needs an independent oracle or declared `expected` value")
    elif normalize(str(independent)) != normalize(computed):
        problems.append(f"independent value '{independent}' differs from the engine result '{computed}'")
    return ("sql_output_checked" if not problems else "unverified"), problems


def _verify_json(doc: dict, ver: dict) -> tuple[str, list[str]]:
    """Exactly one option parses as JSON and it is the marked one."""
    if doc["interaction"] != "mcq":
        return "unverified", ["json verification is for MCQs"]
    valid = []
    for i, option in enumerate(doc["options"]):
        try:
            json.loads(option)
            valid.append(i)
        except ValueError:
            pass
    if valid != [doc["correct_index"]]:
        return "unverified", [f"expected exactly the marked option to be valid JSON, found valid options {valid}"]
    return "reference_checked", []


def _verify_sql(doc: dict, ver: dict) -> tuple[str, list[str]]:
    spec = doc.get("sql")
    if doc["interaction"] != "sql" or not spec:
        return "unverified", ["'sql' verification is for SQL questions only"]
    problems: list[str] = []
    ds = spec["dataset_id"]
    res = _engine(spec["reference_sql"], ds)
    if isinstance(res, str):
        return "unverified", ["reference query failed: " + res]
    cols, rows = res
    exp = spec["expected"]
    if not exp["rows"]:
        problems.append("expected result must have at least one row")
    if len({c.lower() for c in cols}) != len(cols):
        problems.append("reference query returns duplicate column names")
    v = sql_compare.compare(cols, rows, exp["columns"], exp["rows"], ordered=spec["ordered"], check_column_names=True, precision=spec["precision"], sql=spec["reference_sql"])
    if not v.correct:
        problems.append("reference query result differs from the stored expected result: " + " ".join(v.messages[:2]))
    fn = oracles.ORACLES.get(str(ver.get("oracle", "")))
    if fn is None:
        problems.append("an independent oracle is required and is not registered")
    else:
        try:
            ov = sql_compare.compare(cols, rows, cols, [list(r) for r in fn(_tables())], ordered=spec["ordered"], precision=spec["precision"])
        except Exception as exc:  # noqa: BLE001
            ov = None
            problems.append(f"oracle failed: {type(exc).__name__}")
        if ov is not None and not ov.correct:
            problems.append("independent Python oracle disagrees with the engine: " + " ".join(ov.messages[:2]))
    starter = spec.get("starter")

    def starter_solves() -> bool:
        r = sandbox.run_query(starter, ds)
        return r.ok and sql_compare.compare(r.columns, r.rows, exp["columns"], exp["rows"], ordered=spec["ordered"],
                                            check_column_names=spec["check_column_names"], precision=spec["precision"], sql=starter).correct

    if doc["format"] in ("debug", "complete") and not starter:
        problems.append(f"a {doc['format']} question needs a starter query")
    if starter and doc["format"] == "debug" and starter_solves():
        problems.append("the broken starter query already produces the expected result")
    if starter and doc["format"] == "complete":
        if "___" not in starter:
            problems.append("a completion starter must contain a ___ blank")
        elif sandbox.run_query(starter, ds).ok:
            problems.append("a completion starter with blanks must not run as-is")
    if starter and doc["format"] in ("query", "output") and starter_solves():
        problems.append("the starter query already solves the task")
    return ("sql_checked" if not problems else "unverified"), problems


def verify_question(doc: dict) -> tuple[str, list[str]]:
    """(review_status, problems). Machine checks run in-process against repository-owned content only."""
    ver = doc.get("verification")
    if not isinstance(ver, dict) or "method" not in ver:
        return "unverified", ["missing verification block"]
    method = ver["method"]
    if method == "manual_review":
        if len(str(ver.get("note", "")).strip()) < 15:
            return "unverified", ["manual review needs a note explaining the reasoning"]
        return "manual_review", []
    if method == "reference":
        return _verify_reference(doc, ver)
    if method == "json_valid":
        return _verify_json(doc, ver)
    if method == "sql_output":
        return _verify_sql_output(doc, ver)
    if method == "sql":
        return _verify_sql(doc, ver)
    return "unverified", [f"unknown verification method '{method}'"]


def validate_question(doc: dict) -> list[str]:
    try:
        q = QuestionContent.model_validate(doc)
    except ValidationError as exc:
        return [f"schema: {e['loc']} {e['msg']}" for e in exc.errors()[:5]]

    problems: list[str] = []
    if TOPIC_TO_UNIT.get(q.topic_id) != q.unit_id:
        problems.append("topic does not belong to the unit (or is unknown)")
    if q.question_id != question_id_for(q.topic_id, q.statement, q.code):
        problems.append("question_id is not the stable id for this content")
    text = " ".join([q.statement, q.explanation, q.code or "", *q.options])
    if _REAL_EXAM_CLAIM.search(text):
        problems.append("must not claim the question appeared in a real exam")
    framing = " ".join([q.statement, q.code or ""])  # distractor options may legitimately list several dialects
    if q.dialect == "standard" and (_VENDOR_SQL.search(framing) or _VENDOR_MONGO.search(framing)):
        problems.append("vendor-specific syntax must declare its dialect (it is not standard SQL)")
    if q.interaction == "sql" and q.dialect != "sqlite":
        problems.append("SQL-lab questions run on SQLite and must declare dialect 'sqlite'")
    if q.dataset_id is not None and q.dataset_id not in datasets.dataset_ids():
        problems.append("unknown dataset")
    if q.interaction == "sql" and not q.hints:
        problems.append("SQL questions need at least one hint")
    for need in q.requires:
        caps = sandbox.capabilities()
        if need == "window_functions" and not caps["window_functions"]:
            problems.append("requires window functions, which this SQLite lacks")
        if need == "right_join" and not caps["right_full_join"]:
            problems.append("requires RIGHT/FULL JOIN, which this SQLite lacks")
    if q.interaction == "mcq":
        if len({normalize(o) for o in q.options}) != 4:
            problems.append("options must be four distinct values")
        if any(_AMBIGUOUS.search(o) for o in q.options):
            problems.append("'all/none of the above' options are not allowed")
    review, vproblems = verify_question(doc)
    problems.extend(vproblems)
    if q.status == "active" and review == "unverified":
        problems.append("an active question must carry a passing verification")
    return problems
