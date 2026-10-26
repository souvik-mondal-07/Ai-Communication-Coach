"""Debug-the-query and complete-the-query exercises. Every broken starter is checked to really fail or give a wrong result."""

from __future__ import annotations

from app.services.dbms_sql.content.build import mcq as M, sqlq as Q

WF = ("window_functions",)


def questions() -> list[dict]:
    return [
        # ---- debug: syntax and logic errors ----
        Q("basic-sql-operations", "easy", "debug", "This query should return the name and salary of Engineering employees (dept_id = 1) ordered by name, but it returns only one column. Fix it.",
          "SELECT name, salary FROM employees WHERE dept_id = 1 ORDER BY name",
          lambda T: [(e["name"], e["salary"]) for e in sorted((e for e in T["employees"] if e["dept_id"] == 1), key=lambda e: e["name"])],
          "Without a comma, SQL reads 'name salary' as the column name with the alias salary, so only one column is returned.",
          hints=("Count the columns the query returns.",), starter="SELECT name salary FROM employees WHERE dept_id = 1 ORDER BY name", ordered=True),
        Q("group-by-having", "medium", "debug", "This query should list departments (dept_id) with more than 4 employees and their headcount, but it errors. Fix it; name the count headcount and order by dept_id.",
          "SELECT dept_id, COUNT(*) AS headcount FROM employees WHERE dept_id IS NOT NULL GROUP BY dept_id HAVING COUNT(*) > 4 ORDER BY dept_id",
          lambda T: [(d, n) for d, n in sorted((d, sum(1 for e in T["employees"] if e["dept_id"] == d)) for d in {e["dept_id"] for e in T["employees"] if e["dept_id"] is not None}) if n > 4],
          "Aggregates cannot be used in WHERE because WHERE runs before grouping. Conditions on aggregates belong in HAVING.",
          hints=("Which clause runs after GROUP BY?",), starter="SELECT dept_id, COUNT(*) FROM employees WHERE COUNT(*) > 4 GROUP BY dept_id", ordered=True, names=True),
        Q("joins", "medium", "debug", "Every department should be listed with its employee count as headcount (Legal must show 0), ordered by dept_name. The query shows 1 for Legal. Fix the bug.",
          "SELECT d.dept_name, COUNT(e.emp_id) AS headcount FROM departments d LEFT JOIN employees e ON d.dept_id = e.dept_id GROUP BY d.dept_id, d.dept_name ORDER BY d.dept_name",
          lambda T: sorted((d["dept_name"], sum(1 for e in T["employees"] if e["dept_id"] == d["dept_id"])) for d in T["departments"]),
          "COUNT(*) counts the NULL-padded row the LEFT JOIN creates for Legal. COUNT(e.emp_id) counts only real employees.",
          hints=("What does COUNT(*) count when the right side is all NULL?",),
          starter="SELECT d.dept_name, COUNT(*) AS headcount FROM departments d LEFT JOIN employees e ON d.dept_id = e.dept_id GROUP BY d.dept_id, d.dept_name ORDER BY d.dept_name", ordered=True, names=True),
        Q("joins", "easy", "debug", "This query should list each employee's name with their department name (only employees with a department), ordered by name, but it returns far too many rows. Fix it.",
          "SELECT e.name, d.dept_name FROM employees e JOIN departments d ON e.dept_id = d.dept_id ORDER BY e.name",
          lambda T: sorted(((e["name"], d["dept_name"]) for e in T["employees"] for d in T["departments"] if e["dept_id"] == d["dept_id"])),
          "Listing two tables with no join condition produces the Cartesian product (16 x 5 rows). Join on the shared key.",
          hints=("How many rows does a join without ON produce?",), starter="SELECT e.name, d.dept_name FROM employees e, departments d ORDER BY e.name", ordered=True),
        Q("joins", "hard", "debug", "This query should return the names of departments that have no projects, but it returns nothing. Fix the join.",
          "SELECT d.dept_name FROM departments d LEFT JOIN projects p ON p.dept_id = d.dept_id WHERE p.project_id IS NULL ORDER BY d.dept_name",
          lambda T: [(d["dept_name"],) for d in sorted(T["departments"], key=lambda d: d["dept_name"]) if not any(p["dept_id"] == d["dept_id"] for p in T["projects"])],
          "An INNER JOIN drops departments without projects, so the IS NULL test can never match. A LEFT JOIN keeps them.",
          hints=("Which join keeps unmatched rows from the left table?",),
          starter="SELECT d.dept_name FROM departments d JOIN projects p ON p.dept_id = d.dept_id WHERE p.project_id IS NULL ORDER BY d.dept_name", ordered=True),
        Q("null-constraint-violations", "medium", "debug", "Return the names (ordered) of employees whose salary is not 65000, INCLUDING employees with no recorded salary. The query misses one person. Fix it.",
          "SELECT name FROM employees WHERE salary <> 65000 OR salary IS NULL ORDER BY name",
          lambda T: [(e["name"],) for e in sorted(T["employees"], key=lambda e: e["name"]) if e["salary"] is None or e["salary"] != 65000],
          "salary <> 65000 is unknown when salary is NULL, so NULL rows are filtered out. Add an explicit IS NULL branch.",
          hints=("What does NULL <> 65000 evaluate to?",), starter="SELECT name FROM employees WHERE salary <> 65000 ORDER BY name", ordered=True),
        Q("subqueries", "medium", "debug", "Return the names (ordered) of employees whose salary equals ANY salary paid in Engineering (dept_id = 1). The query returns only one name. Fix it.",
          "SELECT name FROM employees WHERE salary IN (SELECT salary FROM employees WHERE dept_id = 1) ORDER BY name",
          lambda T: [(e["name"],) for e in sorted(T["employees"], key=lambda e: e["name"]) if e["salary"] is not None and e["salary"] in {x["salary"] for x in T["employees"] if x["dept_id"] == 1 and x["salary"] is not None}],
          "= compares with a single value (SQLite uses the first row of the subquery). IN tests membership in the whole set.",
          hints=("The subquery returns several values.",), starter="SELECT name FROM employees WHERE salary = (SELECT salary FROM employees WHERE dept_id = 1) ORDER BY name", ordered=True),
        Q("group-by-having", "medium", "debug", "Return customer_id and total (sum of amount) for the three customers with the highest total of DELIVERED orders, largest first. The query has a syntax error. Fix it.",
          "SELECT customer_id, SUM(amount) AS total FROM orders WHERE status = 'delivered' GROUP BY customer_id ORDER BY total DESC LIMIT 3",
          lambda T: _top_delivered(T),
          "Clause order is fixed: WHERE, GROUP BY, ORDER BY, LIMIT. A WHERE after LIMIT is a syntax error.",
          hints=("Check the order of the clauses.",), starter="SELECT customer_id, SUM(amount) AS total FROM orders GROUP BY customer_id ORDER BY total DESC LIMIT 3 WHERE status = 'delivered'", ordered=True, names=True),
        Q("window-functions", "hard", "debug", "Return name and rank r for Sales employees (dept_id = 2), ranked by salary descending with RANK(), ordered by r then name. The window syntax is broken. Fix it.",
          "SELECT name, RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS r FROM employees WHERE dept_id = 2 ORDER BY r, name",
          lambda T: _sales_rank(T), "The window specification must be written inside parentheses after OVER.", hints=("OVER takes a parenthesised window specification.",), requires=WF,
          starter="SELECT name, RANK() OVER PARTITION BY dept_id ORDER BY salary DESC AS r FROM employees WHERE dept_id = 2 ORDER BY r, name", ordered=True, names=True),
        Q("null-constraint-violations", "medium", "debug", "Return the average salary of employees who have NO department, as avg_salary. The query returns NULL instead of a number. Fix it.",
          "SELECT AVG(salary) AS avg_salary FROM employees WHERE dept_id IS NULL",
          lambda T: [(sum(e["salary"] for e in T["employees"] if e["dept_id"] is None) / sum(1 for e in T["employees"] if e["dept_id"] is None),)],
          "= NULL is never true, so no row matched and AVG of nothing is NULL. IS NULL is the right test.", hints=("How do you test for NULL?",),
          starter="SELECT AVG(salary) AS avg_salary FROM employees WHERE dept_id = NULL", names=True),
        Q("basic-sql-operations", "easy", "debug", "Return each distinct city of customers that have a city, alphabetically, as one column. The query repeats cities and shows a NULL. Fix it.",
          "SELECT DISTINCT city FROM customers WHERE city IS NOT NULL ORDER BY city",
          lambda T: [(c,) for c in sorted({c["city"] for c in T["customers"] if c["city"] is not None})],
          "DISTINCT removes duplicate rows and WHERE city IS NOT NULL removes the missing value.", hints=("Two cities appear more than once.",), starter="SELECT city FROM customers ORDER BY city", ordered=True),
        # ---- debug: multiple choice ----
        M("aggregate-functions", "medium", "Why does this query raise an error?", "An aggregate cannot be used in WHERE; the condition must go in HAVING after GROUP BY",
          ["COUNT(*) needs a column name", "GROUP BY must come before FROM", "dept_id cannot be selected with COUNT"], "WHERE is evaluated per row before grouping, so an aggregate result does not exist yet.",
          fmt="debug", code="SELECT dept_id, COUNT(*) FROM employees WHERE COUNT(*) > 4 GROUP BY dept_id", dialect="standard"),
        M("joins", "hard", "This query is meant to list customers with no orders but returns no rows. What is the cause?", "The INNER JOIN already discards customers without orders, so o.order_id IS NULL never matches",
          ["IS NULL cannot be used with joins", "customer_id is not a key", "ORDER BY removes all rows"], "Use LEFT JOIN so unmatched customers survive with NULLs on the order side.", fmt="debug",
          code="SELECT c.customer_name FROM customers c JOIN orders o ON o.customer_id = c.customer_id WHERE o.order_id IS NULL"),
        # ---- complete ----
        Q("joins", "medium", "complete", "List every employee with the department name (NULL when none), ordered by name. Return name and dept_name. Fill the blank with the right join type.",
          "SELECT e.name, d.dept_name FROM employees e LEFT JOIN departments d ON e.dept_id = d.dept_id ORDER BY e.name",
          lambda T: sorted((e["name"], next((d["dept_name"] for d in T["departments"] if d["dept_id"] == e["dept_id"]), None)) for e in T["employees"]),
          "A LEFT JOIN keeps every employee, including the one with no department, whose dept_name is NULL.", hints=("Which table must keep all its rows?",),
          starter="SELECT e.name, d.dept_name FROM employees e ___ JOIN departments d ON e.dept_id = d.dept_id ORDER BY e.name", ordered=True),
        Q("group-by-having", "medium", "complete", "Return customer_id and orders_count for customers with at least 3 orders, ordered by customer_id. Fill in the missing clause keyword.",
          "SELECT customer_id, COUNT(*) AS orders_count FROM orders GROUP BY customer_id HAVING COUNT(*) >= 3 ORDER BY customer_id",
          lambda T: [(c, n) for c, n in sorted((c, sum(1 for o in T["orders"] if o["customer_id"] == c)) for c in {o["customer_id"] for o in T["orders"]}) if n >= 3],
          "A condition on an aggregate is written with HAVING after GROUP BY.", hints=("Which clause filters groups?",),
          starter="SELECT customer_id, COUNT(*) AS orders_count FROM orders GROUP BY customer_id ___ COUNT(*) >= 3 ORDER BY customer_id", ordered=True, names=True),
        Q("subqueries", "medium", "complete", "Return the names of employees paid less than the company average salary (employees with no salary are not included), ordered by name. Fill in the aggregate function.",
          "SELECT name FROM employees WHERE salary < (SELECT AVG(salary) FROM employees) ORDER BY name",
          lambda T: [(e["name"],) for e in sorted(T["employees"], key=lambda e: e["name"]) if e["salary"] is not None and e["salary"] < _mean([x["salary"] for x in T["employees"]])],
          "The scalar subquery computes the average once and the outer WHERE compares each salary with it.", hints=("Which aggregate returns the mean?",),
          starter="SELECT name FROM employees WHERE salary < (SELECT ___(salary) FROM employees) ORDER BY name", ordered=True),
        Q("window-functions", "medium", "complete", "For customer 2's orders, return order_id, amount and prev_amount (the previous order's amount, NULL for the first), ordered by order_id. Fill in the window function.",
          "SELECT order_id, amount, LAG(amount) OVER (ORDER BY order_id) AS prev_amount FROM orders WHERE customer_id = 2 ORDER BY order_id",
          lambda T: _lag_c2(T), "LAG(x) returns the value from the previous row of the window.", hints=("Which function looks at the previous row?",), requires=WF,
          starter="SELECT order_id, amount, ___(amount) OVER (ORDER BY order_id) AS prev_amount FROM orders WHERE customer_id = 2 ORDER BY order_id", ordered=True, names=True),
        Q("set-operators", "medium", "complete", "Using a set operator, return the customer_id values that appear in BOTH customers and orders, ordered ascending. Fill in the operator.",
          "SELECT customer_id FROM customers INTERSECT SELECT customer_id FROM orders ORDER BY customer_id",
          lambda T: [(c,) for c in sorted({c["customer_id"] for c in T["customers"]} & {o["customer_id"] for o in T["orders"]})],
          "INTERSECT returns rows common to both queries.", hints=("Which operator keeps only the overlap?",),
          starter="SELECT customer_id FROM customers ___ SELECT customer_id FROM orders ORDER BY customer_id", ordered=True),
        Q("aggregate-functions", "easy", "complete", "Return each order status and how many orders have it, as n, ordered by status. Fill in the aggregate function.",
          "SELECT status, COUNT(*) AS n FROM orders GROUP BY status ORDER BY status",
          lambda T: sorted((s, sum(1 for o in T["orders"] if o["status"] == s)) for s in {o["status"] for o in T["orders"]}),
          "COUNT(*) counts the rows in each group.", hints=("Which aggregate counts rows?",), starter="SELECT status, ___(*) AS n FROM orders GROUP BY status ORDER BY status", ordered=True, names=True),
        Q("basic-sql-operations", "medium", "complete", "Return the names (ordered) of Sales employees (dept_id = 2) hired between 2019-01-01 and 2020-12-31 inclusive. Fill in the operator.",
          "SELECT name FROM employees WHERE hire_date BETWEEN '2019-01-01' AND '2020-12-31' AND dept_id = 2 ORDER BY name",
          lambda T: [(e["name"],) for e in sorted(T["employees"], key=lambda e: e["name"]) if e["dept_id"] == 2 and "2019-01-01" <= e["hire_date"] <= "2020-12-31"],
          "BETWEEN is inclusive of both bounds.", hints=("Which operator checks a range?",),
          starter="SELECT name FROM employees WHERE hire_date ___ '2019-01-01' AND '2020-12-31' AND dept_id = 2 ORDER BY name", ordered=True),
    ]


def _mean(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals)


def _top_delivered(T):
    totals: dict[int, float] = {}
    for o in T["orders"]:
        if o["status"] == "delivered" and o["amount"] is not None:
            totals[o["customer_id"]] = totals.get(o["customer_id"], 0.0) + o["amount"]
    return sorted(totals.items(), key=lambda kv: -kv[1])[:3]


def _sales_rank(T):
    emps = [e for e in T["employees"] if e["dept_id"] == 2]
    return sorted(((e["name"], 1 + sum(1 for x in emps if x["salary"] > e["salary"])) for e in emps), key=lambda r: (r[1], r[0]))


def _lag_c2(T):
    rows = sorted((o for o in T["orders"] if o["customer_id"] == 2), key=lambda o: o["order_id"])
    prev = [None] + [o["amount"] for o in rows[:-1]]
    return [(o["order_id"], o["amount"], p) for o, p in zip(rows, prev)]
