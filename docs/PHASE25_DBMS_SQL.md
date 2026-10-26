# Phase 25: DBMS & SQL Interview Lab

A dedicated module for database theory, SQL query writing, output prediction, debugging, normalization, transactions and
NoSQL/MongoDB interview practice. Route: **`/dbms-sql`** (sidebar: *DBMS & SQL Lab*; also a dashboard Quick Access link).
The suggested URL `/practice/dbms-sql` redirects to it. The app's existing convention is a top-level route per module
(`/aptitude`, `/dsa`), and `/practice` is already the cybersecurity practice page, so a nested route would have clashed.

## What was built

* **Syllabus:** 7 units (A-G), **70 topics**, one per bullet of the supplied syllabus (`services/dbms_sql/syllabus.py`).
* **Question bank:** **333 validated questions**, seeded idempotently into MongoDB, with every topic at 3 or more questions and
  all three difficulty levels. Formats: concept 180, design 31, query 30, scenario 26, output 22, transaction 22, debug 13,
  complete 9. Interactions: 277 multiple-choice, 50 SQL exercises, 6 short-answer. See
  [`dbms-sql-coverage.md`](dbms-sql-coverage.md) for per-topic counts.
* **12 practice modes:** topic practice, mixed practice, technical interview, SQL query lab, predict the output, debug the
  query, complete the query, database design lab, transaction scenario lab, NoSQL & MongoDB lab, timed mock interview, weak topics.
  Easy / medium / hard selection, question count 1-50, optional timer (mandatory for the mock).
* **SQL playground:** free, unscored exploration of the sample tables in the same sandbox.
* **Schema and sample-data viewer**, result tables, plain-language errors, progressive hints, reference solutions with explanations.
* **Analytics:** accuracy by topic, unit and difficulty; SQL queries checked / solved / solutions revealed; mock scores; repeated
  mistakes; weak topics and recommendations; improvement trend. All computed from stored, graded attempts. Empty state when there is no history.
* **History Center integration:** sessions appear under type `dbms_sql` with a full scored review.

## Files

**New (backend)**

| File | Purpose |
|---|---|
| `app/schemas/dbms_sql.py` | Question and request schemas (Pydantic 2) |
| `app/api/routes/dbms_sql.py` | 16 routes |
| `app/services/dbms_sql/syllabus.py` | Units and topics |
| `app/services/dbms_sql/datasets.py` | The six-table practice dataset, built into an in-memory image |
| `app/services/dbms_sql/sandbox.py` | The isolated SQL execution engine |
| `app/services/dbms_sql/sql_compare.py` | Deterministic result comparison, feedback, short-answer grading |
| `app/services/dbms_sql/design_algos.py` | Closure, keys, normal forms, lossless-join chase, dependency preservation, MVD, 4NF |
| `app/services/dbms_sql/txn_algos.py` | Conflict/view serializability, recoverability, cascading rollback, 2PL, deadlock detection, isolation |
| `app/services/dbms_sql/references.py`, `oracles.py` | Registries used to verify answer keys |
| `app/services/dbms_sql/validation.py`, `bank.py` | Fail-closed validation, seeding, public projection, syllabus and coverage |
| `app/services/dbms_sql/sessions.py`, `analytics.py` | Session lifecycle, server-side scoring, idempotent completion, analytics |
| `app/services/dbms_sql/cli.py`, `errors.py` | Maintainer CLI; consistent errors |
| `app/services/dbms_sql/content/*.py` | Question content: `unit_a`-`unit_g`, `labs`, `scenarios`, `build` |
| `tools/verify_dbms_bank.py` | Independent re-verification of the bank (see Commands) |
| `tests/test_dbms_sql_{sandbox,algos,bank,api,tools}.py` | 408 tests |
| `docs/dbms-sql-coverage.md`, `docs/PHASE25_DBMS_SQL.md` | This documentation |

