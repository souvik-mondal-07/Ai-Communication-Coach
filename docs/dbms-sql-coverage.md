# DBMS & SQL Interview Lab: syllabus coverage report

Generated from the validated seed bank: **333 questions**, 0 rejected. A topic is *ready* with at least 3 questions; depth beyond that minimum is stated, not implied.

SQL practice engine: SQLite 3.45.1 (read-only; window functions: True; RIGHT/FULL JOIN: True).

**Verification:** 123 questions are machine-verified (reference computation, or SQL engine plus an independent Python oracle). 210 are manual-review definition questions with a written justification but NO executable check; they need subject-expert sign-off.

| Questions by format | Count |
|---|---:|
| concept | 180 |
| design | 31 |
| query | 30 |
| scenario | 26 |
| output | 22 |
| transaction | 22 |
| debug | 13 |
| complete | 9 |

| Questions by interaction | Count |
|---|---:|
| mcq | 277 |
| sql | 50 |
| short | 6 |

| Questions by difficulty | Count |
|---|---:|
| medium | 147 |
| easy | 99 |
| hard | 87 |

| Questions by dialect | Count |
|---|---:|
| standard | 220 |
| sqlite | 71 |
| mongodb | 23 |
| mysql | 5 |
| postgresql | 4 |
| sqlserver | 4 |
| dynamodb | 4 |
| oracle | 2 |

| Verification method | Count |
|---|---:|
| manual review (no machine check) | 210 |
| reference computation | 54 |
| SQL engine + Python oracle | 50 |
| SQL engine + Python oracle/declared value | 19 |

## Unit A: Introduction to databases (32 questions)

| Topic | Total | E/M/H | Formats | Interactions | Machine-verified | Status |
|---|---:|:-:|---|---|---:|---|
| Purpose and advantages of DBMS | 3 | 1/1/1 | concept 3 | mcq 3 | 0 | implemented |
| Components and applications of DBMS | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Three-tier architecture | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Data independence | 3 | 1/1/1 | concept 3 | mcq 3 | 0 | implemented |
| Database schema versus instance | 4 | 2/1/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Data modelling | 4 | 2/1/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Entity-Relationship model | 3 | 1/1/1 | concept 3 | mcq 3 | 0 | implemented |
| Relational model | 3 | 1/1/1 | concept 3 | mcq 3 | 0 | implemented |
| Relational versus non-relational databases | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |

## Unit B: Relational query language (43 questions)

| Topic | Total | E/M/H | Formats | Interactions | Machine-verified | Status |
|---|---:|:-:|---|---|---:|---|
| DDL, DML, DCL, and TCL | 4 | 2/1/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| SQL commands and their purposes | 3 | 1/1/1 | concept 3 | mcq 3 | 0 | implemented |
| Integrity constraints | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Primary, foreign, candidate, super, and composite keys | 8 | 2/4/2 | design 8 | mcq 5, short 3 | 6 | implemented |
| Basic SQL operations | 9 | 5/3/1 | complete 1, concept 1, debug 2, query 5 | mcq 1, sql 8 | 8 | implemented |
| INSERT, SELECT, UPDATE, and DELETE concepts | 5 | 2/2/1 | concept 3, output 2 | mcq 5 | 2 | implemented |
| NULL handling and constraint violations | 10 | 4/5/1 | complete 1, concept 2, debug 2, output 4, query 1 | mcq 6, sql 4 | 8 | implemented |

## Unit C: Relational operations and advanced SQL (85 questions)

| Topic | Total | E/M/H | Formats | Interactions | Machine-verified | Status |
|---|---:|:-:|---|---|---:|---|
| Aggregate functions | 7 | 3/3/1 | complete 1, concept 1, debug 1, output 2, query 2 | mcq 4, sql 3 | 5 | implemented |
| GROUP BY and HAVING | 9 | 2/6/1 | complete 1, concept 2, debug 2, output 1, query 3 | mcq 3, sql 6 | 7 | implemented |
| INNER, LEFT, RIGHT, and other supported joins | 14 | 4/7/3 | complete 1, concept 3, debug 4, output 1, query 5 | mcq 5, sql 9 | 11 | implemented |
| Set operators | 6 | 1/4/1 | complete 1, concept 1, output 1, query 3 | mcq 2, sql 4 | 5 | implemented |
| Views | 4 | 1/2/1 | concept 3, query 1 | mcq 3, sql 1 | 1 | implemented |
| Subqueries and correlated subqueries | 9 | 1/5/3 | complete 1, concept 2, debug 1, output 1, query 4 | mcq 3, sql 6 | 7 | implemented |
| Relational algebra | 5 | 1/3/1 | concept 4, output 1 | mcq 5 | 1 | implemented |
| Window functions | 8 | 1/3/4 | complete 1, concept 2, debug 1, output 1, query 3 | mcq 3, sql 5 | 6 | implemented |
| Ranking and partitioning | 5 | 1/2/2 | concept 2, query 3 | mcq 2, sql 3 | 3 | implemented |
| Hashing and indexing | 6 | 2/3/1 | concept 5, scenario 1 | mcq 6 | 2 | implemented |
| Query optimization | 5 | 1/3/1 | concept 4, scenario 1 | mcq 5 | 0 | implemented |
| Execution plans and performance reasoning | 7 | 2/3/2 | concept 2, output 5 | mcq 7 | 5 | implemented |

