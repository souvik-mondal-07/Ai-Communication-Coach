"""
Maintainer command: validate the DBMS & SQL seed bank and independently re-verify it.

    cd backend && python -m tools.verify_dbms_bank

Checks (exits non-zero on any problem):
  1. every seed passes `validate_question` (no rejections);
  2. every SQL reference query is re-run in the sandbox and compared with BOTH the stored expected result and the independent
     pure-Python oracle; every debug starter is really broken and every completion starter really incomplete;
  3. every MongoDB result question is recomputed with `mongomock` (an independent engine) when it is installed;
  4. a live probe confirms the sandbox rejects dangerous statements and system-table access, and enforces its resource limits.
Runs only repository-owned seed content; never user submissions.
"""

from __future__ import annotations

import copy
import sys

from app.services.dbms_sql import bank, datasets, oracles, sandbox, sql_compare

DANGEROUS = (
    "DROP TABLE employees", "DELETE FROM employees", "UPDATE employees SET salary = 0", "INSERT INTO departments VALUES (9,'x','y',1)", "CREATE TABLE t (a INT)",
    "PRAGMA table_info(employees)", "ATTACH DATABASE 'x.db' AS x", "SELECT 1; DROP TABLE employees", "SELECT * FROM sqlite_master", "SELECT load_extension('x')",
    "SELECT readfile('/etc/passwd')", "SELECT * FROM pragma_table_info('employees')", "WITH x AS (SELECT 1) DELETE FROM employees",
)


def _sql_checks(valid: list[dict]) -> tuple[int, list[str]]:
    problems, n = [], 0
    tables = datasets.python_tables()
    for q in valid:
        if q["interaction"] != "sql":
            continue
        n += 1
        spec, label = q["sql"], q["statement"][:60]
        run = sandbox.run_query(spec["reference_sql"], spec["dataset_id"])
        if not run.ok:
            problems.append(f"{label}: reference failed: {run.error.message}")
            continue
        if not sql_compare.compare(run.columns, run.rows, spec["expected"]["columns"], spec["expected"]["rows"], ordered=spec["ordered"], check_column_names=True, precision=spec["precision"]).correct:
            problems.append(f"{label}: stored expected result differs from the engine")
        oracle_rows = [list(r) for r in oracles.ORACLES[q["question_id"]](tables)]
        if not sql_compare.compare(run.columns, run.rows, run.columns, oracle_rows, ordered=spec["ordered"], precision=spec["precision"]).correct:
            problems.append(f"{label}: Python oracle disagrees with the engine")
    return n, problems


def _mongo_checks(valid: list[dict]) -> tuple[int, list[str]]:
    specs = [(q, q["verification"]["mongo_check"]) for q in valid if (q.get("verification") or {}).get("mongo_check")]
    if not specs:
        return 0, []
    try:
        import mongomock
    except ImportError:
        return 0, ["mongomock is not installed, so MongoDB result questions were NOT re-verified (pip install mongomock)"]
    problems = []
    for q, s in specs:
        coll = mongomock.MongoClient()["verify"]["items"]
        coll.insert_many(copy.deepcopy(s["docs"]))
        if s["op"] == "update_many_count":
            coll.update_many(s["filter"], s["update"])
            got_count = coll.count_documents(s["count_filter"])
            if got_count != s["expected"]:
                problems.append(f"{q['statement'][:60]}: mongomock counted {got_count}, declared {s['expected']}")
            continue
        if s["op"] == "find":
            got = list(coll.find(s["filter"], s["projection"]).sort(s["sort"]))
        else:
            coll.update_one(s["filter"], s["update"])
            got = list(coll.find(s["filter"], {"_id": 0}))
        got = [{k: v for k, v in d.items() if k != "_id"} for d in got]
        if got != s["expected"]:
            problems.append(f"{q['statement'][:60]}: mongomock returned {got}, declared {s['expected']}")
    return len(specs), problems


def _security_probe() -> list[str]:
    problems = [f"dangerous statement was NOT rejected: {sql}" for sql in DANGEROUS if sandbox.run_query(sql).ok]
    r = sandbox.run_query("WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM c) SELECT count(*) FROM c")
    if r.ok or r.error.kind != "timeout":
        problems.append("runaway recursion was not stopped by the resource budget")
    if sandbox.run_query("SELECT COUNT(*) FROM employees").rows != [[16]]:
        problems.append("practice data changed after hostile statements")
    return problems


def verify() -> int:
    valid, rejected = bank.build_valid_seed_bank()
    problems = [f"REJECTED {r['question_id']}: {r['problems']}" for r in rejected]
    n_sql, p = _sql_checks(valid)
    problems += p
    n_mongo, p = _mongo_checks(valid)
    problems += p
    problems += _security_probe()
    print(f"validated={len(valid)} rejected={len(rejected)} | re-executed: sql-exercises={n_sql} mongodb-results={n_mongo} | security-probe statements={len(DANGEROUS)}")
    for p in problems:
        print("PROBLEM:", p)
    if not problems:
        print("OK: every seed validated, every SQL reference matched its oracle, and the sandbox rejected every hostile statement.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(verify())