**New (frontend):** `types/dbmsSql.ts`, `services/dbmsSqlService.ts`, `store/dbmsSqlStore.ts`, `pages/DbmsSql.tsx`,
`pages/DbmsSqlSession.tsx`, `pages/DbmsSqlResult.tsx`, `features/dbms-sql/*` (PracticeSetup, SyllabusBrowser, QuestionCard,
SqlWorkbench, SchemaViewer, ResultTable, QuestionNavigator, ResultView, ProgressPanel, Playground, dbmsSqlMeta), and tests
`App.dbmsSql.test.tsx`, `store/dbmsSqlStore.test.ts`, `features/dbms-sql/dbmsSqlMeta.test.ts`, `features/dbms-sql/integration.test.tsx`.

**Modified (14 files, small and additive)**

`backend/app/api/router.py` (register router), `app/main.py` (index + seed at startup), `app/db/collections.py` (3 collection names),
`app/schemas/history.py` and `app/services/history/history_service.py` (history type `dbms_sql`), `backend/tests/test_history.py`
(one line: the per-type count dict gained `dbms_sql: 0`, as earlier phases did);
`README.md` (Phase 25 section), `frontend/src/App.tsx` (routes + redirect), `components/common/navigation.ts` (sidebar item), `features/dashboard/QuickAccessCard.tsx`
(link), `features/history/{ActivityDetailBody.tsx,historyMeta.ts}` and `types/history.ts` (history type), `store/sessionReset.ts` (wipe on logout).

## Dependencies and environment

* **No new dependencies.** `requirements.txt` and `package.json` are unchanged. The SQL engine is Python's standard-library
  `sqlite3`; MongoDB remains the only application persistence. (`mongomock`, already a test dependency, re-verifies MongoDB examples in tests.)
* **No new environment variables.** Limits are constants in `sandbox.py`.
* No Docker, no other AI provider. **Gemini is not used anywhere in this module**, and a test enforces that: answer keys and grading
  are deterministic.

## Seeding

Automatic at API startup (`main.py` calls `ensure_indexes` then `ensure_seeded`). It is **idempotent**: stable question ids, unique
indexes on `question_id` and `fingerprint`, a content hash that bumps `version` only when a seed changes, and seeds that disappear
from the code become `inactive` (never deleted, so old results still resolve). Seeds are **fail-closed**: each one is validated
(its SQL re-executed, its answer key re-derived) and a seed that fails is logged and never stored.

## SQL sandbox: architecture and security

User SQL is **never** run against MongoDB or any application data. Defence in depth, each layer tested:

1. **Fresh copy per run:** the practice database is serialized once; every execution deserializes it into a brand-new `:memory:`
   connection and closes it afterwards. No file, no shared connection, no state between users or sessions.
2. **Statement gate (a real lexer, not substring matching):** comments, strings and quoted names are tokenised; only one
   `SELECT` / `WITH` / `VALUES` or `EXPLAIN QUERY PLAN <select>` is accepted. Multiple statements, bare `EXPLAIN`, `PRAGMA`,
   `ATTACH`, DDL, DML and transaction control are refused with a clear message.
3. **Engine-level authorizer (the real enforcement):** SQLite asks our callback about every action while compiling. We allow
   only SELECT, reads of the six practice tables (plus declared CTE names), and a whitelist of pure scalar, aggregate and window
   functions. Writes, `ATTACH`, `PRAGMA`, virtual tables, `sqlite_master`, `load_extension`, `readfile`, `randomblob` and
   `random` are denied **by SQLite itself**. The tests call SQLite directly, bypassing our lexer, to prove this layer holds alone.
4. `PRAGMA query_only=ON` and `trusted_schema=OFF`; extension loading is never enabled.
5. **Resource limits:** 4,000 characters of SQL, 200 result rows, 30 columns, 200-character cells, 1.5 s wall clock, and a
   deterministic 3 million VM-step budget enforced by SQLite's progress handler (runaway recursion and cross-join explosions are
   interrupted in tens of milliseconds); SQLite limits on expression depth, compound selects, LIKE pattern length and function arguments.