## Unit D: Relational database design (45 questions)

| Topic | Total | E/M/H | Formats | Interactions | Machine-verified | Status |
|---|---:|:-:|---|---|---:|---|
| Data integrity | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Functional dependencies | 6 | 2/3/1 | concept 1, design 5 | mcq 4, short 2 | 4 | implemented |
| Purpose of normalization | 4 | 1/1/2 | concept 3, design 1 | mcq 3, short 1 | 1 | implemented |
| First Normal Form (1NF) | 4 | 2/1/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Second Normal Form (2NF) | 4 | 2/1/1 | concept 1, design 3 | mcq 4 | 3 | implemented |
| Third Normal Form (3NF) | 4 | 1/2/1 | concept 1, design 3 | mcq 4 | 3 | implemented |
| Boyce-Codd Normal Form (BCNF) | 3 | 1/1/1 | concept 1, design 2 | mcq 3 | 2 | implemented |
| Multivalued dependencies | 3 | 1/1/1 | concept 1, design 2 | mcq 3 | 2 | implemented |
| Fourth Normal Form (4NF) | 4 | 1/2/1 | concept 1, design 3 | mcq 4 | 3 | implemented |
| Identifying insertion, update, and deletion anomalies | 4 | 2/1/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Decomposition and lossless-join reasoning | 5 | 1/2/2 | concept 1, design 4 | mcq 5 | 4 | implemented |

## Unit E: Database programming constructs (26 questions)

| Topic | Total | E/M/H | Formats | Interactions | Machine-verified | Status |
|---|---:|:-:|---|---|---:|---|
| Database flow control | 5 | 1/3/1 | complete 1, concept 3, scenario 1 | mcq 4, sql 1 | 1 | implemented |
| Functions | 3 | 1/1/1 | concept 3 | mcq 3 | 0 | implemented |
| Stored procedures | 4 | 2/1/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Cursors | 3 | 1/1/1 | concept 3 | mcq 3 | 0 | implemented |
| Triggers | 3 | 1/1/1 | concept 3 | mcq 3 | 0 | implemented |
| Exception handling | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Differences between database features across SQL dialects | 4 | 1/2/1 | concept 4 | mcq 4 | 0 | implemented |

## Unit F: Transactions and concurrency (59 questions)

| Topic | Total | E/M/H | Formats | Interactions | Machine-verified | Status |
|---|---:|:-:|---|---|---:|---|
| Transaction concepts | 4 | 2/1/1 | concept 3, scenario 1 | mcq 4 | 1 | implemented |
| ACID properties | 4 | 1/2/1 | concept 4 | mcq 4 | 0 | implemented |
| Transaction states | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Schedules | 5 | 2/1/2 | concept 1, transaction 4 | mcq 5 | 4 | implemented |
| Serial and concurrent execution | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Conflict and view serializability | 5 | 1/2/2 | concept 2, transaction 3 | mcq 5 | 3 | implemented |
| Concurrency control | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Locking concepts | 4 | 1/2/1 | concept 3, transaction 1 | mcq 4 | 1 | implemented |
| Deadlocks | 6 | 1/3/2 | concept 3, transaction 3 | mcq 6 | 3 | implemented |
| Recoverability | 5 | 1/2/2 | concept 1, transaction 4 | mcq 5 | 4 | implemented |
| Cascading rollback | 4 | 1/2/1 | concept 1, transaction 3 | mcq 4 | 3 | implemented |
| Dirty reads, non-repeatable reads, and phantom reads | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Isolation levels | 6 | 1/3/2 | concept 2, transaction 4 | mcq 6 | 3 | implemented |

## Unit G: NoSQL and MongoDB (43 questions)

| Topic | Total | E/M/H | Formats | Interactions | Machine-verified | Status |
|---|---:|:-:|---|---|---:|---|
| NoSQL database concepts | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| MongoDB | 4 | 2/1/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| DynamoDB concepts | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| Serverless cloud databases | 3 | 1/1/1 | concept 3 | mcq 3 | 0 | implemented |
| MongoDB databases, collections, and documents | 4 | 2/1/1 | concept 4 | mcq 4 | 0 | implemented |
| Basic MongoDB CRUD operations | 5 | 1/3/1 | concept 2, output 3 | mcq 5 | 0 | implemented |
| SQL versus NoSQL | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| JSON representation and document modelling | 3 | 1/1/1 | concept 3 | mcq 3 | 1 | implemented |
| Index creation and performance | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |
| EXPLAIN and query-plan interpretation | 4 | 1/2/1 | concept 4 | mcq 4 | 0 | implemented |
| Vector databases and their use cases | 4 | 1/2/1 | concept 3, scenario 1 | mcq 4 | 0 | implemented |

## Remaining gaps

- No topic is below the minimum, and every topic has all three difficulty levels.

Thinnest topics (candidates for the next content expansion): Boyce-Codd Normal Form (BCNF) (3); Cursors (3); Data independence (3); Entity-Relationship model (3); Functions (3); JSON representation and document modelling (3); Multivalued dependencies (3); Purpose and advantages of DBMS (3).

