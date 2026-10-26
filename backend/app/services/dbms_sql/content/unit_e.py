"""Unit E: Database programming constructs. Procedural SQL is vendor-specific, so each such question declares its dialect."""

from __future__ import annotations

from app.services.dbms_sql.content.build import mcq as M, sqlq as Q


def _band(salary):
    if salary is not None and salary >= 90000:
        return "high"
    if salary is not None and salary >= 65000:
        return "mid"
    return "low"


def questions() -> list[dict]:
    return [
        # flow-control
        M("flow-control", "easy", "In Oracle PL/SQL, which keyword introduces an 'else if' branch?", "ELSIF", ["ELSEIF", "ELIF", "ELSE IF"],
          "PL/SQL spells it ELSIF. (MySQL stored programs use ELSEIF; writing ELSE IF would open a nested IF needing its own END IF.)", dialect="oracle"),
        M("flow-control", "medium", "Which construct gives conditional logic inside a SELECT list in standard SQL?", "CASE WHEN ... THEN ... ELSE ... END", ["IF(condition, a, b)", "SWITCH ... CASE", "WHEN ... DO ... END"],
          "CASE is the standard conditional expression. IF() as a function is MySQL-specific."),
        M("flow-control", "medium", "In a MySQL stored program, which form loops while a condition holds?", "WHILE condition DO ... END WHILE", ["WHILE condition { ... }", "LOOP UNTIL condition ... NEXT", "FOR EACH condition ... END"],
          "MySQL uses WHILE ... DO ... END WHILE (also REPEAT ... UNTIL and LOOP ... END LOOP).", dialect="mysql"),
        Q("flow-control", "medium", "complete", "Complete the query so each Engineering employee (dept_id = 1) gets a band: 'high' for salary of at least 90000, 'mid' for at least 65000, otherwise 'low' (NULL salary is 'low'). Return name and band, ordered by emp_id.",
          "SELECT name, CASE WHEN salary >= 90000 THEN 'high' WHEN salary >= 65000 THEN 'mid' ELSE 'low' END AS band FROM employees WHERE dept_id = 1 ORDER BY emp_id",
          lambda T: [(e["name"], _band(e["salary"])) for e in T["employees"] if e["dept_id"] == 1],
          "CASE tests its WHEN branches in order. A NULL salary makes every comparison unknown, so it falls to ELSE.",
          hints=("Branches are checked top to bottom; put the highest threshold first.",),
          starter="SELECT name, CASE WHEN salary >= 90000 THEN 'high' WHEN salary >= 65000 THEN ___ ELSE ___ END AS band FROM employees WHERE dept_id = 1 ORDER BY emp_id", ordered=True, names=True),
        # functions
        M("functions", "easy", "A user-defined function differs from a stored procedure mainly because a function:", "Returns a value and can be used inside SQL expressions", ["Cannot take parameters", "Can never read tables", "Always runs on the client"],
          "Functions are called from expressions (SELECT, WHERE); procedures are invoked as statements (CALL or EXEC)."),
        M("functions", "medium", "UPPER(name) and ROUND(salary, 2) are examples of:", "Scalar functions (one value per input row)", ["Aggregate functions", "Window functions", "Table-valued functions"],
          "Scalar functions return one value per row; aggregates (SUM, COUNT) summarise many rows into one."),
        M("functions", "hard", "In SQL Server, an inline table-valued function returns:", "A result set defined by a single SELECT statement", ["Only one scalar value", "Nothing; it must be a procedure", "A cursor that must be closed"],
          "Inline table-valued functions behave like parameterised views and can be used in FROM.", dialect="sqlserver"),
        # stored-procedures
        M("stored-procedures", "easy", "A main benefit of stored procedures is that they:", "Keep logic on the server, reducing round trips and centralising rules", ["Remove the need for indexes", "Make all queries free", "Replace transactions"],
          "Server-side routines can run several statements in one call and apply consistent logic, subject to the maintenance cost of keeping code in the database."),
        M("stored-procedures", "easy", "In MySQL, which statement runs a stored procedure?", "CALL procedure_name(arguments)", ["EXEC procedure_name", "RUN procedure_name", "SELECT procedure_name()"],
          "MySQL, MariaDB and PostgreSQL 11+ use CALL.", dialect="mysql"),
        M("stored-procedures", "medium", "In SQL Server (T-SQL), which keyword runs a stored procedure?", "EXEC (or EXECUTE)", ["CALL", "INVOKE", "RUN"], "T-SQL uses EXEC/EXECUTE rather than CALL.", dialect="sqlserver"),
        # cursors
        M("cursors", "easy", "A cursor lets procedural code:", "Process the rows of a query result one at a time", ["Delete a table", "Speed up every query", "Create an index"], "A cursor is a pointer over a result set that is advanced row by row."),
        M("cursors", "medium", "The usual cursor life cycle in SQL/PSM style code is:", "DECLARE, OPEN, FETCH (in a loop), CLOSE", ["OPEN, DECLARE, CLOSE, FETCH", "FETCH, OPEN, DECLARE, CLOSE", "DECLARE, CLOSE, FETCH, OPEN"],
          "A cursor is declared, opened to run the query, fetched until no rows remain, and closed to release resources."),
        M("cursors", "hard", "Why are cursors often discouraged when a set-based statement could do the work?", "Row-by-row processing is usually much slower than one set-based statement", ["Cursors cannot read data", "Cursors always lock the entire database", "Set-based SQL cannot filter rows"],
          "The optimizer can process a set-based UPDATE or INSERT...SELECT in bulk; a cursor loop pays per-row overhead."),
        # triggers
        M("triggers", "easy", "Which description best defines a database trigger?", "A routine that runs automatically in response to INSERT, UPDATE or DELETE events", ["A scheduled backup job", "A type of index", "A user login rule only"], "Triggers fire on data-modification events, before or after the change."),
        M("triggers", "medium", "In a MySQL row-level trigger, how do you refer to the value a column is being changed to?", "NEW.column_name", ["INSERTED.column_name", ":NEW.column_name", "AFTER.column_name"],
          "MySQL (and PostgreSQL) use NEW and OLD. Oracle writes :NEW and :OLD; SQL Server uses the inserted and deleted tables.", dialect="mysql"),
        M("triggers", "hard", "In SQL Server DML triggers, the rows affected by the statement are available in special tables named:", "inserted and deleted", ["new and old", "before and after", "added and removed"],
          "SQL Server exposes the new row versions in inserted and the old versions in deleted (an UPDATE fills both).", dialect="sqlserver"),
        # exception-handling
        M("exception-handling", "easy", "In Oracle PL/SQL, which block section handles run-time errors?", "The EXCEPTION section", ["The DECLARE section", "The COMMIT section", "The ERROR section"],
          "A PL/SQL block has DECLARE, BEGIN and EXCEPTION sections; WHEN handlers sit in EXCEPTION.", dialect="oracle"),
        M("exception-handling", "medium", "Which pair of statements does SQL Server T-SQL use for structured error handling?", "BEGIN TRY ... END TRY and BEGIN CATCH ... END CATCH", ["TRY ... EXCEPT", "ON ERROR GOTO", "DECLARE HANDLER ... FOR"],
          "T-SQL has TRY...CATCH. (MySQL declares condition handlers instead.)", dialect="sqlserver"),
        M("exception-handling", "medium", "In PL/pgSQL, how do you catch an error inside a function?", "Add an EXCEPTION WHEN ... THEN clause to the BEGIN block", ["Wrap the statement in TRY ... CATCH", "Set ON ERROR CONTINUE", "Call a built-in ERROR() function"],
          "PL/pgSQL attaches an EXCEPTION section to a BEGIN ... END block; entering it rolls back that block's changes.", dialect="postgresql"),
        # dialect-differences
        M("dialect-differences", "medium", "Which spelling of 'return only the first n rows' is defined by the ISO SQL standard?", "FETCH FIRST n ROWS ONLY", ["LIMIT n", "TOP n", "ROWNUM <= n"],
          "LIMIT (PostgreSQL, MySQL, SQLite), TOP (SQL Server) and ROWNUM (classic Oracle) are vendor forms; FETCH FIRST is standard."),
        M("dialect-differences", "easy", "Which operator concatenates strings in standard SQL?", "||", ["+", "&", "CONCAT only"], "Standard SQL uses ||. SQL Server uses +, and MySQL treats || as OR unless PIPES_AS_CONCAT is set."),
        M("dialect-differences", "medium", "In MySQL, an auto-numbering primary key is declared with:", "AUTO_INCREMENT", ["SERIAL only", "IDENTITY(1,1) only", "NEXTVAL only"],
          "MySQL uses AUTO_INCREMENT; PostgreSQL uses GENERATED ... AS IDENTITY (or SERIAL); SQL Server uses IDENTITY; Oracle uses identity columns or sequences.", dialect="mysql"),
        M("dialect-differences", "hard", "When ORDER BY sorts a column that contains NULLs, SQLite:", "Treats NULL as smaller than every other value, so it sorts first ascending and last descending",
          ["Always rejects the query", "Always puts NULLs last", "Removes the NULL rows"], "Standard SQL leaves NULL placement implementation-defined (NULLS FIRST/LAST can state it); products differ.", dialect="sqlite"),
    ]