6. **Safe errors:** failures map to short categories (`syntax`, `unknown_object`, `not_allowed`, `timeout`, `limit`,
   `unsupported`, `runtime`). No traceback, path or internal text leaves the module.
7. **API controls:** authentication on every route, rate limits (sandbox 30/min, SQL check 20/min, session create 15/min), bounded
   bodies, user taken only from the token, identical 404 for missing and foreign sessions.

**Mutation check performed:** disabling the authorizer makes 24 sandbox tests fail; disabling the lexer gate makes 11 fail (the
engine-bypass tests still pass, proving the authorizer works alone).

**Limitations of the sandbox (be aware):** it runs in-process in the API worker (a thread), so there is no OS-level CPU or memory
cgroup; memory is bounded indirectly by the step budget and row/length limits. It guards against hostile *SQL*, not against a
vulnerability inside SQLite itself. For a hardened deployment run the API under container or `ulimit` resource limits. The rate
limiter is the project's existing in-memory, per-process limiter.

## Supported SQL dialect (practice engine: SQLite)

*Supported:* `SELECT` with `WHERE`, `ORDER BY`, `LIMIT`, `DISTINCT`, joins (INNER, LEFT, CROSS, and RIGHT/FULL on SQLite 3.39+),
`GROUP BY` / `HAVING`, aggregates, subqueries (scalar, `IN`, `EXISTS`, correlated), set operators (`UNION [ALL]`, `INTERSECT`, `EXCEPT`),
CTEs including `WITH RECURSIVE`, window functions (`ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE`, `LAG`, `LEAD`, `FIRST_VALUE`,
`LAST_VALUE`, `SUM/AVG/... OVER`), `CASE`, string/date/numeric functions, `EXPLAIN QUERY PLAN`. The UI reads the installed
SQLite version and capabilities from the server rather than assuming them.

*Not supported:* `INSERT/UPDATE/DELETE`, DDL, `PRAGMA`, multiple statements, views and triggers creation, vendor syntax
(`TOP`, `NVL`, `FETCH FIRST`, stored procedures, `DECLARE @`). DML, procedures, triggers and cursors are covered by multiple-choice
and output questions instead. **Vendor-specific questions are labelled** with their dialect (MySQL, PostgreSQL, Oracle, SQL Server,
MongoDB, DynamoDB) and validation refuses a question that uses vendor syntax but claims to be standard SQL.

## Correctness of the question bank

| How an answer is verified | Questions |
|---|---:|
| Reference computation (design / transaction algorithms), including 6 short answers (54 questions) | machine-verified |
| SQL engine **and** an independent pure-Python oracle agree (50 exercises + 19 output/plan questions = 69) | machine-verified |
| MongoDB result questions are additionally recomputed with `mongomock` in tests and the verifier | machine-verified |
| Definition-level theory: a written justification, **no executable check** (includes 3 MongoDB results re-checked with `mongomock` in tests) | **210 of 333 (63%)** |

123 questions are machine-verified. The 210 manual-review questions are authored and self-reviewed; **they need subject-expert
sign-off** before being treated as authoritative. They are reported separately and never counted as verified. The coverage
report states this explicitly.

Grading never trusts the client: a score, correctness flag or completion status sent by the browser is ignored (tested). SQL is
graded by **result comparison** (columns by position and optionally by name, rows as a multiset unless ordering is required,
NULL-aware, numeric precision, case-sensitive text), so a different valid query structure is accepted.

## API (all under `/api/v1/dbms-sql`, all authenticated)

`GET /syllabus` · `GET /coverage` · `GET /datasets/{id}` · `GET /questions` (answer-free, filtered, paginated, max 50) ·
`POST /sandbox/run` · `POST /sessions` · `GET /sessions` · `GET /sessions/{id}` · `PUT /sessions/{id}/answers/{qid}` ·
`POST /sessions/{id}/questions/{qid}/check` · `.../reveal` · `.../hint` · `POST /sessions/{id}/submit` ·
`GET /sessions/{id}/result` · `GET /progress` · `GET /recommendations`.

