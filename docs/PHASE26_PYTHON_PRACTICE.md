# Phase 26: Python Interview Practice Engine

A module for Python placement and interview preparation: concepts, output prediction, tracing, debugging, code completion, coding
challenges, complexity analysis, scenario questions and defensive cybersecurity automation. Route: **`/python-practice`** (sidebar:
*Python Interview Lab*; dashboard Quick Access link). The suggested URL `/practice/python` redirects to it: the app's convention is a
top-level route per module (`/aptitude`, `/dsa`, `/dbms-sql`), and `/practice` is already the cybersecurity page.

## 1. What was inspected first

The repository was inspected before any change. Findings that shaped the design:

* There is no git history in the supplied archive, so Phase 25 (DBMS & SQL) was used as the architectural template: schemas, a validated
  seeded bank with fail-closed validation, a session service with server-side scoring and atomic idempotent completion, analytics from
  stored attempts, History Center integration, and a Zustand + service + page frontend.
* Phases 21-25 each have real implementations and tests in the repo; the baseline backend suite passed file by file (36 files verified
  before the baseline worker was interrupted) and the baseline frontend passed 469 tests, `tsc -b` and the production build.
* The project supports macOS, Linux **and Windows** without Docker. That decided the sandbox design (section 3).
* There is no code-editor dependency (Phase 25 used a plain textarea), so none was added.

## 2. What was built

* **Syllabus:** 9 units (A-I), **144 topics** (`services/python_practice/syllabus.py`). Every bullet of the supplied syllabus maps to a topic;
  a few near-duplicate bullets share one (for example "Identity versus equality" and "is versus ==") and the coverage matrix names them.
* **Question bank:** **331 validated questions** seeded idempotently into MongoDB. All 144 topics have at least 2 questions and every unit has
  easy, medium and hard questions. 289 are multiple-choice and 42 are code exercises (31 coding challenges, 6 debug, 5 completion).
  Exercise types: concept 110, output 143, scenario 24, coding 31, complexity 6, trace 6, debug 6, complete 5.
  Per-topic counts, exercise types, verification and gaps: [`python-coverage.md`](python-coverage.md) (generated from the bank).
* **14 practice modes:** topic, mixed MCQs, interview theory, predict the output, trace the code, debug the code, complete the code, coding
  challenges, complexity analysis, OOP, advanced Python, cybersecurity automation, timed mock interview, weak-topic revision. Easy / medium / hard.
* **Coding workspace:** problem statement, signature, constraints, examples, editor, **Run examples** (visible tests only), **Submit solution**
  (all tests), per-test results, progressive hints, and a reference solution with complexity and explanation after an earned reveal.
* **Analytics:** accuracy by topic, unit and difficulty; coding exercises answered and solved, submissions, trial runs, tests passed,
  solutions revealed; mock-interview results; repeated mistakes; weak topics; trend. All computed from stored, graded attempts.
* **History Center:** sessions appear under type `python_practice` with a full scored review.

## 3. Code execution: architecture and limitations

**Submitted code is never executed in the FastAPI process.** No `eval`, `exec` or in-process `subprocess` of user code exists anywhere in
the application. Execution happens in a separate OS process built by `services/python_practice/sandbox/`:

| Layer | Mechanism |
|---|---|
| Separate process, empty environment | `launcher.py` is started with `env={}`, cwd `/`, closed descriptors, its own session. No JWT secret, database URI or API key is inherited |
| Non-privileged identity | New **user namespace** mapping one id to the launcher's own unprivileged id. If the API runs as root, the supervisor first drops to `nobody` (uid 65534) |
| No capabilities | Bounding, ambient, effective, permitted and inheritable sets are all emptied; `no_new_privs` is set |
| Private filesystem | New **mount namespace** and `chroot` into a **read-only runtime image** that holds only the interpreter, loader, shared libraries and standard-library copy. No application files, `/etc`, `/home`, `/proc` or `/sys`. `/tmp` is a 2 MB tmpfs; `/work` is read-only |
| No network | New **network namespace** with no interfaces (no external and no loopback networking, no DNS) |
| Process isolation | New **PID namespace**: the program is PID 1, so killing it kills everything it started; it cannot see or signal host processes |
| Resource limits | CPU seconds, address space (384 MB), process count (12), open files, file size; core dumps off |
| Syscall filter | **seccomp** blocks namespace creation (`unshare`, `setns`, `clone` with namespace flags), `mount`, `chroot`, `pivot_root`, `ptrace`, `bpf`, keyrings, `io_uring` and similar |
| Bounded I/O | Wall-clock deadline (6 s), per-test timeout (1.5 s), 400 KB total output cap, 10,000-character source cap, at most 60 cases per run |
| Concurrency | At most 2 simultaneous runs; others wait 4 s and are then refused with a retry message |
| Cleanup | Everything lives in the namespaces and tmpfs mounts, which vanish with the process; the PID-namespace init is killed on timeout |

