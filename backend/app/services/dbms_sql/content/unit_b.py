"""Unit B: Relational query language. Theory MCQs, key analysis (machine-checked), and SQL exercises with independent oracles."""

from __future__ import annotations

from app.services.dbms_sql.content.build import mcq as M, outq as O, short as S, sqlq as Q


def _by_sal_desc_name(e):
    return (e["salary"] is None, -(e["salary"] or 0), e["name"])


def questions() -> list[dict]:
    return [
        # ddl-dml-dcl-tcl
        M("ddl-dml-dcl-tcl", "easy", "Which statement belongs to the Data Definition Language (DDL)?", "ALTER TABLE", ["UPDATE", "GRANT", "COMMIT"],
          "DDL defines or changes schema objects (CREATE, ALTER, DROP). UPDATE is DML, GRANT is DCL and COMMIT is TCL."),
        M("ddl-dml-dcl-tcl", "easy", "GRANT and REVOKE are classified as:", "DCL (data control language)", ["DDL", "DML", "TCL"],
          "DCL manages privileges: GRANT gives them and REVOKE removes them."),
        M("ddl-dml-dcl-tcl", "medium", "SAVEPOINT belongs to which group of SQL statements?", "TCL (transaction control language)", ["DDL", "DCL", "DML"],
          "TCL statements (COMMIT, ROLLBACK, SAVEPOINT) control the boundaries of transactions."),
        # sql-commands
        M("sql-commands", "easy", "Which command is intended to remove all rows while keeping the table definition, typically faster than DELETE?", "TRUNCATE TABLE",
          ["DROP TABLE", "ALTER TABLE", "SELECT * FROM"], "TRUNCATE empties a table and keeps its structure. DROP TABLE would remove the table itself. (SQLite has no TRUNCATE; it uses DELETE FROM.)"),
        M("sql-commands", "medium", "DROP TABLE differs from DELETE FROM table in that DROP:", "Removes the table definition as well as its data",
          ["Removes only the selected rows", "Only works on views", "Cannot be used on an empty table"], "DELETE removes rows; DROP TABLE removes the whole object, including its structure."),
        M("sql-commands", "hard", "Which of these is NOT something ALTER TABLE does in standard SQL?", "Change the value stored in one row",
          ["Add a column", "Add a constraint", "Drop a column"], "Changing row values is DML (UPDATE). ALTER TABLE changes the table's structure."),
        # integrity-constraints
        M("integrity-constraints", "easy", "Which constraint stops a column from holding NULL?", "NOT NULL", ["UNIQUE", "CHECK", "DEFAULT"],
          "NOT NULL forbids missing values. UNIQUE forbids duplicates and CHECK tests a condition."),
        M("integrity-constraints", "medium", "A constraint such as CHECK (salary > 0) enforces:", "Domain integrity", ["Referential integrity", "Entity integrity", "Transaction isolation"],
          "Domain integrity restricts a column to valid values."),
        M("integrity-constraints", "medium", "Referential integrity between orders.customer_id and customers.customer_id is enforced by:", "A FOREIGN KEY constraint",
          ["A UNIQUE constraint on orders.order_id", "A NOT NULL constraint on amount", "An index on order_date"], "A foreign key requires each non-NULL value to exist in the referenced key."),
        # keys (design format, machine-checked)
        M("keys", "easy", "What are the candidate keys of R(A,B,C,D) with A->B, B->C, C->D?", "{A}", ["{B}", "{A, B}", "{D}"],
          "A reaches B, C and D transitively, so {A} determines everything and is minimal. No other single attribute reaches A.", fmt="design",
          ref=("candidate_keys", {"attrs": "ABCD", "fds": "A->B, B->C, C->D"}), hints=("Compute the closure of A.",)),
        M("keys", "medium", "Given R(A,B,C,D) with A->B and B->C, is {A, D} a superkey?", "Yes", ["No", "Only if D is unique", "It depends on the data"],
          "closure({A,D}) = {A, B, C, D}, which is every attribute, so it is a superkey (though not minimal if A alone were enough; here D is needed).", fmt="design",
          ref=("is_superkey", {"attrs": "ABCD", "fds": "A->B, B->C", "x": "AD"}), hints=("A superkey's closure is the whole relation.",)),
        S("keys", "medium", "R(A,B,C,D) has the dependencies AB->C and C->D. Give all candidate keys.", "keys", ["AB"],
          "Type each key as letters; separate several keys with commas, e.g. AB, CD.",
          "closure({A,B}) = {A,B,C,D}. Neither A nor B alone determines the rest, so {A,B} is the only candidate key.", ("candidate_keys", {"attrs": "ABCD", "fds": "AB->C, C->D"}),
          hints=("Attributes that never appear on a right-hand side must be in every key.",)),
        M("keys", "easy", "In employee_projects(emp_id, project_id, role, hours) the primary key (emp_id, project_id) is:", "A composite key",
          ["A foreign key only", "A surrogate key", "Not a key because it has two columns"], "A key made of two or more attributes together is a composite key.", fmt="design"),
        M("keys", "medium", "A foreign key must reference:", "A primary key or unique (candidate) key of the parent table",
          ["Any non-key column of the parent", "Only a column in the same table", "Only an indexed text column"], "The parent column(s) must uniquely identify a row, so a primary or unique key is required.", fmt="design"),
        # basic-sql-operations
        Q("basic-sql-operations", "easy", "query",
          "List the name and salary of every employee in the Engineering department (dept_id = 1), highest salary first, then by name A-Z. Employees with no recorded salary must still appear, last.",
          "SELECT name, salary FROM employees WHERE dept_id = 1 ORDER BY salary DESC, name",
          lambda T: [(e["name"], e["salary"]) for e in sorted((e for e in T["employees"] if e["dept_id"] == 1), key=_by_sal_desc_name)],
          "Filter with WHERE, then ORDER BY salary DESC and name. In SQLite NULL sorts as the smallest value, so it comes last in a descending sort.",
          hints=("Filter first with WHERE dept_id = 1.", "ORDER BY accepts several keys, each with its own direction."), ordered=True),
        Q("basic-sql-operations", "easy", "query", "Return each distinct department location exactly once as a single column, alphabetically.",
          "SELECT DISTINCT location FROM departments ORDER BY location",
          lambda T: [(x,) for x in sorted({d["location"] for d in T["departments"]})],
          "DISTINCT removes duplicate output rows; ORDER BY then sorts the remaining values.", hints=("Two departments share a city; DISTINCT collapses them.",), ordered=True),
        Q("basic-sql-operations", "medium", "query", "List the names of employees whose job_title contains the word Manager (any letter case), ordered by name.",
          "SELECT name FROM employees WHERE job_title LIKE '%Manager%' ORDER BY name",
          lambda T: [(e["name"],) for e in sorted(T["employees"], key=lambda e: e["name"]) if "manager" in e["job_title"].lower()],
          "LIKE with % wildcards matches substrings. SQLite's LIKE is case-insensitive for ASCII letters.", hints=("Use LIKE '%word%'.",), ordered=True),
        Q("basic-sql-operations", "medium", "query", "Return name and hire_date for employees hired on or after 2022-01-01, newest hire first; break ties by name.",
          "SELECT name, hire_date FROM employees WHERE hire_date >= '2022-01-01' ORDER BY hire_date DESC, name",
          lambda T: [(e["name"], e["hire_date"]) for e in sorted((e for e in T["employees"] if e["hire_date"] >= "2022-01-01"), key=lambda e: (_neg(e["hire_date"]), e["name"]))],
          "ISO-8601 date strings sort and compare correctly as text, so a plain >= comparison works.", hints=("Dates are stored as YYYY-MM-DD text.",), ordered=True),
        Q("basic-sql-operations", "easy", "query", "Return order_id and order_date of the three earliest orders (by order_date, oldest first).",
          "SELECT order_id, order_date FROM orders ORDER BY order_date LIMIT 3",
          lambda T: [(o["order_id"], o["order_date"]) for o in sorted(T["orders"], key=lambda o: o["order_date"])[:3]],
          "Sort ascending, then keep three rows. LIMIT is supported by SQLite, MySQL and PostgreSQL; standard SQL spells it FETCH FIRST 3 ROWS ONLY.", hints=("Sort first, then limit.",), ordered=True),
        M("basic-sql-operations", "hard", "In which order does a SQL engine logically evaluate these clauses?", "FROM, WHERE, SELECT, ORDER BY",
          ["SELECT, FROM, WHERE, ORDER BY", "WHERE, FROM, ORDER BY, SELECT", "ORDER BY, SELECT, WHERE, FROM"],
          "Logical order: FROM (and joins), WHERE, GROUP BY, HAVING, SELECT, ORDER BY, then LIMIT. That is why a column alias is usable in ORDER BY but not in WHERE."),
        # crud-concepts
        M("crud-concepts", "easy", "What does UPDATE employees SET salary = 0 do when there is no WHERE clause?", "It updates every row in the table",
          ["It updates only the first row", "It is rejected as a syntax error", "It updates only rows where salary is NULL"], "Without WHERE the condition is always true, so all rows are affected."),
        M("crud-concepts", "medium", "Which statement inserts a row while naming the target columns explicitly (the safer form)?",
          "INSERT INTO departments (dept_id, dept_name, location, budget) VALUES (6, 'Research', 'Pune', 100000)",
          ["INSERT departments (dept_id, dept_name) INTO VALUES (6, 'Research')", "ADD ROW departments (6, 'Research', 'Pune', 100000)", "PUT INTO departments VALUES (6, 'Research', 'Pune', 100000)"],
          "INSERT INTO table (columns) VALUES (...) stays correct if columns are later added or reordered."),
        M("crud-concepts", "medium", "DELETE FROM orders WHERE status = 'cancelled' differs from DROP TABLE orders because DELETE:",
          "Removes only matching rows, keeps the table, and can be rolled back inside a transaction",
          ["Removes the table structure too", "Cannot use a WHERE clause", "Is DDL and can never be rolled back in any DBMS"], "DELETE is DML: it removes rows and is transactional; DROP TABLE removes the object itself."),
        O("crud-concepts", "easy", "How many rows does this statement return?", "SELECT * FROM orders WHERE status = 'cancelled'", "count",
          lambda T: str(sum(1 for o in T["orders"] if o["status"] == "cancelled")), ["1", "3", "15"],
          "Orders 1004 and 1013 are cancelled, so two rows match."),
        # null-constraint-violations
        O("null-constraint-violations", "medium", "What does this query return?", "SELECT COUNT(*) FROM employees WHERE salary = NULL", "scalar",
          lambda T: "0", ["1", "15", "16"], "Any comparison with NULL is unknown, never true, so no row qualifies. Use salary IS NULL instead.", hints=("What does NULL = NULL evaluate to?",)),
        O("null-constraint-violations", "medium", "What does this query return? (give COUNT(salary), COUNT(*))", "SELECT COUNT(salary), COUNT(*) FROM employees", "rows",
          lambda T: f"({sum(1 for e in T['employees'] if e['salary'] is not None)}, {len(T['employees'])})", ["(16, 16)", "(15, 15)", "(16, 15)"],
          "COUNT(column) skips NULLs (one employee has no salary); COUNT(*) counts every row."),
        O("null-constraint-violations", "easy", "What does this query return?", "SELECT COUNT(*) FROM employees WHERE salary IS NULL", "scalar",
          lambda T: str(sum(1 for e in T["employees"] if e["salary"] is None)), ["0", "2", "16"], "IS NULL is the correct test for missing values; only the intern has no salary."),
        M("null-constraint-violations", "easy", "Inserting an employee with dept_id = 99 when no such department exists violates:", "Referential integrity (the foreign key)",
          ["Entity integrity", "A domain CHECK on salary", "Atomicity"], "The foreign key requires dept_id to match an existing departments row (or be NULL)."),
        M("null-constraint-violations", "easy", "Inserting a second row with an already-used primary key value violates:", "The primary key (entity integrity) uniqueness rule",
          ["Referential integrity", "A NOT NULL constraint", "Transaction isolation"], "A primary key must be unique and not null for every row."),
        Q("null-constraint-violations", "easy", "query", "Return the names of employees who have no recorded salary, ordered by name.",
          "SELECT name FROM employees WHERE salary IS NULL ORDER BY name",
          lambda T: [(e["name"],) for e in sorted(T["employees"], key=lambda e: e["name"]) if e["salary"] is None],
          "NULL means unknown, so it must be tested with IS NULL; = NULL never matches.", hints=("Which operator tests for NULL?",), ordered=True),
        Q("null-constraint-violations", "medium", "complete", "Complete the query so employees in department 1 show their salary, or 0 when salary is missing, in a column named pay. Order by emp_id; return name and pay.",
          "SELECT name, COALESCE(salary, 0) AS pay FROM employees WHERE dept_id = 1 ORDER BY emp_id",
          lambda T: [(e["name"], e["salary"] or 0) for e in T["employees"] if e["dept_id"] == 1],
          "COALESCE returns its first non-NULL argument, so it supplies a default for missing values.", hints=("COALESCE(x, default) replaces NULL.",),
          starter="SELECT name, ___(salary, 0) AS pay FROM employees WHERE dept_id = 1 ORDER BY emp_id", ordered=True, names=True),
    ]


def _neg(text: str) -> tuple:
    """Sort key that reverses a string ascending sort (for DESC on text)."""
    return tuple(-ord(c) for c in text)
