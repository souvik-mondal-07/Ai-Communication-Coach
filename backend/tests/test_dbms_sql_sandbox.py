"""Phase 25 -- SQL sandbox: supported SQL, rejection of unsafe SQL (gate AND engine), isolation, and resource limits."""

from __future__ import annotations

import sqlite3

import pytest

from app.services.dbms_sql import datasets, sandbox


def run(sql: str):
    return sandbox.run_query(sql)


class TestSupportedSql:
    def test_basic_select(self):
        r = run("SELECT name, salary FROM employees WHERE dept_id = 1 ORDER BY salary DESC, name")
        assert r.ok and r.columns == ["name", "salary"] and r.rows[0] == ["Asha", 150000] and r.row_count == 6

    @pytest.mark.parametrize("sql", [
        "SELECT d.dept_name, COUNT(e.emp_id) FROM departments d LEFT JOIN employees e ON e.dept_id = d.dept_id GROUP BY d.dept_id",
        "SELECT name FROM employees WHERE salary > (SELECT AVG(salary) FROM employees)",
        "SELECT name, RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) FROM employees",
        "WITH c(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM c WHERE n < 5) SELECT n FROM c",
        "WITH c(n) AS (SELECT 1) SELECT count(*) FROM c",
        "SELECT city FROM customers UNION SELECT location FROM departments",
        "SELECT ROUND(AVG(amount), 2), SUM(amount), MIN(amount), MAX(amount), COUNT(*) FROM orders",
        "SELECT COALESCE(salary, 0), UPPER(name), LENGTH(name), SUBSTR(name, 1, 2) FROM employees",
        "VALUES (1), (2)",
        "-- a comment first\nSELECT 1;",
        "/* block */ SELECT 1",
        "SELECT 'it''s; fine' AS s",
        "EXPLAIN QUERY PLAN SELECT * FROM employees WHERE dept_id = 2",
    ])
    def test_allowed(self, sql):
        r = run(sql)
        assert r.ok, r.error

    def test_semicolon_inside_string_is_not_a_second_statement(self):
        assert run("SELECT 'a;b'").ok

    def test_explain_query_plan_reports_index_use(self):
        r = run("EXPLAIN QUERY PLAN SELECT * FROM employees WHERE dept_id = 2")
        assert any("idx_employees_dept" in str(row[3]) for row in r.rows)

    def test_capabilities_are_reported_honestly(self):
        caps = sandbox.capabilities()
        assert caps["engine"] == "SQLite" and caps["read_only"] is True and caps["window_functions"] is True
        assert caps["limits"]["max_rows"] == sandbox.MAX_ROWS


class TestUnsafeSqlRejectedByGate:
    @pytest.mark.parametrize("sql,kind", [
        ("DROP TABLE employees", "not_allowed"),
        ("DELETE FROM employees", "not_allowed"),
        ("UPDATE employees SET salary = 0", "not_allowed"),
        ("INSERT INTO departments VALUES (9, 'x', 'y', 1)", "not_allowed"),
        ("CREATE TABLE t (a INT)", "not_allowed"),
        ("ALTER TABLE employees ADD COLUMN x INT", "not_allowed"),
        ("PRAGMA table_info(employees)", "not_allowed"),
        ("ATTACH DATABASE 'x.db' AS x", "not_allowed"),
        ("DETACH DATABASE main", "not_allowed"),
        ("VACUUM", "not_allowed"),
        ("BEGIN", "not_allowed"),
        ("COMMIT", "not_allowed"),
        ("REPLACE INTO departments VALUES (1,'a','b',1)", "not_allowed"),
        ("EXPLAIN SELECT 1", "not_allowed"),
        ("SELECT 1; DROP TABLE employees", "not_allowed"),
        ("SELECT 1; SELECT 2", "not_allowed"),
        ("SELECT 1;;", "not_allowed"),
        ("SELEC 1", "syntax"),
        ("", "empty"),
        ("   \n  ", "empty"),
        ("-- only a comment", "empty"),
        ("SELECT 'unterminated", "syntax"),
        ("SELECT 1 /* unterminated", "syntax"),
    ])
    def test_rejected_with_safe_message(self, sql, kind):
        r = run(sql)
        assert not r.ok and r.error.kind == kind
        assert "Traceback" not in r.error.message and "sqlite3" not in r.error.message.lower()

    def test_comment_cannot_hide_a_dangerous_statement(self):
        assert not run("/* SELECT */ DROP TABLE employees").ok
        assert not run("-- SELECT 1\nDROP TABLE employees").ok

    def test_too_long_query_rejected(self):
        r = run("SELECT " + "1," * 3000 + "1")
        assert not r.ok and r.error.kind == "limit"

    def test_null_byte_rejected(self):
        assert not run("SELECT 1\x00; DROP TABLE employees").ok