**Answer-key secrecy.** The sandbox receives only the submitted source and test *inputs*. Expected outputs, hidden-test labels and reference
solutions stay in the API process; the sandbox returns raw outputs and the **server** compares them. A hidden test reports pass/fail only:
never its input, expected value, printed output or error text.

**Fail closed.** On first use the runner runs a **self-test** (a hostile probe program inside the sandbox) and enables execution only if every
property holds: empty environment, no host directories visible, `/etc`, `/proc` and `/home` unreadable, read-only filesystem, no network of
any kind, no capabilities, no namespace creation, no mounting, no `chroot`, memory limit enforced, process limit enforced. If anything fails,
or the platform is not Linux, or `PYTHON_RUNNER_ENABLED=false`, the runner reports **unavailable with the reason** and:

* coding, debug and completion modes refuse to start (HTTP 409, `RUNNER_UNAVAILABLE`);
* every other mode silently excludes code exercises, so nothing ungradeable is ever served;
* the UI shows the reason and says coding exercises are turned off.

**Limitations (stated plainly).**

* **Linux only.** macOS and Windows have no equivalent namespaces, `setrlimit` or seccomp, and Docker is out of scope for this phase, so on
  those systems code exercises are disabled. Theory, output-prediction, tracing and complexity questions work everywhere.
* Linux hosts that forbid unprivileged user namespaces (for example Ubuntu with `apparmor_restrict_unprivileged_userns=1`, or hardened
  containers) will fail the self-test and run with the runner disabled, unless an administrator enables them.
* This is **kernel-level isolation, not a hypervisor**. A kernel vulnerability reachable through the allowed syscalls could in principle escape
  it; the seccomp filter is a deny-list of dangerous syscalls, not an allow-list. Do not treat it as a defence against a determined attacker with a kernel exploit. Run the API as an unprivileged user.
* Only x86_64 and aarch64 get the seccomp filter and the capability syscall; other architectures fail the self-test and disable execution.
* No cgroup memory accounting: memory is bounded by `RLIMIT_AS` and the tmpfs size, which are best-effort.
* A submitted program can forge its own result line; this cannot help because grading compares raw outputs with expected values it never sees.
* Execution is synchronous in a worker thread; a full submit of many ungraded code questions at session end can take several seconds.

**Existing policy test.** `tests/test_security.py::TestNoExecutionSurface` forbids `eval`, `exec`, `compile(`, `os.system` and `shell=True` anywhere under
`app/`. Phase 26 necessarily adds an execution surface, so that test now exempts exactly one file, `sandbox/harness.py`, whose `main()` runs only
inside the isolated runner. The API process imports that module for the pure `to_jsonable` helper only. Everything else, including the rest of this
module, is still scanned (the validation gate parses source with `ast.parse`, which compiles and runs nothing). This is a deliberate, reviewable change
to an existing guard-rail; revert the one-line allow-list to disable the module.

## 4. Question verification

* **Output / trace questions (158):** each snippet is **executed in the isolated runner** by `python -m tools.verify_python_bank --write`, and what it
  printed (or raised) must equal the stored answer. The result is stored in `content/verified.json` bound to a hash of the snippet, so editing
  a snippet un-verifies it and the validation gate rejects it until the tool is re-run. A seed cannot declare itself verified.
* **Coding / debug / complete (42):** expected outputs are **computed by running a trusted reference solution**, and an **independent**
  alternative solution must agree on every test case, or the build records a failure and the question is rejected. Every reference solution is
  also run through the sandbox, and every debug or completion starter is proven to **fail** while the reference passes.
* **Theory MCQs (131):** `manual_review`. There is no executable check; they are reported separately and never counted as verified.
  They need subject-expert sign-off before being treated as authoritative.
* Distinct options, exactly one correct, no "all of the above"; version-sensitive questions declare `python_version`; no claims of real
  company exams; **executable questions cannot use network, subprocess, `eval`/`exec` or real files**, so the cybersecurity exercises are
  offline sample data only.
* Gemini is not used. All grading is deterministic. (The brief allows optional Gemini explanations; none were added, to keep grading and content free of unverified generated text.)

The verifier caught real mistakes while the bank was written (wrong answer keys in four of my own questions, a harness bug that inherited
`from __future__ import annotations`, missing imports in displayed reference solutions, and two disagreements between reference and
alternative solutions). All were fixed rather than patched around.

## 5. Grading rules

* MCQ: stored key. Short answer: deterministic normalisation (typed output compares lines with surrounding spaces ignored).
* Code: a question is correct only when **every** test passes. Comparison: `bool` never equals `int`; `int`/`float` compare by value; list and
  tuple are interchangeable; modes `unordered`, `set_like`, `float` (tolerance), `text` (stdio) and `validator` (properties, for problems with many
  valid answers, such as rearranging a string with no adjacent repeats).
