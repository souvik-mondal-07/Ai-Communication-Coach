"""
Isolated SQL practice sandbox (Phase 25).

WHAT THIS IS
    A read-only SQLite engine over a disposable, predefined, in-memory dataset. User SQL is never run against the
    application's MongoDB, any file, or any other database.

HOW IT IS ISOLATED (defence in depth; no single control is relied on)
    1. Fresh copy per run: the practice database image is deserialized into a brand-new ``:memory:`` connection for every
       execution and closed afterwards. There is no shared connection, no file, no cross-user or cross-session state.
    2. Statement gate (real lexer, not substrings): comments, strings and quoted identifiers are tokenised properly. Only a
       single SELECT / WITH / VALUES statement, or ``EXPLAIN QUERY PLAN <select>``, is accepted. Multiple statements, bare
       ``EXPLAIN``, PRAGMA, ATTACH, DDL, DML and transaction control are rejected before SQLite sees them.
    3. Engine-level authorizer (the actual enforcement): SQLite asks our callback about every action while it compiles the
       statement. We allow only SELECT, reads of the six practice tables, recursion, and a whitelist of pure scalar /
       aggregate / window functions. Everything else (writes, ATTACH, PRAGMA, virtual tables, ``sqlite_master``,
       ``load_extension``, ``readfile``, ``randomblob`` ...) is denied by SQLite itself.
    4. ``PRAGMA query_only`` and ``trusted_schema=OFF`` are set before the authorizer is installed; extension loading is
       never enabled.
    5. Resource limits: SQL length, result rows, cell length, wall-clock time and a deterministic VM-step budget enforced by
       SQLite's progress handler (so runaway joins and recursive CTEs are interrupted), plus SQLite's own per-statement
       limits (expression depth, compound selects, columns, LIKE pattern, function arguments, string length).
    6. Safe errors: failures are mapped to short, user-facing categories. Tracebacks, paths and internals never leave
       this module.

WHAT THIS IS NOT
    It is not a general database service and it makes no claim to run untrusted *code*: only SQL, through the controls
    above. It does not emulate other vendors. See docs/PHASE25_DBMS_SQL.md for the supported dialect and limitations.
"""

from __future__ import annotations

import math
import re
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from app.services.dbms_sql import datasets

MAX_SQL_CHARS = 4000
MAX_ROWS = 200
MAX_COLUMNS = 30
MAX_CELL_CHARS = 200
MAX_SECONDS = 1.5
MAX_VM_STEPS = 3_000_000
PROGRESS_EVERY = 1000

# Pure, deterministic-enough functions only. No random/blob/file/extension/introspection functions.
ALLOWED_FUNCTIONS = frozenset({
    "abs", "avg", "coalesce", "count", "ifnull", "iif", "instr", "length", "lower", "ltrim", "max", "min", "nullif",
    "replace", "round", "rtrim", "substr", "substring", "sum", "total", "trim", "upper", "typeof", "group_concat",
    "like", "glob", "printf", "format", "date", "datetime", "julianday", "strftime", "time",
    "row_number", "rank", "dense_rank", "percent_rank", "cume_dist", "ntile", "lag", "lead", "first_value",
    "last_value", "nth_value",
})

# sqlite3 authorizer action codes (stable SQLite constants)
_OK, _DENY = sqlite3.SQLITE_OK, sqlite3.SQLITE_DENY
_A_SELECT, _A_READ, _A_FUNCTION, _A_RECURSIVE = 21, 20, 31, 33

SUPPORTED_STATEMENTS = ("SELECT", "WITH ... SELECT", "VALUES", "EXPLAIN QUERY PLAN SELECT ...")


@dataclass(frozen=True)
class SqlError:
    kind: str  # syntax | unknown_object | not_allowed | unsupported | timeout | limit | runtime | empty
    message: str


@dataclass
class RunResult:
    ok: bool
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    elapsed_ms: int
    error: SqlError | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok, "columns": self.columns, "rows": self.rows, "row_count": self.row_count, "truncated": self.truncated,
            "elapsed_ms": self.elapsed_ms, "error": None if self.error is None else {"kind": self.error.kind, "message": self.error.message},
        }


