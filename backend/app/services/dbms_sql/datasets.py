"""
Predefined, disposable SQL practice datasets (Phase 25).

The `practice` dataset has six tables: employees, departments, projects, employee_projects, customers and orders.
It is plain repository data. At startup it is built once into an in-memory SQLite image (never a file, never the
application's MongoDB); every sandbox run gets its own fresh copy of that image, so nothing a query does can persist
or leak between users or sessions.

Deliberate edge cases (exercises rely on them):
  * departments : Legal (5) has NO employees.
  * employees   : Manoj (13) has NO department; Neha (14) has a NULL salary; several people share a salary
                  (95000, 65000, 70000); Asha, Esha, Isha, Kavya and Manoj have no manager.
  * projects    : Echo (105) has NO assigned employees; Bilal and Dev work on two projects.
  * employee_projects : Isha, Jatin and Manoj are on no project. Composite primary key (emp_id, project_id).
  * customers   : Green Grocers (7) and Harbor Hotels (8) have NO orders; Harbor Hotels has a NULL city.
  * orders      : order 1012 has a NULL amount; two orders share the amount 75.00; some are cancelled.
Indexes (so execution-plan questions are checkable): idx_employees_dept(dept_id), idx_orders_customer_amount(customer_id, amount).
"""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from typing import Any

DEFAULT_DATASET = "practice"

DDL = """
CREATE TABLE departments (
    dept_id    INTEGER PRIMARY KEY,
    dept_name  TEXT NOT NULL UNIQUE,
    location   TEXT NOT NULL,
    budget     INTEGER NOT NULL
);
CREATE TABLE employees (
    emp_id      INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    dept_id     INTEGER REFERENCES departments(dept_id),
    manager_id  INTEGER REFERENCES employees(emp_id),
    salary      INTEGER,
    hire_date   TEXT NOT NULL,
    job_title   TEXT NOT NULL
);
CREATE TABLE projects (
    project_id    INTEGER PRIMARY KEY,
    project_name  TEXT NOT NULL,
    dept_id       INTEGER NOT NULL REFERENCES departments(dept_id),
    budget        INTEGER NOT NULL,
    start_date    TEXT NOT NULL
);
CREATE TABLE employee_projects (
    emp_id      INTEGER NOT NULL REFERENCES employees(emp_id),
    project_id  INTEGER NOT NULL REFERENCES projects(project_id),
    role        TEXT NOT NULL,
    hours       INTEGER NOT NULL,
    PRIMARY KEY (emp_id, project_id)
);
CREATE TABLE customers (
    customer_id    INTEGER PRIMARY KEY,
    customer_name  TEXT NOT NULL,
    city           TEXT,
    signup_date    TEXT NOT NULL
);
CREATE TABLE orders (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date   TEXT NOT NULL,
    amount       REAL,
    status       TEXT NOT NULL
);
CREATE INDEX idx_employees_dept ON employees(dept_id);
CREATE INDEX idx_orders_customer_amount ON orders(customer_id, amount);
"""

TABLE_ORDER = ("departments", "employees", "projects", "employee_projects", "customers", "orders")

COLUMNS: dict[str, tuple[str, ...]] = {
    "departments": ("dept_id", "dept_name", "location", "budget"),
    "employees": ("emp_id", "name", "dept_id", "manager_id", "salary", "hire_date", "job_title"),
    "projects": ("project_id", "project_name", "dept_id", "budget", "start_date"),
    "employee_projects": ("emp_id", "project_id", "role", "hours"),
    "customers": ("customer_id", "customer_name", "city", "signup_date"),
    "orders": ("order_id", "customer_id", "order_date", "amount", "status"),
}