Answer keys, explanations, reference queries and expected rows are returned only after an answer locks (practice), after an
explicit reveal, or in the result after completion. The timed mock reveals nothing, and allows no check, hint or reveal, until submission.
Revealing a SQL solution before solving it scores that question 0. Completion is one atomic conditional update, and attempts are
written once (unique index), so retries and the timer racing the button cannot double-count.

## Commands

```bash
# backend (from backend/)
pip install -r requirements.txt
uvicorn app.main:app --reload                       # seeds the bank on startup
python -m tools.verify_dbms_bank                    # re-run every SQL reference, oracle, MongoDB check and a live security probe
python -m app.services.dbms_sql.cli coverage        # regenerate docs/dbms-sql-coverage.md
python -m pytest tests/test_dbms_sql_*.py           # the 408 new tests
python -m pytest                                    # everything

# frontend (from frontend/)
npm ci && npm run dev
npx tsc -b && npm run lint && npm test && npm run build
```

## Tests actually run (this environment, Python 3.12.3, SQLite 3.45.1, Node 22)

| Suite | Result |
|---|---|
| Backend, full run in six batches | **2,188 passed, 1 skipped, 0 failed** (2,189 collected; 1,781 pre-existing + 408 new). The skip is the existing `faster_whisper` import-skip: that voice dependency is not installed here. |
| Backend new DBMS tests | 408 passed (sandbox 111, algorithms and comparison 75, bank and validator 65, API 149, tools 8) |
| Existing security, final-audit, history, aptitude, DSA, voice, interview, news, profile, analytics suites | passed unchanged (history test needed the one-line `dbms_sql: 0` addition) |
| `python -m tools.verify_dbms_bank` | OK: 333 validated, 0 rejected, 50 SQL exercises and 3 MongoDB checks re-executed, 13 hostile statements rejected |
| Frontend `vitest run` | **469 passed, 32 files** (baseline 370 in 28 files; +99 new tests) |
| `tsc -b` | clean |
| `oxlint` | 0 errors, 11 warnings (identical to the baseline; none from new code) |
| `npm run build` | succeeded |

Test-quality notes: the bank validator is tested with deliberately broken questions (wrong key, duplicate options, vendor syntax
labelled standard, failing reference query, oracle disagreement, a debug starter that already works, ...), the sandbox tests were
mutation-checked as described above, and one analytics test suite was found to depend on content sizes and was fixed to derive them from the data.

**Not done, and why:** the app was not run against a real MongoDB server or a real browser here, so there was no manual visual QA
(MongoDB behaviour is exercised through `mongomock`, the UI through jsdom with an in-memory fake backend that holds the answer keys).
Responsive layout relies on the existing Tailwind breakpoints and was not checked on devices.

## Known limitations and remaining gaps

* **63% of questions are manual-review theory** (see above). Highest-priority follow-up: expert review of the 210.
* Thinnest topics (3 questions each, but all three difficulties): BCNF, Cursors, Data independence, Entity-Relationship model,
  Functions, JSON document modelling, Multivalued dependencies, Purpose and advantages of DBMS.
* The SQL editor is a plain accessible `<textarea>`; the project has no code-editor library, so there is **no syntax highlighting**.
* The practice engine is SQLite only. Execution-plan questions depend on SQLite's planner wording; they are validated at startup
  against the installed version and would be rejected (and logged) rather than served wrongly on a different planner.
* Only 6 short-answer (typed) questions; they use single-letter attributes.
* MongoDB, DynamoDB and vector-database content is theory plus a few `mongomock`-checked results; nothing runs against real MongoDB or DynamoDB.
* As with Aptitude and DSA, DBMS & SQL appears in the History Center and its own analytics, not in the cybersecurity-skills Progress page.
* Per-question time is reported by the browser, capped by server-side elapsed time.