def capabilities() -> dict[str, Any]:
    """What the installed SQLite supports. Surfaced to the UI so dialect limits are honest, not assumed."""
    v = sqlite3.sqlite_version_info
    return {
        "engine": "SQLite", "version": sqlite3.sqlite_version, "window_functions": v >= (3, 25, 0),
        "right_full_join": v >= (3, 39, 0), "dialect": "sqlite", "read_only": True,
        "limits": {"max_sql_chars": MAX_SQL_CHARS, "max_rows": MAX_ROWS, "max_seconds": MAX_SECONDS, "supported_statements": list(SUPPORTED_STATEMENTS)},
    }


# --- Lexer ---------------------------------------------------------------------------------------------------------


class _LexError(Exception):
    pass


_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
_NUMBER = re.compile(r"(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def _lex(sql: str) -> list[tuple[str, str]]:
    """Tokenise SQL into (kind, text), skipping whitespace and comments. Raises _LexError on unterminated constructs."""
    tokens: list[tuple[str, str]] = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if c.isspace():
            i += 1
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j == -1 else j + 1
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j == -1:
                raise _LexError("unterminated comment")
            i = j + 2
        elif c in "'\"`":
            j = i + 1
            while True:
                j = sql.find(c, j)
                if j == -1:
                    raise _LexError("unterminated string or quoted name")
                if j + 1 < n and sql[j + 1] == c:  # doubled quote escapes itself
                    j += 2
                    continue
                break
            tokens.append(("string" if c == "'" else "ident", sql[i : j + 1]))
            i = j + 1
        elif c == "[":
            j = sql.find("]", i)
            if j == -1:
                raise _LexError("unterminated [identifier]")
            tokens.append(("ident", sql[i : j + 1]))
            i = j + 1
        elif c == ";":
            tokens.append(("semi", ";"))
            i += 1
        else:
            m = _WORD.match(sql, i) or _NUMBER.match(sql, i)
            if m:
                tokens.append(("word" if _WORD.match(sql, i) else "number", m.group(0)))
                i = m.end()
            else:
                tokens.append(("punct", c))
                i += 1
    return tokens


_SAFE_CTE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
# Eponymous / system objects that must never be reachable, even if a query names a CTE after them.
_BLOCKED_NAMES = frozenset({"json_each", "json_tree", "dbstat", "generate_series", "carray", "completion", "bytecode", "tables_used", "csv", "zipfile", "fsdir"})
_DANGEROUS_FIRST = frozenset({
    "INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER", "PRAGMA", "ATTACH", "DETACH", "VACUUM", "REINDEX", "ANALYZE",
    "BEGIN", "COMMIT", "END", "ROLLBACK", "SAVEPOINT", "RELEASE", "GRANT", "REVOKE", "TRUNCATE", "MERGE", "CALL", "EXEC", "EXECUTE",
    "SET", "USE", "SHOW", "DESCRIBE", "LOAD", "COPY",
})


def _unquote(text: str) -> str:
    if len(text) >= 2 and text[0] in "\"`[" and text[-1] in "\"`]":
        return text[1:-1]
    return text


def _cte_names(tokens: list[tuple[str, str]]) -> frozenset[str]:
    """Names declared by WITH clauses anywhere in the statement (needed because SQLite reports `count(*) FROM cte` as a name-only read)."""
    n = len(tokens)

    def after_parens(j: int) -> int:
        depth = 0
        while j < n:
            kind, text = tokens[j]
            if kind == "punct" and text == "(":
                depth += 1
            elif kind == "punct" and text == ")":
                depth -= 1
                if depth == 0:
                    return j + 1
            j += 1
        return n

    def is_word(j: int, *words: str) -> bool:
        return j < n and tokens[j][0] == "word" and tokens[j][1].upper() in words

    names: set[str] = set()
    for i, (kind, text) in enumerate(tokens):
        if kind != "word" or text.upper() != "WITH":
            continue
        j = i + 1
        if is_word(j, "RECURSIVE"):
            j += 1
        while j < n and tokens[j][0] in ("word", "ident"):
            name = _unquote(tokens[j][1]).lower()
            j += 1
            if j < n and tokens[j] == ("punct", "("):
                j = after_parens(j)
            if not is_word(j, "AS"):
                break
            j += 1
            while is_word(j, "NOT", "MATERIALIZED"):
                j += 1
            if not (j < n and tokens[j] == ("punct", "(")):
                break
            names.add(name)
            j = after_parens(j)
            if j < n and tokens[j] == ("punct", ","):
                j += 1
                continue
            break
    return frozenset(names)


def _usable_cte_names(names: frozenset[str]) -> frozenset[str]:
    return frozenset(n for n in names if _SAFE_CTE_NAME.match(n) and not n.startswith(("sqlite_", "pragma_")) and n not in _BLOCKED_NAMES)


def check_statement(sql: str) -> SqlError | None:
    """Fast, lexer-based gate. The engine authorizer remains the real enforcement; this gives clear early messages."""
    if not isinstance(sql, str) or not sql.strip():
        return SqlError("empty", "Write a query first.")
    if len(sql) > MAX_SQL_CHARS:
        return SqlError("limit", f"The query is too long (limit {MAX_SQL_CHARS} characters).")
    if "\x00" in sql:
        return SqlError("not_allowed", "The query contains an invalid character.")
    try:
        tokens = _lex(sql)
    except _LexError as exc:
        return SqlError("syntax", f"SQL syntax error: {exc}.")
    if not tokens:
        return SqlError("empty", "Write a query first.")
        
    # Reject excessively nested expressions before passing SQL to SQLite.
    max_nesting_depth = 50
    nesting_depth = 0

    for kind, value in tokens:
        if kind != "punct":
            continue

        if value == "(":
            nesting_depth += 1
            if nesting_depth > max_nesting_depth:
                return SqlError(
                    "limit",
                    "The query is too deeply nested for the practice sandbox.",
                )
        elif value == ")":
            nesting_depth = max(0, nesting_depth - 1)

    semis = [i for i, (k, _) in enumerate(tokens) if k == "semi"]
    if semis and (semis[0] != len(tokens) - 1 or len(semis) > 1):
        return SqlError("not_allowed", "Only one statement can be run at a time. Remove the extra statement after the semicolon.")
    words = [t.upper() for k, t in tokens if k == "word"]
    first = tokens[0][1].upper() if tokens[0][0] == "word" else ""
    if first == "EXPLAIN":
        if words[:3] != ["EXPLAIN", "QUERY", "PLAN"]:
            return SqlError("not_allowed", "Only EXPLAIN QUERY PLAN is supported (bytecode EXPLAIN is not).")
        rest = tokens[3] if len(tokens) > 3 else None
        if rest is None or rest[0] != "word" or rest[1].upper() not in ("SELECT", "WITH", "VALUES"):
            return SqlError("not_allowed", "EXPLAIN QUERY PLAN must be followed by a SELECT query.")
        return None
    if first not in ("SELECT", "WITH", "VALUES"):
        if first in _DANGEROUS_FIRST:
            return SqlError("not_allowed", f"{first} is not allowed in the practice sandbox. Only read-only SELECT queries (including WITH, subqueries and window functions) can be run.")
        found = tokens[0][1][:20] if tokens[0][0] in ("word", "ident") else "that"
        return SqlError("syntax", f"A query must start with SELECT or WITH (found '{found}'). Check the spelling of the first keyword.")
    return None


# --- Execution -----------------------------------------------------------------------------------------------------


def _make_authorizer(tables: frozenset[str], cte_names: frozenset[str] = frozenset()):
    allowed_tables = {t.lower() for t in tables}
    allowed_names = allowed_tables | cte_names

    def authorizer(action: int, arg1: str | None, arg2: str | None, dbname: str | None, _source: str | None) -> int:
        if action == _A_SELECT or action == _A_RECURSIVE:
            return _OK
        if action == _A_READ:
            name = (arg1 or "").lower()
            if dbname == "main":  # a real column read: must be one of the practice tables
                return _OK if name in allowed_tables else _DENY
            if dbname in (None, "") and not arg2:  # name-only read (e.g. count(*)): a practice table or a declared CTE
                return _OK if name in allowed_names else _DENY
            return _DENY
        if action == _A_FUNCTION:
            return _OK if (arg2 or arg1 or "").lower() in ALLOWED_FUNCTIONS else _DENY
        return _DENY  # PRAGMA, ATTACH, INSERT, UPDATE, DELETE, CREATE_*, DROP_*, ALTER, TRANSACTION, VTABLE, ...

    return authorizer


def _apply_limits(conn: sqlite3.Connection) -> None:
    limits = {
        "SQLITE_LIMIT_SQL_LENGTH": MAX_SQL_CHARS + 100, "SQLITE_LIMIT_LENGTH": 100_000, "SQLITE_LIMIT_COLUMN": MAX_COLUMNS,
        "SQLITE_LIMIT_EXPR_DEPTH": 50, "SQLITE_LIMIT_COMPOUND_SELECT": 10, "SQLITE_LIMIT_VDBE_OP": 20_000,
        "SQLITE_LIMIT_FUNCTION_ARG": 8, "SQLITE_LIMIT_ATTACHED": 0, "SQLITE_LIMIT_LIKE_PATTERN_LENGTH": 100,
        "SQLITE_LIMIT_VARIABLE_NUMBER": 0,
    }
    for name, value in limits.items():
        const = getattr(sqlite3, name, None)
        if const is not None:
            conn.setlimit(const, value)


def _open(dataset_id: str, cte_names: frozenset[str] = frozenset()) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=True)
    try:
        conn.deserialize(datasets.image(dataset_id))
        conn.execute("PRAGMA query_only = ON")
        conn.execute("PRAGMA trusted_schema = OFF")
        _apply_limits(conn)
        conn.set_authorizer(_make_authorizer(datasets.table_names(dataset_id), cte_names))
        return conn
    except Exception:
        conn.close()
        raise


