"""Unit C: Relational operations and advanced SQL. SQL exercises, output prediction and plan questions are engine- and oracle-checked."""

from __future__ import annotations

from collections import defaultdict

from app.services.dbms_sql.content.build import mcq as M, outq as O, planq as P, sqlq as Q

WF = ("window_functions",)


def _avg(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _dept_avgs(T):
    groups = defaultdict(list)
    for e in T["employees"]:
        if e["dept_id"] is not None:
            groups[e["dept_id"]].append(e["salary"])
    return {d: _avg(v) for d, v in groups.items()}


def _customer_totals(T, skip_cancelled=True):
    totals = defaultdict(float)
    for o in T["orders"]:
        if o["amount"] is None or (skip_cancelled and o["status"] == "cancelled"):
            continue
        totals[o["customer_id"]] += o["amount"]
    return totals


def _rank(values_desc, value):
    return 1 + sum(1 for v in values_desc if v > value)


def questions() -> list[dict]:
    return [
        # aggregate-functions
        Q("aggregate-functions", "easy", "query",
          "In ONE row, return the number of employees as headcount, the average salary rounded to 2 decimals as avg_salary, and the highest salary as max_salary (all employees).",
          "SELECT COUNT(*) AS headcount, ROUND(AVG(salary), 2) AS avg_salary, MAX(salary) AS max_salary FROM employees",
          lambda T: [(len(T["employees"]), round(_avg([e["salary"] for e in T["employees"]]), 2), max(e["salary"] for e in T["employees"] if e["salary"] is not None))],
          "COUNT(*) counts rows; AVG and MAX ignore NULL salaries. ROUND(x, 2) limits the decimals.", hints=("Aggregates without GROUP BY return a single row.",), names=True),
        Q("aggregate-functions", "medium", "query", "Return the total amount of all delivered orders as a single column named delivered_total.",
          "SELECT SUM(amount) AS delivered_total FROM orders WHERE status = 'delivered'",
          lambda T: [(sum(o["amount"] for o in T["orders"] if o["status"] == "delivered" and o["amount"] is not None),)],
          "WHERE filters rows before SUM aggregates them.", hints=("Filter on status before aggregating.",), names=True),
        O("aggregate-functions", "medium", "What does this query return?", "SELECT AVG(salary) FROM employees WHERE dept_id = 2", "scalar",
          lambda T: f"{_avg([e['salary'] for e in T['employees'] if e['dept_id'] == 2]):.4f}".rstrip("0").rstrip("."), ["72000", "65000", "80000"],
          "The five Sales salaries are 110000, 65000, 65000, 80000 and 72000, which sum to 392000; 392000 / 5 = 78400."),
        M("aggregate-functions", "easy", "Which expression counts ALL rows of employees, including rows where salary is NULL?", "COUNT(*)", ["COUNT(salary)", "SUM(salary)", "AVG(salary)"],
          "COUNT(*) counts rows. COUNT(column) counts only non-NULL values; SUM and AVG also skip NULLs."),
        O("aggregate-functions", "hard", "What does this query return?", "SELECT COUNT(DISTINCT dept_id) FROM employees", "scalar",
          lambda T: str(len({e["dept_id"] for e in T["employees"] if e["dept_id"] is not None})), ["5", "16", "6"],
          "DISTINCT ignores NULL in COUNT(DISTINCT col): departments 1, 2, 3 and 4 are used, so the answer is 4 (Manoj's NULL is not counted)."),
        # group-by-having
        Q("group-by-having", "easy", "query", "For employees that belong to a department, return dept_id and the number of employees in it as headcount, ordered by dept_id.",
          "SELECT dept_id, COUNT(*) AS headcount FROM employees WHERE dept_id IS NOT NULL GROUP BY dept_id ORDER BY dept_id",
          lambda T: sorted(((d, sum(1 for e in T["employees"] if e["dept_id"] == d)) for d in {e["dept_id"] for e in T["employees"] if e["dept_id"] is not None})),
          "GROUP BY forms one group per department. Without the WHERE filter the employee with no department would form a NULL group.",
          hints=("Exclude NULL dept_id before grouping.",), ordered=True, names=True),
        Q("group-by-having", "medium", "query", "Return dept_id and the average salary rounded to 2 decimals as avg_salary, only for departments whose average salary is above 75000, ordered by dept_id.",
          "SELECT dept_id, ROUND(AVG(salary), 2) AS avg_salary FROM employees WHERE dept_id IS NOT NULL GROUP BY dept_id HAVING AVG(salary) > 75000 ORDER BY dept_id",
          lambda T: [(d, round(a, 2)) for d, a in sorted(_dept_avgs(T).items()) if a is not None and a > 75000],
          "HAVING filters groups after aggregation, which WHERE cannot do.", hints=("A condition on an aggregate belongs in HAVING.",), ordered=True, names=True),
        Q("group-by-having", "hard", "query",
          "For non-cancelled orders, return customer_id and the sum of amount as total for customers whose total exceeds 500, largest total first.",
          "SELECT customer_id, SUM(amount) AS total FROM orders WHERE status <> 'cancelled' GROUP BY customer_id HAVING SUM(amount) > 500 ORDER BY total DESC",
          lambda T: sorted([(c, t) for c, t in _customer_totals(T).items() if t > 500], key=lambda r: -r[1]),
          "Filter rows with WHERE (cancelled orders), group per customer, then filter groups with HAVING. SUM ignores the NULL amount.", hints=("WHERE removes rows; HAVING removes groups.",), ordered=True, names=True),
        M("group-by-having", "easy", "Which clause can filter on an aggregate such as COUNT(*) > 3?", "HAVING", ["WHERE", "ORDER BY", "FROM"],
          "WHERE runs before grouping and cannot see aggregates; HAVING runs after."),
        M("group-by-having", "medium", "According to standard SQL (and PostgreSQL), a query selects dept_id and salary but groups only by dept_id. This is:",
          "An error, because salary is neither grouped nor aggregated", ["Valid and returns the average salary", "Valid and returns the first row of each group", "Valid only when ORDER BY is present"],
          "Every selected column must be grouped or aggregated. (SQLite and old MySQL modes silently allow it, which is a dialect leniency.)"),
        O("group-by-having", "medium", "What does this query return?", "SELECT dept_id, COUNT(*) FROM employees GROUP BY dept_id HAVING COUNT(*) > 4 ORDER BY dept_id", "rows",
          lambda T: "; ".join(f"({d}, {n})" for d, n in sorted((d, sum(1 for e in T["employees"] if e["dept_id"] == d)) for d in {e["dept_id"] for e in T["employees"] if e["dept_id"] is not None}) if n > 4),
          ["(1, 5); (2, 5)", "(1, 6)", "(2, 5); (3, 2)"], "COUNT(*) counts the intern too, so Engineering has 6 and Sales has 5; HR (2) and Marketing (2) are filtered out."),
        # joins
        Q("joins", "easy", "query", "Return each employee's name and their department's name (as dept_name) for employees that have a department, ordered by name.",
          "SELECT e.name, d.dept_name FROM employees e JOIN departments d ON e.dept_id = d.dept_id ORDER BY e.name",
          lambda T: sorted(((e["name"], d["dept_name"]) for e in T["employees"] for d in T["departments"] if e["dept_id"] == d["dept_id"])),
          "An INNER JOIN keeps only rows with a match on both sides, so the employee with no department is dropped.", hints=("Join on dept_id.",), ordered=True, names=True),
        Q("joins", "medium", "query", "List every department with its number of employees as headcount, including departments with none (they must show 0). Return dept_name, headcount ordered by dept_name.",
          "SELECT d.dept_name, COUNT(e.emp_id) AS headcount FROM departments d LEFT JOIN employees e ON e.dept_id = d.dept_id GROUP BY d.dept_id, d.dept_name ORDER BY d.dept_name",
          lambda T: sorted((d["dept_name"], sum(1 for e in T["employees"] if e["dept_id"] == d["dept_id"])) for d in T["departments"]),
          "A LEFT JOIN keeps every department. COUNT(e.emp_id) counts only matched employees, so Legal gets 0 (COUNT(*) would wrongly give 1).",
          hints=("Which table must keep all of its rows?", "Count a column from the optional side, not *."), ordered=True, names=True),
        Q("joins", "medium", "query", "Return the names of customers who have never placed an order, ordered by name.",
          "SELECT c.customer_name FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE o.order_id IS NULL ORDER BY c.customer_name",
          lambda T: sorted((c["customer_name"],) for c in T["customers"] if not any(o["customer_id"] == c["customer_id"] for o in T["orders"])),
          "A LEFT JOIN plus WHERE right-key IS NULL is the classic anti-join: it keeps only rows with no match.", hints=("After a LEFT JOIN, unmatched rows have NULL on the right side.",), ordered=True),
        Q("joins", "medium", "query", "Return each employee that has a manager as two columns: employee (their name) and manager (the manager's name), ordered by employee.",
          "SELECT e.name AS employee, m.name AS manager FROM employees e JOIN employees m ON e.manager_id = m.emp_id ORDER BY e.name",
          lambda T: sorted((e["name"], m["name"]) for e in T["employees"] for m in T["employees"] if e["manager_id"] == m["emp_id"]),
          "A self-join uses the same table twice under different aliases to relate a row to another row of itself.", hints=("Join employees to employees.",), ordered=True, names=True),
        Q("joins", "hard", "query", "For every project return project_name and the total hours logged on it as total_hours (0 when nobody is assigned), ordered by project_name.",
          "SELECT p.project_name, COALESCE(SUM(ep.hours), 0) AS total_hours FROM projects p LEFT JOIN employee_projects ep ON ep.project_id = p.project_id GROUP BY p.project_id, p.project_name ORDER BY p.project_name",
          lambda T: sorted((p["project_name"], sum(ep["hours"] for ep in T["employee_projects"] if ep["project_id"] == p["project_id"])) for p in T["projects"]),
          "LEFT JOIN keeps the unassigned project, SUM over no rows is NULL, and COALESCE turns it into 0.", hints=("SUM of nothing is NULL.",), ordered=True, names=True),
        M("joins", "easy", "Which join returns all rows of the left table plus matching rows of the right, with NULLs where there is no match?", "LEFT OUTER JOIN",
          ["INNER JOIN", "CROSS JOIN", "NATURAL JOIN"], "LEFT OUTER JOIN preserves every left row; INNER JOIN would drop unmatched ones."),
        M("joins", "medium", "A FULL OUTER JOIN of tables A and B returns:", "Matching rows plus unmatched rows from both tables, padded with NULLs",
          ["Only matching rows", "Only the unmatched rows of A", "The Cartesian product of A and B"],
          "FULL = LEFT plus RIGHT. In SQLite it is available from version 3.39; older versions need LEFT JOIN UNION ALL the unmatched right rows."),
        M("joins", "easy", "Table A has 4 rows and table B has 5 rows. How many rows does A CROSS JOIN B return?", "20", ["9", "5", "4"],
          "A cross join pairs every row of A with every row of B: 4 x 5 = 20.", ref=("arithmetic", {"value": 20})),
        O("joins", "medium", "How many rows does this query return?", "SELECT COUNT(*) FROM employees e JOIN departments d ON e.dept_id = d.dept_id", "scalar",
          lambda T: str(sum(1 for e in T["employees"] if any(d["dept_id"] == e["dept_id"] for d in T["departments"]))), ["16", "14", "5"],
          "Manoj has a NULL dept_id, which matches nothing, so the inner join returns 15 of the 16 employees."),
        # set-operators
        Q("set-operators", "medium", "query", "Return one column named city listing every distinct city that appears in customers.city or departments.location (ignore NULL), alphabetically.",
          "SELECT city FROM customers WHERE city IS NOT NULL UNION SELECT location FROM departments ORDER BY 1",
          lambda T: [(c,) for c in sorted({c["city"] for c in T["customers"] if c["city"]} | {d["location"] for d in T["departments"]})],
          "UNION combines two queries and removes duplicates. The output column takes the name of the first query.", hints=("UNION removes duplicates.",), ordered=True, names=True),
        Q("set-operators", "medium", "query", "Using a set operator, return the customer_id of customers that have no orders, ordered by customer_id.",
          "SELECT customer_id FROM customers EXCEPT SELECT customer_id FROM orders ORDER BY customer_id",
          lambda T: [(c["customer_id"],) for c in sorted(T["customers"], key=lambda c: c["customer_id"]) if not any(o["customer_id"] == c["customer_id"] for o in T["orders"])],
          "EXCEPT returns rows of the first query that are absent from the second.", hints=("Which operator subtracts one result from another?",), ordered=True),
        Q("set-operators", "medium", "query", "Return, as one column dept_id, the department ids that appear in BOTH employees and projects, ordered ascending.",
          "SELECT dept_id FROM employees INTERSECT SELECT dept_id FROM projects ORDER BY dept_id",
          lambda T: [(d,) for d in sorted({e["dept_id"] for e in T["employees"] if e["dept_id"] is not None} & {p["dept_id"] for p in T["projects"]})],
          "INTERSECT keeps only rows present in both results (duplicates removed).", hints=("Think of set intersection.",), ordered=True, names=True),
        M("set-operators", "easy", "How do UNION and UNION ALL differ?", "UNION removes duplicate rows; UNION ALL keeps them", ["UNION ALL removes duplicates; UNION keeps them", "UNION needs a JOIN condition", "UNION ALL sorts the result"],
          "UNION must deduplicate (extra work); UNION ALL simply concatenates and is usually faster."),
        O("set-operators", "hard", "How many rows does this query return?", "SELECT COUNT(*) FROM (SELECT dept_id FROM employees UNION SELECT dept_id FROM projects)", "scalar",
          lambda T: str(len({e["dept_id"] for e in T["employees"]} | {p["dept_id"] for p in T["projects"]})), ["4", "21", "16"],
          "The distinct values are 1, 2, 3, 4 and NULL. Set operators treat NULLs as equal, so there is exactly one NULL row: 5 rows."),
        # views
        M("views", "easy", "A regular (non-materialized) view stores:", "A saved query definition that runs when the view is used",
          ["A physical copy of the result refreshed hourly", "Only the first hundred rows", "An index on the base tables"], "A view is a named query; its rows are computed from the base tables each time."),
        M("views", "medium", "Which is a common reason to create a view?", "To expose only selected columns or rows to certain users", ["To speed up every INSERT", "To replace primary keys", "To disable transactions"],
          "Views simplify complex queries and restrict what users can see, without copying data."),
        M("views", "hard", "A materialized view differs from a regular view because it:", "Stores the query result physically and has to be refreshed", ["Never reads the base tables", "Cannot be indexed", "Is always updated instantly by every base-table write"],
          "Materialized views trade freshness for speed. They exist in PostgreSQL and Oracle; MySQL and SQLite have no native materialized views.", dialect="postgresql"),
        Q("views", "medium", "query", "A view named high_paid would hold employees with salary of at least 90000. Emulate it with a WITH clause named high_paid and return its name column ordered by name.",
          "WITH high_paid AS (SELECT name, salary FROM employees WHERE salary >= 90000) SELECT name FROM high_paid ORDER BY name",
          lambda T: [(e["name"],) for e in sorted(T["employees"], key=lambda e: e["name"]) if e["salary"] is not None and e["salary"] >= 90000],
          "A common table expression is a query-scoped named subquery, behaving like a temporary view.", hints=("WITH name AS (SELECT ...) SELECT ... FROM name",), ordered=True),
        # subqueries
        Q("subqueries", "medium", "query", "Return name and salary of employees who earn more than the company-wide average salary, highest salary first, then name.",
          "SELECT name, salary FROM employees WHERE salary > (SELECT AVG(salary) FROM employees) ORDER BY salary DESC, name",
          lambda T: [(e["name"], e["salary"]) for e in sorted((e for e in T["employees"] if e["salary"] is not None and e["salary"] > _avg([x["salary"] for x in T["employees"]])), key=lambda e: (-e["salary"], e["name"]))],
          "A scalar subquery returns one value that the outer WHERE compares against.", hints=("Compute AVG(salary) in a parenthesised subquery.",), ordered=True),
        Q("subqueries", "medium", "query", "Return the names (ordered) of employees who work on the project named Apollo, using subqueries rather than joins.",
          "SELECT name FROM employees WHERE emp_id IN (SELECT emp_id FROM employee_projects WHERE project_id = (SELECT project_id FROM projects WHERE project_name = 'Apollo')) ORDER BY name",
          lambda T: [(e["name"],) for e in sorted(T["employees"], key=lambda e: e["name"]) if any(ep["emp_id"] == e["emp_id"] and ep["project_id"] == 101 for ep in T["employee_projects"])],
          "Nested IN subqueries let you filter by membership in a derived set.", hints=("First find the project_id, then the employees on it.",), ordered=True),
        Q("subqueries", "hard", "query", "Using a correlated subquery, return name and dept_id of employees who earn more than the average salary of their OWN department, ordered by name.",
          "SELECT name, dept_id FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE dept_id = e.dept_id) ORDER BY name",
          lambda T: [(e["name"], e["dept_id"]) for e in sorted(T["employees"], key=lambda e: e["name"]) if e["dept_id"] is not None and e["salary"] is not None and e["salary"] > _dept_avgs(T)[e["dept_id"]]],
          "The inner query references e.dept_id from the outer row, so it is re-evaluated per employee. The employee with no department never qualifies because the comparison is NULL.",
          hints=("The inner query needs the outer row's dept_id.",), ordered=True),
        Q("subqueries", "medium", "query", "Return the names of departments that have no employees, using NOT EXISTS.",
          "SELECT dept_name FROM departments d WHERE NOT EXISTS (SELECT 1 FROM employees e WHERE e.dept_id = d.dept_id)",
          lambda T: [(d["dept_name"],) for d in T["departments"] if not any(e["dept_id"] == d["dept_id"] for e in T["employees"])],
          "NOT EXISTS is true when the correlated subquery returns no row. It is NULL-safe, unlike NOT IN.", hints=("Correlate on dept_id.",)),
        M("subqueries", "easy", "Which kind of subquery refers to a column of the outer query and is logically re-evaluated for each outer row?", "A correlated subquery",
          ["A scalar constant subquery", "A derived table in FROM", "A UNION subquery"], "Correlation means the inner query depends on the current outer row."),
        M("subqueries", "hard", "Why can x NOT IN (SELECT col ...) return no rows at all when the subquery result contains a NULL?", "Comparing with NULL is unknown, so the NOT IN condition can never be true",
          ["NULL is treated as zero in NOT IN", "SQL rejects such queries", "NOT IN always skips the first row"], "x <> NULL is unknown; with a NULL in the list the whole NOT IN is unknown or false for every x. Use NOT EXISTS or filter the NULLs out."),
        O("subqueries", "hard", "What does this query return?", "SELECT COUNT(*) FROM employees WHERE dept_id NOT IN (SELECT dept_id FROM employees WHERE emp_id = 13)", "scalar",
          lambda T: "0", ["15", "16", "1"], "Employee 13 has a NULL dept_id, so the subquery yields {NULL}. dept_id NOT IN (NULL) is never true, so no rows qualify."),
        # relational-algebra
        M("relational-algebra", "easy", "Which relational algebra operator selects the ROWS that satisfy a condition?", "Selection (sigma)", ["Projection (pi)", "Natural join", "Rename (rho)"],
          "Selection filters tuples; projection chooses attributes."),
        M("relational-algebra", "medium", "Which SQL is equivalent to pi_name,salary( sigma_salary>90000 (Employees) ) under set semantics?", "SELECT DISTINCT name, salary FROM employees WHERE salary > 90000",
          ["SELECT * FROM employees WHERE salary > 90000", "SELECT name FROM employees WHERE salary > 90000", "SELECT name, salary FROM employees HAVING salary > 90000"],
          "Selection becomes WHERE, projection picks the columns, and relational algebra returns a set, hence DISTINCT."),
        M("relational-algebra", "medium", "Which of these is a derived (not primitive) relational algebra operator?", "Natural join", ["Selection", "Projection", "Set difference"],
          "The primitives are selection, projection, union, set difference, Cartesian product and rename; joins can be expressed with them."),
        M("relational-algebra", "medium", "R has degree 3 and 4 tuples; S has degree 2 and 5 tuples. The Cartesian product R x S has:", "Degree 5 and 20 tuples", ["Degree 6 and 9 tuples", "Degree 5 and 9 tuples", "Degree 6 and 20 tuples"],
          "Degrees add (3 + 2) and cardinalities multiply (4 x 5)."),
        O("relational-algebra", "hard", "pi_salary(Employees) as a set, ignoring NULL: how many tuples does this SQL return?", "SELECT COUNT(*) FROM (SELECT DISTINCT salary FROM employees WHERE salary IS NOT NULL)", "scalar",
          lambda T: str(len({e["salary"] for e in T["employees"] if e["salary"] is not None})), ["15", "16", "10"], "Projection removes duplicate tuples: 15 non-NULL salaries collapse to 12 distinct values."),
        # window-functions
        Q("window-functions", "medium", "query", "For orders of customer 1, return order_id, amount and a cumulative running_total of amount in order_id order. Order the output by order_id.",
          "SELECT order_id, amount, SUM(amount) OVER (ORDER BY order_id) AS running_total FROM orders WHERE customer_id = 1 ORDER BY order_id",
          lambda T: _running(T), "SUM(...) OVER (ORDER BY ...) accumulates over the default frame, keeping every row.", hints=("Use SUM as a window function with OVER (ORDER BY ...).",), requires=WF, ordered=True, names=True),
        Q("window-functions", "medium", "query", "For customer 1's orders, return order_id, amount and prev_amount: the amount of the same customer's previous order by order_id (NULL for the first). Order by order_id.",
          "SELECT order_id, amount, LAG(amount) OVER (ORDER BY order_id) AS prev_amount FROM orders WHERE customer_id = 1 ORDER BY order_id",
          lambda T: [(o["order_id"], o["amount"], p) for o, p in zip(*_cust1(T))], "LAG looks back a row inside the window; the first row has no predecessor so it is NULL.", hints=("LAG(col) OVER (ORDER BY ...)",), requires=WF, ordered=True, names=True),
        Q("window-functions", "hard", "query", "For employees that have BOTH a department and a salary, return name, salary and dept_avg (the average salary of their department, rounded to 2 decimals), ordered by emp_id.",
          "SELECT name, salary, ROUND(AVG(salary) OVER (PARTITION BY dept_id), 2) AS dept_avg FROM employees WHERE dept_id IS NOT NULL AND salary IS NOT NULL ORDER BY emp_id",
          lambda T: _with_dept_avg(T), "AVG(...) OVER (PARTITION BY dept_id) adds the group average to every row without collapsing rows. The WHERE filter is applied before the window is computed.",
          hints=("PARTITION BY plays the role GROUP BY plays for ordinary aggregates.",), requires=WF, ordered=True, names=True),
        M("window-functions", "easy", "What distinguishes a window function from GROUP BY aggregation?", "It computes over related rows but keeps every input row in the output",
          ["It can only be used with INNER JOIN", "It removes duplicate rows", "It must be used with HAVING"], "GROUP BY collapses each group to one row; a window function annotates each row with a value computed over its window.", requires=WF),
        M("window-functions", "hard", "For SUM(x) OVER (ORDER BY d) with no explicit frame, the default frame is:", "RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW",
          ["The whole partition always", "Only the current row", "ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING"], "With ORDER BY and no frame clause the frame runs from the partition start to the current row (peers included), which gives running totals.", requires=WF),
        O("window-functions", "hard", "What does this query return?", "SELECT ROW_NUMBER() OVER (ORDER BY salary DESC, name) FROM employees WHERE name = 'Bilal'", "scalar",
          lambda T: "1", ["2", "5", "16"], "WHERE runs before window functions, so only Bilal's row is in the window and its row number is 1.", requires=WF),
        # ranking-partitioning
        Q("ranking-partitioning", "medium", "query", "For Engineering employees (dept_id = 1) with a salary, return name, dept_id and salary_rank using RANK() by salary descending within the department. Order by salary_rank, then name.",
          "SELECT name, dept_id, RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS salary_rank FROM employees WHERE dept_id = 1 AND salary IS NOT NULL ORDER BY salary_rank, name",
          lambda T: _rank_dept1(T), "RANK gives ties the same number and leaves gaps: two people tied for 2nd are followed by rank 4.", hints=("Ties share a rank with RANK().",), requires=WF, ordered=True, names=True),
        Q("ranking-partitioning", "hard", "query", "Return name and salary of employees whose salary is among the top 3 DISTINCT salaries (use DENSE_RANK), ordered by salary descending then name.",
          "WITH r AS (SELECT name, salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS rnk FROM employees WHERE salary IS NOT NULL) SELECT name, salary FROM r WHERE rnk <= 3 ORDER BY salary DESC, name",
          lambda T: _top3_distinct(T), "DENSE_RANK has no gaps, so rnk <= 3 keeps everyone holding one of the three highest distinct salaries, including ties. Window results cannot be filtered in WHERE directly, hence the CTE.",
          hints=("A window function cannot appear in WHERE; wrap it in a CTE.",), requires=WF, ordered=True),
        Q("ranking-partitioning", "hard", "query", "Return the highest-paid employee of each department (ties broken by name, employees without a department or salary excluded): dept_id, name, ordered by dept_id.",
          "WITH r AS (SELECT dept_id, name, ROW_NUMBER() OVER (PARTITION BY dept_id ORDER BY salary DESC, name) AS rn FROM employees WHERE dept_id IS NOT NULL AND salary IS NOT NULL) SELECT dept_id, name FROM r WHERE rn = 1 ORDER BY dept_id",
          lambda T: _top_per_dept(T), "ROW_NUMBER gives a unique ordering per partition, so rn = 1 picks exactly one row per department (the classic top-N-per-group pattern).",
          hints=("ROW_NUMBER with a deterministic tie-breaker gives exactly one winner.",), requires=WF, ordered=True),
        M("ranking-partitioning", "medium", "Two employees tie for 2nd highest salary. The next lower salary gets RANK() 4 and DENSE_RANK() of:", "3", ["4", "2", "5"],
          "RANK skips numbers after ties (1, 2, 2, 4). DENSE_RANK does not (1, 2, 2, 3).", requires=WF),
        M("ranking-partitioning", "easy", "What does PARTITION BY do in a window function?", "Splits rows into independent groups for the calculation without collapsing them",
          ["Sorts the final output", "Removes duplicate rows", "Joins the table to itself"], "Each partition is processed separately, but all rows are still returned.", requires=WF),
        # hashing-indexing
        M("hashing-indexing", "medium", "A hash table has 7 slots, h(k) = k mod 7 and linear probing. After inserting 15, 22, 8, 29 in that order, which slot holds 29?", "4", ["1", "2", "3"],
          "15 goes to slot 1; 22 collides and takes 2; 8 collides at 1 and 2 and takes 3; 29 collides at 1, 2 and 3 and takes 4.",
          ref=("hash_slot", {"size": 7, "keys": [15, 22, 8, 29], "probe": "linear", "key": 29}), hints=("Probe slot h, h+1, h+2... until one is empty.",)),
        M("hashing-indexing", "medium", "With separate chaining, h(k) = k mod 5 and keys 12, 17, 22 and 7, which bucket do all four keys share?", "bucket 2", ["bucket 0", "bucket 1", "bucket 3"],
          "Each key mod 5 equals 2, so all four are chained in bucket 2.", ref=("hash_slot", {"size": 5, "keys": [12, 17, 22, 7], "probe": "chain", "key": 12})),
        M("hashing-indexing", "medium", "Why does a B+-tree index support range queries better than a hash index?", "Its leaves keep keys in sorted, linked order, so a range is a sequential scan",
          ["Hash indexes cannot store integers", "B+-trees avoid disk I/O entirely", "Hash indexes keep keys sorted automatically"], "Hashing scatters keys, so only equality lookups are efficient; B+-tree leaves are ordered."),
        M("hashing-indexing", "easy", "Which predicate can an equality-only hash index accelerate?", "WHERE emp_id = 7", ["WHERE salary > 90000", "ORDER BY name", "WHERE name LIKE 'A%'"],
          "Hash indexes answer exact-match lookups; ranges, ordering and prefixes need an ordered index."),
        M("hashing-indexing", "easy", "Adding an index to a table usually makes writes:", "Slower, because the index must be kept up to date", ["Faster", "Unaffected", "Impossible"],
          "Indexes speed reads but cost extra work and space on INSERT, UPDATE and DELETE."),
        # query-optimization
        M("query-optimization", "medium", "Which rewrite is a classic heuristic optimisation?", "Push selections (filters) down so they run before joins", ["Perform joins before any filtering", "Avoid indexes where possible", "Sort every table first"],
          "Filtering early reduces the rows entering joins, which is usually far cheaper."),
        M("query-optimization", "medium", "Why is SELECT * often discouraged in production queries?", "It reads unneeded columns, can prevent covering-index use and breaks when columns change",
          ["It is a syntax error in most systems", "It always disables indexes", "It locks the whole database"], "Selecting only needed columns reduces I/O and keeps queries stable."),
        M("query-optimization", "hard", "A predicate such as WHERE UPPER(name) = 'ASHA' is usually non-sargable on an ordinary index of name because:", "The function must be applied to every row, so the index order on name cannot be used",
          ["UPPER is not allowed in WHERE", "Indexes only work on numbers", "The optimizer ignores all string columns"], "Wrapping an indexed column in a function hides its order from the index; use an expression index or compare the bare column."),
        M("query-optimization", "medium", "A cost-based optimizer chooses between candidate plans mainly using:", "Statistics about table sizes and value distributions", ["The order of columns in SELECT", "Alphabetical table names", "The login name of the user"],
          "Cardinality and selectivity estimates drive the cost model."),
        # execution-plans
        P("execution-plans", "easy", "Which access method does SQLite report for this query?", "SELECT * FROM employees WHERE emp_id = 7", "Primary key lookup",
          ["Index search", "Covering index search", "Full table scan"], "emp_id is the INTEGER PRIMARY KEY (the rowid), so SQLite does a direct rowid search.", hints=("Use EXPLAIN QUERY PLAN in the editor to see the plan.",)),
        P("execution-plans", "medium", "Which access method does SQLite report for this query?", "SELECT * FROM employees WHERE dept_id = 2", "Index search",
          ["Primary key lookup", "Covering index search", "Full table scan"], "idx_employees_dept covers dept_id; the query needs other columns too, so it is an index search followed by row lookups."),
        P("execution-plans", "medium", "Which access method does SQLite report for this query?", "SELECT * FROM employees WHERE salary > 90000", "Full table scan",
          ["Primary key lookup", "Index search", "Covering index search"], "There is no index on salary, so every row must be examined."),
        P("execution-plans", "hard", "Which access method does SQLite report for this query?", "SELECT * FROM employees WHERE dept_id + 0 = 2", "Full table scan",
          ["Primary key lookup", "Index search", "Covering index search"], "Applying arithmetic to the indexed column hides it from the index, so the plan falls back to a scan."),
        P("execution-plans", "hard", "Which access method does SQLite report for this query?", "SELECT customer_id, amount FROM orders WHERE customer_id = 1", "Covering index search",
          ["Primary key lookup", "Index search", "Full table scan"], "idx_orders_customer_amount contains both customer_id and amount, so the table itself is never read."),
        M("execution-plans", "medium", "When reading an execution plan for a large table, what is usually the warning sign?", "A full table scan where an indexed lookup was expected", ["An index search on the primary key", "A covering index", "A plan with one step"],
          "A scan reads every row. Check the predicate, the available indexes and whether a function or type conversion hides the index."),
    ]


def _cust1(T):
    rows = sorted((o for o in T["orders"] if o["customer_id"] == 1), key=lambda o: o["order_id"])
    prev = [None] + [o["amount"] for o in rows[:-1]]
    return rows, prev


def _running(T):
    rows, total = sorted((o for o in T["orders"] if o["customer_id"] == 1), key=lambda o: o["order_id"]), 0.0
    out = []
    for o in rows:
        total += o["amount"]
        out.append((o["order_id"], o["amount"], total))
    return out


def _with_dept_avg(T):
    emps = [e for e in T["employees"] if e["dept_id"] is not None and e["salary"] is not None]
    avgs = defaultdict(list)
    for e in emps:
        avgs[e["dept_id"]].append(e["salary"])
    return [(e["name"], e["salary"], round(sum(avgs[e["dept_id"]]) / len(avgs[e["dept_id"]]), 2)) for e in sorted(emps, key=lambda e: e["emp_id"])]


def _rank_dept1(T):
    emps = [e for e in T["employees"] if e["dept_id"] == 1 and e["salary"] is not None]
    sal = [e["salary"] for e in emps]
    return sorted(((e["name"], 1, _rank(sal, e["salary"])) for e in emps), key=lambda r: (r[2], r[0]))


def _top3_distinct(T):
    emps = [e for e in T["employees"] if e["salary"] is not None]
    top = sorted({e["salary"] for e in emps}, reverse=True)[:3]
    return sorted(((e["name"], e["salary"]) for e in emps if e["salary"] in top), key=lambda r: (-r[1], r[0]))


def _top_per_dept(T):
    best: dict[int, tuple] = {}
    for e in T["employees"]:
        if e["dept_id"] is None or e["salary"] is None:
            continue
        cand = (-e["salary"], e["name"])
        if e["dept_id"] not in best or cand < best[e["dept_id"]][0]:
            best[e["dept_id"]] = (cand, e["name"])
    return [(d, best[d][1]) for d in sorted(best)]