* Keywords, comments and strings never grant credit; hard-coding the visible examples fails the hidden tests.
* Revealing a reference solution before solving scores 0. It is allowed only after at least one submission or after every hint, and never in a timed mock.
* Timed mock: countdown, no feedback, no hints, no submission checks, no reveal. **Trial runs on the visible examples are allowed** (as in a real
  interview). Unchecked code is graded when the test is submitted. Expiry auto-submits.
* Completion is one atomic conditional update; attempts are unique per (session, question), so repeated or concurrent submissions never double count.

## 6. Files

**New (backend):** `app/schemas/python_practice.py`; `app/api/routes/python_practice.py` (16 routes);
`app/services/python_practice/` (`syllabus`, `bank`, `validation`, `sessions`, `analytics`, `grader`, `compare`, `verify`, `errors`,
`sandbox/{launcher,harness,image,runner}.py`, `content/{build,unit_a..unit_i,challenges,challenges_h,challenges_d,verified.json}`);
`tools/verify_python_bank.py`, `tools/python_coverage_report.py`;
tests `test_python_{sandbox,bank,grader,api}.py`.

**Modified (backend):** `core/config.py` (`python_runner_enabled`), `db/collections.py`, `api/router.py`, `main.py` (index + seed at startup),
`schemas/history.py`, `services/history/history_service.py`.

**New (frontend):** `types/pythonPractice.ts`, `services/pythonPracticeService.ts`, `store/pythonPracticeStore.ts`,
`features/python-practice/{CodeWorkbench,PracticeSetup,QuestionCard,QuestionNavigator,ResultView,SyllabusBrowser,ProgressPanel,Panels,pythonPracticeMeta}`,
`pages/PythonPractice{,Session,Result}.tsx`, tests `App.pythonPractice.test.tsx`, `store/pythonPracticeStore.test.ts`, `features/python-practice/pythonPracticeMeta.test.ts`.

**Modified (frontend):** `App.tsx`, `components/common/navigation.ts`, `features/dashboard/QuickAccessCard.tsx`, `store/sessionReset.ts`,
`types/history.ts`, `features/history/{historyMeta.ts,ActivityDetailBody.tsx}`.

**Dependencies added:** none (backend and frontend). The sandbox uses only the standard library, `ctypes` and Linux kernel features.

## 7. API (all under `/api/v1/python-practice`, all authenticated)

`GET /runner`, `GET /syllabus`, `GET /coverage`, `GET /questions` (answer-free, bounded to 50), `POST /sessions`, `GET /sessions`,
`GET /sessions/{id}`, `PUT /sessions/{id}/answers/{qid}`, `POST /sessions/{id}/questions/{qid}/{run|check|reveal|hint}`,
`POST /sessions/{id}/submit`, `GET /sessions/{id}/result`, `GET /progress`, `GET /recommendations`.
Rate limits per user: run 20/min, check 15/min, reveal 30/min, hint 60/min, create 15/min, answer 300/min. Code is capped at 10,000 characters.

## 8. Running it

```bash
# backend (from backend/)
python -m uvicorn app.main:app --reload          # seeds the Python bank at startup (idempotent)
python -m tools.verify_python_bank               # re-run every snippet and reference in the sandbox (add --write to refresh verified.json)
python -m tools.python_coverage_report           # regenerate docs/python-coverage.md
python -m pytest tests/test_python_*.py          # Phase 26 tests

# frontend (from frontend/)
npm run dev
npx tsc -b && npm test && npm run build
```

Set `PYTHON_RUNNER_ENABLED=false` to turn code execution off. After editing any output-prediction snippet, run the verifier with `--write`.

## 9. Not verified / known limitations

* **No browser testing.** The UI was exercised in jsdom (36 App-level tests, 28 store/meta tests) and type-checked and built, but I did not open it in
  a real browser, so responsive layout on phone and desktop is built with the existing Tailwind patterns and **not visually verified**.
* **No syntax highlighting.** No editor library exists in the project and none was added (the brief allows this); the editor is an accessible textarea.
* **Coverage is the minimum, not depth.** 331 questions is 2 or more per topic. Hard questions are thin in Units A, B, C and E, and 20 topics have only
  manual-review questions (see `python-coverage.md` "Gaps"). Treat the bank as a solid, verified base to expand, not a finished corpus.
* **131 theory MCQs are not machine-verified.** They were written carefully and four wrong keys in *executable* questions were caught by the verifier,
  but the theory keys have no equivalent safety net. Have a Python expert review them.
* **Sandbox verified on Linux only** (Ubuntu 24.04, kernel 6.18, both as root-dropped-to-nobody and as an unprivileged user). Other kernels, distributions
  with AppArmor user-namespace restrictions, and non-x86_64/aarch64 architectures were not tested; they should fail the self-test and disable execution.
* Gemini is not used (optional per the brief).