ROWS: dict[str, list[tuple[Any, ...]]] = {
    "departments": [
        (1, "Engineering", "Bengaluru", 900000),
        (2, "Sales", "Mumbai", 500000),
        (3, "HR", "Delhi", 250000),
        (4, "Marketing", "Mumbai", 400000),
        (5, "Legal", "Delhi", 150000),
    ],
    "employees": [
        (1, "Asha", 1, None, 150000, "2015-03-01", "Engineering Director"),
        (2, "Bilal", 1, 1, 95000, "2018-06-15", "Senior Engineer"),
        (3, "Chitra", 1, 1, 95000, "2019-01-10", "Senior Engineer"),
        (4, "Dev", 1, 2, 70000, "2021-07-01", "Engineer"),
        (5, "Esha", 2, None, 110000, "2016-09-12", "Sales Head"),
        (6, "Farhan", 2, 5, 65000, "2020-02-20", "Sales Executive"),
        (7, "Gita", 2, 5, 65000, "2022-04-05", "Sales Executive"),
        (8, "Harish", 2, 5, 80000, "2019-11-30", "Account Manager"),
        (9, "Isha", 3, None, 90000, "2017-05-17", "HR Manager"),
        (10, "Jatin", 3, 9, 52000, "2023-01-09", "HR Associate"),
        (11, "Kavya", 4, None, 85000, "2018-08-08", "Marketing Lead"),
        (12, "Leela", 4, 11, 58000, "2022-10-10", "Content Strategist"),
        (13, "Manoj", None, None, 60000, "2023-03-03", "Consultant"),
        (14, "Neha", 1, 2, None, "2024-02-01", "Intern"),
        (15, "Omar", 1, 3, 70000, "2022-01-17", "Engineer"),
        (16, "Pooja", 2, 5, 72000, "2021-12-01", "Account Manager"),
    ],
    "projects": [
        (101, "Apollo", 1, 500000, "2023-01-15"),
        (102, "Borealis", 1, 300000, "2023-06-01"),
        (103, "Catalyst", 2, 200000, "2023-03-10"),
        (104, "Delta", 4, 120000, "2024-01-20"),
        (105, "Echo", 3, 80000, "2024-03-01"),
    ],
    "employee_projects": [
        (1, 101, "Lead", 120), (2, 101, "Developer", 300), (3, 101, "Developer", 280), (4, 101, "Developer", 200),
        (14, 101, "Intern", 60), (2, 102, "Lead", 150), (4, 102, "Developer", 220), (15, 102, "Developer", 180),
        (5, 103, "Sponsor", 40), (6, 103, "Executive", 160), (7, 103, "Executive", 140), (8, 103, "Analyst", 90),
        (16, 103, "Analyst", 110), (11, 104, "Lead", 100), (12, 104, "Writer", 210),
    ],
    "customers": [
        (1, "Aarav Traders", "Delhi", "2022-01-10"),
        (2, "Bharat Foods", "Mumbai", "2022-03-22"),
        (3, "Citrus Cafe", "Pune", "2022-07-05"),
        (4, "Delta Mart", "Delhi", "2023-02-14"),
        (5, "Eagle Books", "Chennai", "2023-05-30"),
        (6, "Falcon Gear", "Mumbai", "2023-09-01"),
        (7, "Green Grocers", "Pune", "2024-01-12"),
        (8, "Harbor Hotels", None, "2024-02-02"),
    ],
    "orders": [
        (1001, 1, "2023-01-05", 250.00, "delivered"),
        (1002, 1, "2023-02-11", 120.50, "delivered"),
        (1003, 2, "2023-02-15", 980.00, "delivered"),
        (1004, 2, "2023-03-02", 45.25, "cancelled"),
        (1005, 3, "2023-03-20", 310.75, "delivered"),
        (1006, 4, "2023-04-01", 75.00, "shipped"),
        (1007, 1, "2023-04-18", 640.00, "delivered"),
        (1008, 5, "2023-05-09", 89.99, "delivered"),
        (1009, 2, "2023-06-21", 450.00, "shipped"),
        (1010, 6, "2023-07-07", 1200.00, "delivered"),
        (1011, 4, "2023-08-30", 75.00, "delivered"),
        (1012, 3, "2023-09-12", None, "pending"),
        (1013, 6, "2023-10-01", 300.00, "cancelled"),
        (1014, 5, "2023-11-15", 150.00, "delivered"),
        (1015, 1, "2024-01-20", 99.50, "delivered"),
    ],
}

TABLE_DESCRIPTIONS = {
    "departments": "Company departments. Legal has no employees.",
    "employees": "Staff. dept_id and manager_id may be NULL; salary is NULL for the intern; some salaries are duplicated.",
    "projects": "Projects owned by a department. Echo has no assigned employees.",
    "employee_projects": "Which employee works on which project (many-to-many) with a role and hours. Composite key (emp_id, project_id).",
    "customers": "Shop customers. Two customers have never ordered; one has a NULL city.",
    "orders": "Customer orders. One order has a NULL amount; statuses are delivered, shipped, cancelled or pending.",
}

DATASET_INFO = {
    DEFAULT_DATASET: {
        "id": DEFAULT_DATASET,
        "title": "Company & shop practice data",
        "description": "Six small tables with realistic edge cases. Read-only and disposable: every run gets a fresh copy.",
    }
}


def dataset_ids() -> tuple[str, ...]:
    return tuple(DATASET_INFO)


@lru_cache(maxsize=1)
def _image() -> bytes:
    """Build the practice database once, in memory, and keep only its serialized bytes."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(DDL)
        for table in TABLE_ORDER:
            cols = COLUMNS[table]
            marks = ",".join("?" for _ in cols)
            conn.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({marks})", ROWS[table])
        conn.commit()
        return bytes(conn.serialize())
    finally:
        conn.close()


def image(dataset_id: str) -> bytes:
    if dataset_id not in DATASET_INFO:
        raise KeyError(dataset_id)
    return _image()


def table_names(dataset_id: str = DEFAULT_DATASET) -> frozenset[str]:
    if dataset_id not in DATASET_INFO:
        raise KeyError(dataset_id)
    return frozenset(TABLE_ORDER)


def python_tables() -> dict[str, list[dict[str, Any]]]:
    """The raw rows as lists of dicts, for the independent pure-Python oracles."""
    return {t: [dict(zip(COLUMNS[t], row)) for row in ROWS[t]] for t in TABLE_ORDER}


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    conn = sqlite3.connect(":memory:")
    try:
        conn.deserialize(_image())
        tables = []
        for t in TABLE_ORDER:
            fks = {r[3]: f"{r[2]}.{r[4]}" for r in conn.execute(f"PRAGMA foreign_key_list({t})")}
            cols = []
            for _cid, name, ctype, notnull, _default, pk in conn.execute(f"PRAGMA table_info({t})"):
                cols.append({"name": name, "type": ctype or "ANY", "primary_key": bool(pk), "not_null": bool(notnull or pk), "references": fks.get(name)})
            tables.append({
                "name": t, "description": TABLE_DESCRIPTIONS[t], "columns": cols,
                "rows": [list(r) for r in ROWS[t]], "row_count": len(ROWS[t]),
            })
        indexes = [{"name": n, "table": tb, "sql": s} for n, tb, s in conn.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name")]
        return {"tables": tables, "indexes": indexes}
    finally:
        conn.close()


def describe(dataset_id: str = DEFAULT_DATASET) -> dict[str, Any]:
    """Schema + every sample row, for the schema viewer. Reference data only: it contains no answers."""
    if dataset_id not in DATASET_INFO:
        raise KeyError(dataset_id)
    s = _schema()
    return {**DATASET_INFO[dataset_id], "tables": s["tables"], "indexes": s["indexes"], "ddl": DDL.strip()}