def _cell(value: Any) -> Any:
    if value is None or isinstance(value, (int, str)):
        if isinstance(value, str) and len(value) > MAX_CELL_CHARS:
            return value[:MAX_CELL_CHARS] + "…"
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else ("Infinity" if value > 0 else ("-Infinity" if value < 0 else "NaN"))
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "<binary>"
    return str(value)[:MAX_CELL_CHARS]


_UNKNOWN_TABLE = re.compile(r"no such table: ([\w.$]+)")
_UNKNOWN_COLUMN = re.compile(r"no such column: ([\w.$\"]+)")
_NEAR = re.compile(r'near "([^"]{1,40})": syntax error')


def _map_error(exc: sqlite3.Error, dataset_id: str) -> SqlError:
    msg = str(exc)
    low = msg.lower()
    if "interrupted" in low:
        return SqlError("timeout", f"The query used too many resources and was stopped (limit {MAX_SECONDS:g}s / {MAX_VM_STEPS // 1_000_000}M steps). Add a filter, remove unneeded joins, or check for unbounded recursion.")
    if "not authorized" in low or "unauthorized" in low or "prohibited" in low:
        return SqlError("not_allowed", "That statement, table or function is not allowed in the practice sandbox. Only read-only queries over the six practice tables, with standard aggregate, string, date and window functions, can be run.")
    if "attempt to write a readonly" in low or "readonly" in low:
        return SqlError("not_allowed", "The practice database is read-only.")
    if m := _UNKNOWN_TABLE.search(msg):
        names = ", ".join(datasets.TABLE_ORDER)
        return SqlError("unknown_object", f"Unknown table '{m.group(1)}'. Available tables: {names}.")
    if m := _UNKNOWN_COLUMN.search(msg):
        return SqlError("unknown_object", f"Unknown column {m.group(1)}. Check the schema for the exact column names.")
    if "ambiguous column name" in low:
        return SqlError("syntax", f"{msg[:120]}. Qualify the column with its table alias (e.g. e.name).")
    if "right and full outer joins are not currently supported" in low or "right and full" in low:
        return SqlError("unsupported", "This SQLite version does not support RIGHT or FULL OUTER JOIN. Use a LEFT JOIN with the tables swapped (and UNION for FULL).")
    if "window" in low and ("no such function" in low or "syntax" in low) and not capabilities()["window_functions"]:
        return SqlError("unsupported", "This SQLite version does not support window functions (3.25 or newer is required).")
    if m := _NEAR.search(msg):
        return SqlError("syntax", f"SQL syntax error near \"{m.group(1)}\". Check commas, keywords and parentheses.")
    if "syntax error" in low or "incomplete input" in low:
        return SqlError("syntax", "SQL syntax error. Check commas, keywords and parentheses.")
    if "too many" in low or "too long" in low or "too large" in low or "expression tree" in low:
        return SqlError("limit", "The query is too large or too deeply nested for the practice sandbox.")
    if "no such function" in low:
        name = msg.split(":")[-1].strip()[:40]
        return SqlError("not_allowed", f"Function {name} is not available in the practice sandbox.")
    if "misuse of aggregate" in low or "misuse of window" in low:
        return SqlError("syntax", f"{msg[:140]}. Aggregates cannot be used in WHERE; use HAVING or a subquery.")
    if "datatype mismatch" in low or "integer overflow" in low:
        return SqlError("runtime", "A value had an unexpected type or was out of range.")
    return SqlError("runtime", f"The query could not be executed: {msg[:140]}")


