"""
The complete DBMS & SQL syllabus (Phase 25): 7 units (A-G) and 70 topics.

Every bullet of the supplied syllabus is exactly one topic, so any syllabus line traces to a topic and then to real questions.
This file is static reference data: it never claims a topic is "done" -- completion is computed from questions that exist.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    id: str
    title: str


@dataclass(frozen=True)
class Unit:
    id: str
    code: str
    title: str
    summary: str
    topics: tuple[Topic, ...]


def _u(code: str, title: str, summary: str, topics: list[tuple[str, str]]) -> Unit:
    return Unit(f"unit-{code.lower()}", code, title, summary, tuple(Topic(i, t) for i, t in topics))


UNITS: tuple[Unit, ...] = (
    _u("A", "Introduction to databases", "Why DBMS exists, how it is structured, and how data is modelled.", [
        ("purpose-advantages", "Purpose and advantages of DBMS"),
        ("components-applications", "Components and applications of DBMS"),
        ("three-tier-architecture", "Three-tier architecture"),
        ("data-independence", "Data independence"),
        ("schema-instance", "Database schema versus instance"),
        ("data-modelling", "Data modelling"),
        ("er-model", "Entity-Relationship model"),
        ("relational-model", "Relational model"),
        ("relational-vs-nonrelational", "Relational versus non-relational databases"),
    ]),
    _u("B", "Relational query language", "SQL command families, constraints, keys and the four basic operations.", [
        ("ddl-dml-dcl-tcl", "DDL, DML, DCL, and TCL"),
        ("sql-commands", "SQL commands and their purposes"),
        ("integrity-constraints", "Integrity constraints"),
        ("keys", "Primary, foreign, candidate, super, and composite keys"),
        ("basic-sql-operations", "Basic SQL operations"),
        ("crud-concepts", "INSERT, SELECT, UPDATE, and DELETE concepts"),
        ("null-constraint-violations", "NULL handling and constraint violations"),
    ]),
    _u("C", "Relational operations and advanced SQL", "Aggregation, joins, subqueries, windows, indexing and query performance.", [
        ("aggregate-functions", "Aggregate functions"),
        ("group-by-having", "GROUP BY and HAVING"),
        ("joins", "INNER, LEFT, RIGHT, and other supported joins"),
        ("set-operators", "Set operators"),
        ("views", "Views"),
        ("subqueries", "Subqueries and correlated subqueries"),
        ("relational-algebra", "Relational algebra"),
        ("window-functions", "Window functions"),
        ("ranking-partitioning", "Ranking and partitioning"),
        ("hashing-indexing", "Hashing and indexing"),
        ("query-optimization", "Query optimization"),
        ("execution-plans", "Execution plans and performance reasoning"),
    ]),
    _u("D", "Relational database design", "Dependencies, normal forms, anomalies and decomposition.", [
        ("data-integrity", "Data integrity"),
        ("functional-dependencies", "Functional dependencies"),
        ("normalization-purpose", "Purpose of normalization"),
        ("1nf", "First Normal Form (1NF)"),
        ("2nf", "Second Normal Form (2NF)"),
        ("3nf", "Third Normal Form (3NF)"),
        ("bcnf", "Boyce-Codd Normal Form (BCNF)"),
        ("multivalued-dependencies", "Multivalued dependencies"),
        ("4nf", "Fourth Normal Form (4NF)"),
        ("anomalies", "Identifying insertion, update, and deletion anomalies"),
        ("decomposition-lossless", "Decomposition and lossless-join reasoning"),
    ]),
    _u("E", "Database programming constructs", "Procedural SQL: flow control, routines, cursors, triggers and dialect differences.", [
        ("flow-control", "Database flow control"),
        ("functions", "Functions"),
        ("stored-procedures", "Stored procedures"),
        ("cursors", "Cursors"),
        ("triggers", "Triggers"),
        ("exception-handling", "Exception handling"),
        ("dialect-differences", "Differences between database features across SQL dialects"),
    ]),
    _u("F", "Transactions and concurrency", "ACID, schedules, serializability, locking, deadlocks and isolation.", [
        ("transaction-concepts", "Transaction concepts"),
        ("acid", "ACID properties"),
        ("transaction-states", "Transaction states"),
        ("schedules", "Schedules"),
        ("serial-concurrent", "Serial and concurrent execution"),
        ("serializability", "Conflict and view serializability"),
        ("concurrency-control", "Concurrency control"),
        ("locking", "Locking concepts"),
        ("deadlocks", "Deadlocks"),
        ("recoverability", "Recoverability"),
        ("cascading-rollback", "Cascading rollback"),
        ("read-anomalies", "Dirty reads, non-repeatable reads, and phantom reads"),
        ("isolation-levels", "Isolation levels"),
    ]),
    _u("G", "NoSQL and MongoDB", "Document, key-value and vector stores; MongoDB modelling, CRUD, indexes and plans.", [
        ("nosql-concepts", "NoSQL database concepts"),
        ("mongodb-intro", "MongoDB"),
        ("dynamodb-concepts", "DynamoDB concepts"),
        ("serverless-databases", "Serverless cloud databases"),
        ("mongodb-structure", "MongoDB databases, collections, and documents"),
        ("mongodb-crud", "Basic MongoDB CRUD operations"),
        ("sql-vs-nosql", "SQL versus NoSQL"),
        ("json-document-modelling", "JSON representation and document modelling"),
        ("mongodb-indexes", "Index creation and performance"),
        ("explain-query-plans", "EXPLAIN and query-plan interpretation"),
        ("vector-databases", "Vector databases and their use cases"),
    ]),
)

UNIT_BY_ID: dict[str, Unit] = {u.id: u for u in UNITS}
TOPIC_BY_ID: dict[str, Topic] = {t.id: t for u in UNITS for t in u.topics}
TOPIC_TO_UNIT: dict[str, str] = {t.id: u.id for u in UNITS for t in u.topics}
TOPIC_TITLES: dict[str, str] = {tid: t.title for tid, t in TOPIC_BY_ID.items()}

MIN_QUESTIONS_PER_TOPIC = 3


def unit_title(unit_id: str) -> str:
    u = UNIT_BY_ID.get(unit_id)
    return u.title if u else unit_id


def topic_title(topic_id: str) -> str:
    return TOPIC_TITLES.get(topic_id, topic_id)