class TestEngineEnforcesReadOnlyEvenIfGateIsBypassed:
    """These call SQLite directly on a sandbox connection, skipping our lexer, to prove the engine-level controls hold alone."""

    @pytest.fixture()
    def conn(self):
        c = sandbox._open("practice")
        yield c
        c.close()

    @pytest.mark.parametrize("sql", [
        "DELETE FROM employees", "UPDATE employees SET salary = 1", "INSERT INTO departments VALUES (9,'x','y',1)", "DROP TABLE employees",
        "CREATE TABLE t (a INT)", "CREATE VIEW v AS SELECT 1", "CREATE TRIGGER t AFTER INSERT ON departments BEGIN SELECT 1; END", "ALTER TABLE employees ADD COLUMN x INT",
        "PRAGMA table_info(employees)", "PRAGMA query_only = OFF", "ATTACH DATABASE ':memory:' AS z", "VACUUM", "REINDEX", "ANALYZE",
        "CREATE VIRTUAL TABLE v USING fts5(a)", "BEGIN", "SAVEPOINT s",
    ])
    def test_blocked_by_the_engine(self, conn, sql):
        with pytest.raises(sqlite3.Error):
            conn.execute(sql)

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM sqlite_master", "SELECT * FROM sqlite_schema", "SELECT * FROM sqlite_temp_master", "SELECT count(*) FROM sqlite_master",
        "SELECT * FROM pragma_table_info('employees')", "SELECT * FROM pragma_function_list", "SELECT * FROM json_each('[1]')",
        "SELECT load_extension('x')", "SELECT randomblob(8)", "SELECT zeroblob(1000000)", "SELECT readfile('/etc/passwd')", "SELECT sqlite_version()",
        "SELECT random()", "SELECT fts3_tokenizer('x')", "SELECT * FROM temp.sqlite_master",
    ])
    def test_system_objects_and_dangerous_functions_blocked(self, conn, sql):
        with pytest.raises(sqlite3.Error):
            conn.execute(sql).fetchall()

    def test_data_is_untouched_after_attempts(self, conn):
        for sql in ("DELETE FROM employees", "DROP TABLE employees"):
            with pytest.raises(sqlite3.Error):
                conn.execute(sql)
        assert conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 16

    def test_extension_loading_is_not_enabled(self, conn):
        with pytest.raises((sqlite3.Error, AttributeError)):
            conn.load_extension("nonexistent")


class TestUnsafeSqlViaRunQuery:
    @pytest.mark.parametrize("sql", [
        "SELECT * FROM sqlite_master",
        "SELECT count(*) FROM sqlite_master",
        "WITH sqlite_master AS (SELECT 1) SELECT count(*) FROM main.sqlite_master",
        "WITH json_each AS (SELECT 1) SELECT count(*) FROM main.json_each",
        "SELECT * FROM pragma_table_info('employees')",
        "SELECT count(*) FROM pragma_function_list",
        "SELECT load_extension('x')",
        "SELECT randomblob(1000000)",
        "SELECT readfile('/etc/passwd')",
        "WITH x AS (SELECT 1) DELETE FROM employees",
        "WITH x AS (SELECT 1) INSERT INTO departments SELECT 1,'a','b',1",
        "SELECT * FROM temp.sqlite_master",
        "SELECT * FROM users",
        "SELECT * FROM main.users",
    ])
    def test_access_outside_the_practice_dataset_is_rejected(self, sql):
        r = run(sql)
        assert not r.ok and r.error.kind in ("not_allowed", "unknown_object")
        assert r.rows == []

    def test_unknown_table_message_lists_the_practice_tables(self):
        r = run("SELECT * FROM users")
        assert r.error.kind == "unknown_object" and "employees" in r.error.message

    def test_error_messages_never_leak_internals(self):
        for sql in ("SELECT * FROM nope", "SELECT nope FROM employees", "SELEC 1", "SELECT * FROM sqlite_master", "SELECT 1 FROM employees GROUP BY"):
            r = run(sql)
            assert not r.ok
            text = r.error.message
            assert "Traceback" not in text and ".py" not in text and "/home" not in text and "sqlite3." not in text