def run_query(sql: str, dataset_id: str = datasets.DEFAULT_DATASET, *, max_rows: int = MAX_ROWS) -> RunResult:
    """Run one read-only statement against a fresh copy of the dataset. Never raises for user mistakes."""
    started = time.monotonic()

    def done(**kw: Any) -> RunResult:
        return RunResult(elapsed_ms=int((time.monotonic() - started) * 1000), **kw)

    gate = check_statement(sql)
    if gate is not None:
        return done(ok=False, columns=[], rows=[], row_count=0, truncated=False, error=gate)
    try:
        conn = _open(dataset_id, _usable_cte_names(_cte_names(_lex(sql))))
    except KeyError:
        return done(ok=False, columns=[], rows=[], row_count=0, truncated=False, error=SqlError("not_allowed", "Unknown practice dataset."))
    except sqlite3.Error:
        return done(ok=False, columns=[], rows=[], row_count=0, truncated=False, error=SqlError("runtime", "The practice database is temporarily unavailable."))

    steps = {"n": 0}
    deadline = started + MAX_SECONDS

    def budget() -> int:
        steps["n"] += PROGRESS_EVERY
        return 1 if (steps["n"] > MAX_VM_STEPS or time.monotonic() > deadline) else 0

    try:
        conn.set_progress_handler(budget, PROGRESS_EVERY)
        cur = conn.execute(sql)
        columns = [d[0] for d in (cur.description or [])]
        if not columns:
            return done(ok=False, columns=[], rows=[], row_count=0, truncated=False, error=SqlError("not_allowed", "Only queries that return rows can be run."))
        fetched = cur.fetchmany(max_rows + 1)
        truncated = len(fetched) > max_rows
        rows = [[_cell(v) for v in r] for r in fetched[:max_rows]]
        return done(ok=True, columns=columns, rows=rows, row_count=len(rows), truncated=truncated)
    except sqlite3.Error as exc:
        return done(ok=False, columns=[], rows=[], row_count=0, truncated=False, error=_map_error(exc, dataset_id))
    except Exception:  # noqa: BLE001 - nothing internal may reach the caller
        return done(ok=False, columns=[], rows=[], row_count=0, truncated=False, error=SqlError("runtime", "The query could not be executed."))
    finally:
        conn.close()