class TestIsolation:
    def test_every_run_gets_a_fresh_copy(self):
        a = sandbox._open("practice")
        b = sandbox._open("practice")
        assert a is not b
        assert a.execute("SELECT COUNT(*) FROM employees").fetchone() == b.execute("SELECT COUNT(*) FROM employees").fetchone()
        a.close()
        b.close()

    def test_repeated_runs_are_identical(self):
        first = run("SELECT * FROM employees ORDER BY emp_id")
        for _ in range(3):
            assert run("SELECT * FROM employees ORDER BY emp_id").rows == first.rows

    def test_no_file_is_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        run("SELECT * FROM employees")
        run("DROP TABLE employees")
        assert list(tmp_path.iterdir()) == []

    def test_unknown_dataset_is_refused(self):
        r = sandbox.run_query("SELECT 1", "no-such-dataset")
        assert not r.ok and r.error.kind == "not_allowed"

    def test_dataset_image_is_not_mutated_by_runs(self):
        before = datasets.image("practice")
        run("SELECT * FROM employees")
        assert datasets.image("practice") == before


class TestResourceLimits:
    def test_runaway_recursion_is_stopped(self):
        r = run("WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM c) SELECT count(*) FROM c")
        assert not r.ok and r.error.kind == "timeout"
        assert r.elapsed_ms < sandbox.MAX_SECONDS * 1000 + 1500

    def test_unbounded_recursion_without_aggregate_is_capped_by_row_limit(self):
        r = run("WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM c) SELECT n FROM c")
        assert r.ok and r.truncated and r.row_count == sandbox.MAX_ROWS

    def test_cross_join_explosion_is_stopped(self):
        r = run("SELECT count(*) FROM employees a, employees b, employees c, employees d, employees e, employees f, employees g, employees h, employees i")
        assert not r.ok and r.error.kind == "timeout"

    def test_row_limit_and_truncation_flag(self):
        r = run("WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM c WHERE n < 1000) SELECT n FROM c")
        assert r.ok and r.row_count == sandbox.MAX_ROWS and r.truncated is True

    def test_small_results_are_not_truncated(self):
        r = run("SELECT * FROM departments")
        assert r.ok and not r.truncated and r.row_count == 5

    def test_wide_results_are_rejected(self):
        cols = ", ".join(f"{i} AS c{i}" for i in range(sandbox.MAX_COLUMNS + 5))
        r = run(f"SELECT {cols}")
        assert not r.ok

    def test_deep_expression_is_rejected_safely(self):
        r = run("SELECT " + "(" * 200 + "1" + ")" * 200)
        assert not r.ok and r.error.kind in ("limit", "syntax", "runtime")

    def test_long_cell_values_are_clipped(self):
        r = run("SELECT replace(printf('%0100d', 0), '0', 'abcdefghij')")
        assert r.ok and len(r.rows[0][0]) <= sandbox.MAX_CELL_CHARS + 1


class TestResultFormatting:
    def test_null_and_float_values_are_json_safe(self):
        r = run("SELECT NULL, 1.5, 9e999, -9e999")
        assert r.ok and r.rows[0][0] is None and r.rows[0][1] == 1.5 and r.rows[0][2] == "Infinity" and r.rows[0][3] == "-Infinity"

    def test_to_dict_shape(self):
        d = run("SELECT 1 AS one").to_dict()
        assert d["ok"] and d["columns"] == ["one"] and d["rows"] == [[1]] and d["error"] is None

    def test_failed_run_shape(self):
        d = run("DROP TABLE x").to_dict()
        assert d["ok"] is False and d["rows"] == [] and d["error"]["kind"] == "not_allowed"


class TestDialectLimits:
    def test_right_join_works_or_reports_a_clear_unsupported_message(self):
        r = run("SELECT e.name FROM employees e RIGHT JOIN departments d ON e.dept_id = d.dept_id")
        assert r.ok or r.error.kind == "unsupported"

    def test_vendor_syntax_is_a_syntax_or_unsupported_error_not_a_crash(self):
        for sql in ("SELECT TOP 5 * FROM employees", "SELECT * FROM employees FETCH FIRST 3 ROWS ONLY", "SELECT NVL(salary, 0) FROM employees"):
            r = run(sql)
            assert not r.ok and r.error.kind in ("syntax", "not_allowed", "runtime")
