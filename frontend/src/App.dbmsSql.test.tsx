// @vitest-environment jsdom
/**
 * Phase 25 UI tests. The REAL <App /> (routes, guards, layout, DBMS & SQL pages, store, service) runs in jsdom; only HTTP is faked, by an
 * in-memory backend that keeps its own answer key, reference query and expected rows. That lets the tests prove what the browser sends
 * (never a score, user id, correctness flag or answer key) and what it shows at each stage (no answer, explanation or reference
 * solution before it is earned), including SQL editor interactions, result tables, loading, empty, error and completion states.
 */
import { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter, useLocation } from "react-router-dom";
import { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "@/App";
import { api } from "@/services/api";
import { clearStoredToken } from "@/services/tokenStorage";
import { useAuthStore } from "@/store/authStore";
import { useDbmsSqlStore } from "@/store/dbmsSqlStore";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const SID = "e".repeat(24);
const QIDS = ["dbq-0000000001", "dbq-0000000002", "dbq-0000000003"];
const KEY = 2; // displayed correct option of the MCQ: the fake server's secret
const MCQ_EXPLANATION = "SECRET_EXPLANATION: a candidate key is a minimal superkey.";
const REFERENCE = "SELECT name FROM employees WHERE salary IS NULL ORDER BY name";
const EXPECTED = { columns: ["name"], rows: [["Neha"]], row_count: 1, truncated: false };
const SQL_EXPLANATION = "IS NULL is the way to test for missing values.";
const HINTS = ["Which operator tests for NULL?", "Remember: = NULL is never true."];

interface Fake {
  syllabusStatus: number;
  syllabusDelayMs: number;
  totalQuestions: number;
  progress: "empty" | "data";
  mode: "sql_lab" | "timed_mock";
  answers: Record<string, { selected: number | null; text: string | null; sql: string | null; marked: boolean; locked: boolean; solved: boolean; revealed: boolean; checks: number; hints: number }>;
  status: "in_progress" | "completed";
  failAnswers: false | { status: number; code: string };
  resultStatus: number;
  datasetStatus: number;
  sandboxStatus: number;
}
let fake: Fake;
let requests: { method: string; url: string; body: Record<string, unknown> | undefined }[] = [];
let root: Root;
let container: HTMLDivElement;
let lastPath = "";

const fresh = (): Fake => ({ syllabusStatus: 200, syllabusDelayMs: 0, totalQuestions: 300, progress: "empty", mode: "sql_lab", answers: {}, status: "in_progress", failAnswers: false, resultStatus: 200, datasetStatus: 200, sandboxStatus: 200 });
const blank = () => ({ selected: null, text: null, sql: null, marked: false, locked: false, solved: false, revealed: false, checks: 0, hints: 0 });

const topic = (id: string, title: string, n: number, status: string) => ({ id, title, question_count: n, by_difficulty: { easy: 1, medium: 1, hard: 1 }, by_format: { concept: 2, query: 1 }, by_interaction: n ? { mcq: 2, sql: 1 } : {}, status });
const SYLLABUS = (total: number) => ({
  units: [
    { id: "unit-a", code: "A", title: "Introduction to databases", summary: "Why DBMS exists.", question_count: total ? 27 : 0, topics_implemented: total ? 1 : 0, topics_total: 2, topics: [topic("purpose-advantages", "Purpose and advantages of DBMS", total ? 3 : 0, total ? "implemented" : "missing"), topic("er-model", "Entity-Relationship model", total ? 1 : 0, total ? "partial" : "missing")] },
    { id: "unit-b", code: "B", title: "Relational query language", summary: "SQL command families.", question_count: total ? 31 : 0, topics_implemented: total ? 1 : 0, topics_total: 1, topics: [topic("keys", "Primary, foreign, candidate, super, and composite keys", total ? 5 : 0, total ? "implemented" : "missing")] },
    { id: "unit-d", code: "D", title: "Relational database design", summary: "Normal forms.", question_count: total ? 40 : 0, topics_implemented: 0, topics_total: 0, topics: [] },
  ],
  question_total: total, min_questions_per_topic: 3, topics_implemented: total ? 2 : 0, topics_total: 3,
  sql_engine: { engine: "SQLite", version: "3.45.1", window_functions: true, right_full_join: true, dialect: "sqlite", read_only: true, limits: { max_sql_chars: 4000, max_rows: 200, max_seconds: 1.5, supported_statements: ["SELECT"] } },
});

const DATASET = {
  id: "practice", title: "Company & shop practice data", description: "Six small tables with realistic edge cases.", ddl: "CREATE TABLE employees (...)",
  indexes: [{ name: "idx_employees_dept", table: "employees", sql: "CREATE INDEX ..." }],
  tables: [
    { name: "employees", description: "Staff.", row_count: 2, columns: [{ name: "emp_id", type: "INTEGER", primary_key: true, not_null: true, references: null }, { name: "name", type: "TEXT", primary_key: false, not_null: true, references: null }, { name: "dept_id", type: "INTEGER", primary_key: false, not_null: false, references: "departments.dept_id" }], rows: [[1, "Asha", 1], [14, "Neha", null]] },
    { name: "departments", description: "Departments.", row_count: 1, columns: [{ name: "dept_id", type: "INTEGER", primary_key: true, not_null: true, references: null }], rows: [[1]] },
  ],
};

const baseQ = { unit_id: "unit-b", dialect: "standard", est_time_seconds: 60, tags: [] };
const questionsPublic = () => [
  { ...baseQ, question_id: QIDS[0], topic_id: "keys", format: "design", interaction: "mcq", difficulty: "easy", statement: "Fake DBMS question 1: what are the candidate keys of R?", code: null, dataset_id: null,
    options: ["{B}", "{A, B}", "{A}", "{D}"], short: null, sql: null },
  { ...baseQ, unit_id: "unit-d", question_id: QIDS[1], topic_id: "functional-dependencies", format: "design", interaction: "short", difficulty: "medium", statement: "Fake DBMS question 2: compute the closure of {A} for A->B, B->C.", code: null, dataset_id: null,
    options: [], short: { kind: "attrs", help: "Type the attributes as letters, e.g. ABC." }, sql: null },
  { ...baseQ, dialect: "sqlite", question_id: QIDS[2], topic_id: "null-constraint-violations", format: "query", interaction: "sql", difficulty: "easy", statement: "Fake DBMS question 3: return the names of employees with no salary.", code: null, dataset_id: "practice",
    options: [], short: null, sql: { dataset_id: "practice", starter: null, ordered: false, check_column_names: false, expected_columns: ["name"] } },
];

function feedbackFor(i: number) {
  const a = fake.answers[QIDS[i]] ?? blank();
  if (i === 0) return { kind: "mcq", is_correct: a.selected === KEY, correct_index: KEY, explanation: MCQ_EXPLANATION };
  if (i === 1) return { kind: "short", is_correct: a.solved, answer: "{A, B, C}", explanation: "A reaches B then C." };
  return { kind: "sql", is_correct: a.solved, revealed: a.revealed, reference_sql: REFERENCE, expected: EXPECTED, explanation: SQL_EXPLANATION };
}

function sessionPayload() {
  const now = Date.now();
  const exam = fake.mode === "timed_mock";
  return {
    session_id: SID, mode: fake.mode, status: fake.status, difficulty: null, question_count: 3, requested_count: 3, unit_ids: ["unit-b"], topic_ids: ["keys"],
    immediate_feedback: !exam, exam_mode: exam, started_at: new Date(now).toISOString(), expires_at: exam ? new Date(now + 1_800_000).toISOString() : null,
    server_time: new Date(now).toISOString(), remaining_seconds: exam ? 1800 : null, timer_minutes: exam ? 30 : null, scoring_policy: "Each correct answer scores 1 mark.",
    questions: questionsPublic().map((q, i) => {
      const a = fake.answers[QIDS[i]] ?? blank();
      return { ...q, selected_index: a.selected, text_answer: a.text, sql_answer: a.sql, marked_for_review: a.marked, locked: a.locked, checks: a.checks,
        hints_total: exam ? 0 : i === 2 ? 2 : 0, hints_used: exam ? 0 : a.hints, hints: exam ? [] : HINTS.slice(0, a.hints), last_check: null,
        feedback: a.locked && !exam ? feedbackFor(i) : null };
    }),
  };
}

function resultPayload() {
  const a = (i: number) => fake.answers[QIDS[i]] ?? blank();
  const outcomes = [a(0).selected === null ? "unanswered" : a(0).selected === KEY ? "correct" : "incorrect", a(1).text ? (a(1).solved ? "correct" : "incorrect") : "unanswered",
    a(2).solved ? "correct" : a(2).revealed || a(2).sql ? "incorrect" : "unanswered"];
  const pub = questionsPublic();
  const correct = outcomes.filter((o) => o === "correct").length;
  const incorrect = outcomes.filter((o) => o === "incorrect").length;
  return {
    session_id: SID, mode: fake.mode, status: "completed", total_questions: 3, correct, incorrect, unanswered: 3 - correct - incorrect, score: correct, accuracy: Math.round((correct / 3) * 1000) / 10,
    time_taken_seconds: 95, average_seconds_per_question: 31.7, auto_submitted: false, started_at: new Date().toISOString(), finished_at: new Date().toISOString(),
    topic_performance: [{ topic_id: "keys", topic_title: "Primary, foreign, candidate, super, and composite keys", unit_id: "unit-b", total: 3, correct, incorrect, unanswered: 3 - correct - incorrect, accuracy: 33.3 }],
    revision_topics: correct < 3 ? [{ topic_id: "keys", topic_title: "Primary, foreign, candidate, super, and composite keys", accuracy: 33.3 }] : [], scoring_policy: "Each correct answer scores 1 mark.",
    questions: pub.map((q, i) => ({
      ...q, selected_index: a(i).selected, correct_index: i === 0 ? KEY : null, outcome: outcomes[i], explanation: i === 0 ? MCQ_EXPLANATION : i === 1 ? "A reaches B then C." : SQL_EXPLANATION, marked_for_review: a(i).marked, time_spent_seconds: 5,
      hints_used: a(i).hints, text_answer: a(i).text, sql_answer: a(i).sql, sql_checks: a(i).checks, revealed: a(i).revealed, note: a(i).revealed && !a(i).solved ? "Solution revealed before it was solved." : null,
      verdict: i === 2 && outcomes[2] === "incorrect" && a(2).sql ? { code: "row_count", messages: ["Your query returned 3 row(s); the expected result has 1."] } : null,
      actual: i === 2 && outcomes[2] === "incorrect" && a(2).sql ? { columns: ["name"], rows: [["Asha"], ["Neha"], ["Bilal"]], row_count: 3, truncated: false } : null,
      correct_answer: i === 1 ? "{A, B, C}" : null, reference_sql: i === 2 ? REFERENCE : null, expected: i === 2 ? EXPECTED : null,
    })),
  };
}

const PROGRESS = () => fake.progress === "empty"
  ? { sessions_completed: 0, questions_presented: 0, questions_answered: 0, correct: 0, incorrect: 0, unanswered: 0, accuracy: 0, average_seconds_per_answered_question: null, topic_accuracy: [], unit_accuracy: [], difficulty_accuracy: [],
      sql: { questions_answered: 0, queries_checked: 0, solved: 0, solutions_revealed: 0, success_rate: 0 }, mock_interviews: [], recent_sessions: [], trend: [], improvement_points: null, weak_topics: [], repeated_mistakes: [] }
  : { sessions_completed: 3, questions_presented: 30, questions_answered: 27, correct: 12, incorrect: 15, unanswered: 3, accuracy: 44.4, average_seconds_per_answered_question: 41,
      topic_accuracy: [{ topic_id: "joins", topic_title: "INNER, LEFT, RIGHT, and other supported joins", unit_id: "unit-c", answered: 12, correct: 3, presented: 12, accuracy: 25 }],
      unit_accuracy: [{ unit_id: "unit-c", unit_title: "Relational operations and advanced SQL", answered: 12, correct: 3, accuracy: 25 }], difficulty_accuracy: [{ difficulty: "easy", answered: 27, correct: 12, accuracy: 44.4 }],
      sql: { questions_answered: 8, queries_checked: 21, solved: 3, solutions_revealed: 2, success_rate: 37.5 },
      mock_interviews: [{ session_id: SID, score: 9, total: 20, accuracy: 45, time_taken_seconds: 900, finished_at: new Date().toISOString() }],
      recent_sessions: [{ session_id: SID, mode: "timed_mock", score: 9, total: 20, accuracy: 45, time_taken_seconds: 900, finished_at: new Date().toISOString() }], trend: [], improvement_points: null,
      weak_topics: [{ topic_id: "joins", topic_title: "INNER, LEFT, RIGHT, and other supported joins", unit_id: "unit-c", answered: 12, correct: 3, accuracy: 25, reason: "25% accuracy over 12 answered questions (below 60%)." }],
      repeated_mistakes: [{ question_id: "dbq-ffffffffff", topic_id: "joins", topic_title: "INNER, LEFT, RIGHT, and other supported joins", times_incorrect: 3 }] };

function respond(config: InternalAxiosRequestConfig, data: unknown, status = 200) {
  const response = { data, status, statusText: "", headers: {}, config };
  if (status >= 400) throw new AxiosError("fail", "ERR_BAD_RESPONSE", config, null, response as never);
  return response;
}
const ok = (data: unknown) => ({ success: true, message: "ok", data });
const err = (message: string, error_code: string) => ({ success: false, message, error_code });

async function handler(config: InternalAxiosRequestConfig) {
  const url = config.url ?? "";
  const method = (config.method ?? "get").toLowerCase();
  const body = typeof config.data === "string" ? JSON.parse(config.data) : config.data;
  requests.push({ method, url, body });
  const U = "/dbms-sql";
  if (url === `${U}/syllabus` && fake.syllabusDelayMs) await new Promise((r) => setTimeout(r, fake.syllabusDelayMs));
  if (url === `${U}/syllabus`) return fake.syllabusStatus === 200 ? respond(config, ok(SYLLABUS(fake.totalQuestions))) : respond(config, err("Syllabus service is down.", "SERVICE_UNAVAILABLE"), fake.syllabusStatus);
  if (url === `${U}/datasets/practice`) return fake.datasetStatus === 200 ? respond(config, ok(DATASET)) : respond(config, err("Sample tables are unavailable.", "SERVICE_UNAVAILABLE"), fake.datasetStatus);
  if (url === `${U}/progress`) return respond(config, ok(PROGRESS()));
  if (url === `${U}/recommendations`) return respond(config, ok({ has_history: fake.progress === "data", weak_topics: PROGRESS().weak_topics, incorrect_question_count: fake.progress === "data" ? 4 : 0, repeated_mistake_count: 0, message: fake.progress === "data" ? "1 topic(s) need revision." : "Complete a few practice sessions first; recommendations are based only on your recorded answers.", thresholds: { min_answered: 5, accuracy_below: 60 } }));
  if (method === "post" && url === `${U}/sandbox/run`) {
    if (fake.sandboxStatus !== 200) return respond(config, err("Too many requests.", "RATE_LIMITED"), fake.sandboxStatus);
    const sql = String((body as { sql: string }).sql);
    if (/drop|delete|sqlite_master/i.test(sql)) return respond(config, ok({ ok: false, columns: [], rows: [], row_count: 0, truncated: false, elapsed_ms: 1, error: { kind: "not_allowed", message: "DROP is not allowed in the practice sandbox. Only read-only SELECT queries can be run." } }));
    return respond(config, ok({ ok: true, columns: ["name"], rows: [["Asha"], ["Neha"], [null]], row_count: 3, truncated: false, elapsed_ms: 2, error: null }));
  }
  if (method === "post" && url === `${U}/sessions`) return respond(config, ok(sessionPayload()), 201);
  if (method === "get" && url === `${U}/sessions/${SID}`) return respond(config, ok(sessionPayload()));
  if (method === "put" && url.startsWith(`${U}/sessions/${SID}/answers/`)) {
    if (fake.failAnswers) return respond(config, err("Answer rejected.", fake.failAnswers.code), fake.failAnswers.status);
    const qid = url.split("/").pop()!;
    const i = QIDS.indexOf(qid);
    const b = body as { selected_index?: number | null; text?: string | null; sql?: string | null; marked_for_review: boolean };
    const prev = fake.answers[qid] ?? blank();
    const locked = fake.mode === "sql_lab" && i === 0 && b.selected_index !== null && b.selected_index !== undefined;
    fake.answers[qid] = { ...prev, selected: i === 0 ? (b.selected_index ?? null) : null, text: i === 1 ? (b.text ?? null) : null, sql: i === 2 ? (b.sql ?? null) : null, marked: b.marked_for_review, locked };
    return respond(config, ok({ question_id: qid, selected_index: fake.answers[qid].selected, marked_for_review: b.marked_for_review, locked, feedback: locked ? feedbackFor(i) : null, remaining_seconds: 100 }));
  }
  if (method === "post" && url.endsWith("/check")) {
    const qid = url.split("/").slice(-2)[0];
    const i = QIDS.indexOf(qid);
    const b = body as { sql?: string; text?: string };
    const prev = fake.answers[qid] ?? blank();
    if (i === 1) {
      const correct = (b.text ?? "").toUpperCase().replace(/[^A-Z]/g, "") === "ABC";
      fake.answers[qid] = { ...prev, text: b.text ?? null, locked: true, solved: correct, checks: prev.checks + 1 };
      return respond(config, ok({ question_id: qid, kind: "short", correct, locked: true, checks: prev.checks + 1, feedback: feedbackFor(1), remaining_seconds: 100 }));
    }
    const correct = String(b.sql).trim() === REFERENCE;
    fake.answers[qid] = { ...prev, sql: b.sql ?? null, locked: correct, solved: correct, checks: prev.checks + 1 };
    const run = { ok: true, columns: ["name"], rows: correct ? [["Neha"]] : [["Asha"], ["Neha"], ["Bilal"]], row_count: correct ? 1 : 3, truncated: false, elapsed_ms: 2, error: null };
    return respond(config, ok({ question_id: qid, kind: "sql", correct, locked: correct, checks: prev.checks + 1,
      verdict: { code: correct ? "correct" : "row_count", messages: correct ? ["Your result matches the expected result."] : ["Your query returned 3 row(s); the expected result has 1 (more than expected).", "Possible cause: no filter. Is a WHERE or HAVING condition needed?"] },
      run, comparison: { expected: EXPECTED, actual: { columns: ["name"], rows: run.rows, row_count: run.row_count, truncated: false } }, feedback: correct ? feedbackFor(2) : null, remaining_seconds: 100 }));
  }
  if (method === "post" && url.endsWith("/hint")) {
    const qid = url.split("/").slice(-2)[0];
    const prev = fake.answers[qid] ?? blank();
    fake.answers[qid] = { ...prev, hints: prev.hints + 1 };
    return respond(config, ok({ question_id: qid, hint: HINTS[prev.hints], hint_number: prev.hints + 1, hints_total: 2, hints: HINTS.slice(0, prev.hints + 1) }));
  }
  if (method === "post" && url.endsWith("/reveal")) {
    const qid = url.split("/").slice(-2)[0];
    fake.answers[qid] = { ...(fake.answers[qid] ?? blank()), locked: true, revealed: true };
    return respond(config, ok({ question_id: qid, locked: true, feedback: feedbackFor(2), remaining_seconds: 100 }));
  }
  if (method === "post" && url === `${U}/sessions/${SID}/submit`) { fake.status = "completed"; return respond(config, ok(resultPayload())); }
  if (method === "get" && url === `${U}/sessions/${SID}/result`) return fake.resultStatus === 200 ? respond(config, ok(resultPayload())) : respond(config, err("Results are available after the session is submitted.", "SESSION_NOT_FINISHED"), fake.resultStatus);
  return respond(config, err("Not available in tests.", "NOT_FOUND"), 404);
}

function Probe() {
  const { pathname } = useLocation();
  useEffect(() => { lastPath = pathname; }, [pathname]);
  return null;
}
const text = () => container.textContent ?? "";
async function waitFor(check: () => boolean, ms = 4000) {
  const start = Date.now();
  while (!check()) {
    if (Date.now() - start > ms) throw new Error(`Timed out. Path=${lastPath}. DOM:\n${text().slice(0, 700)}`);
    await act(async () => { await new Promise((r) => setTimeout(r, 20)); });
  }
}
async function visit(path: string) { await act(async () => { root.render(<MemoryRouter key={path} initialEntries={[path]}><App /><Probe /></MemoryRouter>); }); }
const click = (el: Element | null | undefined) => { if (!el) throw new Error("element not found"); return act(async () => { (el as HTMLElement).click(); }); };
const byText = (sel: string, t: string | RegExp) => [...container.querySelectorAll(sel)].find((e) => (typeof t === "string" ? e.textContent?.includes(t) : t.test(e.textContent ?? ""))) as HTMLElement | undefined;
const option = (n: number) => container.querySelectorAll<HTMLElement>('[role="radiogroup"][aria-labelledby="question-heading"] [role="radio"]')[n];
const puts = () => requests.filter((r) => r.method === "put");
const posts = (suffix: string) => requests.filter((r) => r.method === "post" && r.url.endsWith(suffix));
const key = (k: string) => act(async () => { window.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true })); });
const navButton = (n: number) => container.querySelector<HTMLElement>(`nav[aria-label="Question navigator"] ol li:nth-child(${n}) button`)!;
const editor = () => container.querySelector<HTMLTextAreaElement>(`textarea[id^="sql-"]`)!;

async function typeInto(el: HTMLTextAreaElement | HTMLInputElement, value: string) {
  await act(async () => {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value")!.set!.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function startSession(mode: Fake["mode"] = "sql_lab") {
  fake.mode = mode;
  await visit("/dbms-sql");
  await waitFor(() => text().includes("Practice mode"));
  await click(byText('[role="radio"]', mode === "timed_mock" ? "Timed mock interview" : "SQL query lab"));
  await click(byText("button", "Start"));
  await waitFor(() => lastPath === `/dbms-sql/session/${SID}` && text().includes("Question 1 of 3"));
}
const goTo = async (n: number) => { await click(navButton(n)); await waitFor(() => text().includes(`Question ${n} of 3`)); };

beforeEach(() => {
  fake = fresh();
  requests = [];
  lastPath = "";
  window.scrollTo = vi.fn();
  window.matchMedia = window.matchMedia ?? ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, onchange: null, dispatchEvent: () => false }) as MediaQueryList);
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
  (window.HTMLElement.prototype as unknown as { animate: unknown }).animate = vi.fn(() => ({ cancel() {}, finished: Promise.resolve() }));
  (globalThis as Record<string, unknown>).ResizeObserver ??= class { observe() {} unobserve() {} disconnect() {} };
  (globalThis as Record<string, unknown>).IntersectionObserver ??= class { observe() {} unobserve() {} disconnect() {} takeRecords() { return []; } };
  api.defaults.adapter = handler as never;
  useAuthStore.setState({ isAuthenticated: true, user: { id: "u1", name: "Ada Lovelace", email: "ada@example.com" }, accessToken: "tok", isLoading: false, loadCurrentUser: async () => undefined });
  useDbmsSqlStore.getState().reset();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  clearStoredToken();
  vi.restoreAllMocks();
});

describe("module navigation and states", () => {
  it("shows a loading state, then all twelve practice modes", async () => {
    fake.syllabusDelayMs = 150;
    await visit("/dbms-sql");
    await waitFor(() => !!container.querySelector('[role="status"][aria-label="Loading practice options"]'));
    await waitFor(() => text().includes("Practice mode"));
    const modes = [...container.querySelectorAll('[role="radiogroup"][aria-label="Practice mode"] [role="radio"]')].map((b) => b.textContent ?? "");
    expect(modes).toHaveLength(12);
    for (const t of ["Topic practice", "Mixed practice", "Technical interview", "SQL query lab", "Predict the output", "Debug the query", "Complete the query", "Database design lab", "Transaction scenario lab", "NoSQL & MongoDB lab", "Timed mock interview", "Weak topics"]) {
      expect(modes.some((m) => m.includes(t))).toBe(true);
    }
    expect(container.querySelector("h1")?.textContent).toContain("DBMS & SQL Interview Lab");
    expect(text()).toContain("no negative marking");
  });

  it("appears in the sidebar and the suggested /practice/dbms-sql URL redirects to the module", async () => {
    await visit("/practice/dbms-sql");
    await waitFor(() => text().includes("Practice mode"));
    expect(lastPath).toBe("/dbms-sql");
    expect([...container.querySelectorAll("a")].some((a) => a.getAttribute("href") === "/dbms-sql" && a.textContent?.includes("DBMS & SQL Lab"))).toBe(true);
  });

  it("shows an error with a working retry when the syllabus cannot load", async () => {
    fake.syllabusStatus = 503;
    await visit("/dbms-sql");
    await waitFor(() => text().includes("Syllabus service is down."));
    expect(container.querySelector('[role="alert"]')).not.toBeNull();
    fake.syllabusStatus = 200;
    await click(byText("button", "Retry"));
    await waitFor(() => text().includes("Practice mode"));
  });

  it("shows an honest empty state when the bank has no questions", async () => {
    fake.totalQuestions = 0;
    await visit("/dbms-sql");
    await waitFor(() => text().includes("No questions are available yet"));
    expect(container.querySelector('[role="radiogroup"][aria-label="Practice mode"]')).toBeNull();
  });

  it("the syllabus tab reports real coverage and links to topic practice", async () => {
    await visit("/dbms-sql?tab=syllabus");
    await waitFor(() => text().includes("topics have at least 3 questions"));
    expect(text()).toContain("Unit A: Introduction to databases");
    expect(text()).toContain("2 of 3");
    expect(byText("li", "Entity-Relationship model")!.textContent).toContain("Few questions");
    expect(text()).toContain("SQLite 3.45.1");
    const link = container.querySelector<HTMLAnchorElement>('a[aria-label="Practise Primary, foreign, candidate, super, and composite keys"]');
    expect(link?.getAttribute("href")).toContain("/dbms-sql?mode=topic&topic=keys");
  });

  it("the syllabus tab has an error state with retry", async () => {
    fake.syllabusStatus = 500;
    await visit("/dbms-sql?tab=syllabus");
    await waitFor(() => text().includes("Syllabus service is down."));
    fake.syllabusStatus = 200;
    await click(byText("button", "Retry"));
    await waitFor(() => text().includes("Unit A"));
  });
});

describe("topic and difficulty selection", () => {
  it("topic practice needs a topic and then sends the chosen topic, difficulty and count, nothing else", async () => {
    await visit("/dbms-sql");
    await waitFor(() => text().includes("Practice mode"));
    await click(byText("button", "Start"));
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("Choose at least one topic");
    expect(requests.some((r) => r.method === "post" && r.url === "/dbms-sql/sessions")).toBe(false);

    await click(byText("summary", "Relational query language")!);
    await click(container.querySelector('input[type="checkbox"][class]:not([aria-label])') as Element); // first topic checkbox in the opened unit
    await click(byText('[role="radio"]', "Hard"));
    await click(byText("button", "Start"));
    await waitFor(() => lastPath.startsWith("/dbms-sql/session/"));
    const sent = requests.find((r) => r.method === "post" && r.url === "/dbms-sql/sessions")!.body!;
    expect(sent).toMatchObject({ mode: "topic", difficulty: "hard", question_count: 10, immediate_feedback: true });
    expect((sent.topic_ids as string[]).length).toBe(1);
    expect(Object.keys(sent).sort()).toEqual(["difficulty", "immediate_feedback", "mode", "question_count", "topic_ids"]);
  });

  it("deep link from the syllabus pre-selects the topic", async () => {
    await visit("/dbms-sql?mode=topic&topic=keys");
    await waitFor(() => text().includes("Practice mode"));
    expect(container.querySelector<HTMLInputElement>('input[type="checkbox"]:checked')).not.toBeNull();
    await click(byText("button", "Start"));
    await waitFor(() => lastPath.startsWith("/dbms-sql/session/"));
    expect(requests.find((r) => r.url === "/dbms-sql/sessions")!.body).toMatchObject({ mode: "topic", topic_ids: ["keys"] });
  });

  it("the timed mock requires a time limit and sends it; the lab modes fix their own scope", async () => {
    await visit("/dbms-sql");
    await waitFor(() => text().includes("Practice mode"));
    await click(byText('[role="radio"]', "Timed mock interview"));
    expect(container.querySelector<HTMLInputElement>("#dbms-timer")).not.toBeNull();
    expect(text()).not.toContain("Check answers as I go");
    await click(byText('[role="radio"]', "Database design lab"));
    expect(container.querySelector('fieldset legend')?.textContent ?? "").toContain("Practice mode");
    expect(text()).not.toContain("Scope");
    await click(byText('[role="radio"]', "Timed mock interview"));
    await click(byText("button", "Start"));
    await waitFor(() => lastPath.startsWith("/dbms-sql/session/"));
    const body = requests.find((r) => r.url === "/dbms-sql/sessions")!.body!;
    expect(body).toMatchObject({ mode: "timed_mock", question_count: 20 });
    expect(typeof body.timer_minutes).toBe("number");
    expect(body).not.toHaveProperty("immediate_feedback");
  });

  it("rejects an out-of-range question count before calling the server", async () => {
    await visit("/dbms-sql?mode=mixed");
    await waitFor(() => text().includes("Practice mode"));
    await typeInto(container.querySelector("#dbms-count")!, "99");
    await click(byText("button", "Start"));
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("between 1 and 50");
    expect(requests.some((r) => r.url === "/dbms-sql/sessions")).toBe(false);
  });
});

describe("answering multiple-choice questions", () => {
  it("sends only the option position, then shows feedback and locks", async () => {
    await startSession();
    expect(text()).not.toContain("SECRET_EXPLANATION");
    expect(container.querySelector('[aria-label="Hints"]')).toBeNull();
    await click(option(KEY));
    await waitFor(() => text().includes("SECRET_EXPLANATION"));
    const body = puts().at(-1)!.body!;
    expect(body).toMatchObject({ selected_index: KEY });
    expect(Object.keys(body).sort()).toEqual(["marked_for_review", "selected_index", "time_spent_seconds"]);
    expect(option(KEY).className).toContain("border-success");
    expect(text()).toContain("Correct");
    const before = puts().length;
    await click(option(0));
    expect(puts().length).toBe(before);
  });

  it("marks a wrong pick and shows the right option", async () => {
    await startSession();
    await click(option(0));
    await waitFor(() => text().includes("Not quite"));
    expect(option(0).className).toContain("border-danger");
    expect(option(KEY).className).toContain("border-success");
  });

  it("keyboard shortcuts answer and navigate", async () => {
    await startSession();
    await key("c");
    await waitFor(() => puts().length > 0);
    expect(puts().at(-1)!.body).toMatchObject({ selected_index: 2 });
    await key("ArrowRight");
    await waitFor(() => text().includes("Question 2 of 3"));
    await key("m");
    await waitFor(() => puts().some((p) => p.body?.marked_for_review === true));
  });

  it("shows an error and reverts the selection when saving fails, and sends the user to the result if the session ended", async () => {
    await startSession("timed_mock");
    fake.failAnswers = { status: 500, code: "SERVER_ERROR" };
    await click(option(1));
    await waitFor(() => !!container.querySelector('[role="alert"]'));
    expect(option(1).getAttribute("aria-checked")).toBe("false");
    fake.failAnswers = { status: 409, code: "SESSION_EXPIRED" };
    await click(option(0));
    await waitFor(() => lastPath === `/dbms-sql/result/${SID}`);
  });
});

describe("short answers", () => {
  it("checks a short answer on the server and shows the canonical answer", async () => {
    await startSession();
    await goTo(2);
    const input = container.querySelector<HTMLInputElement>(`input[id^="short-"]`)!;
    expect(text()).toContain("Type the attributes as letters");
    await typeInto(input, "cba");
    await click(byText("button", "Check answer"));
    await waitFor(() => text().includes("Correct answer:"));
    expect(posts("/check").at(-1)!.body).toEqual({ text: "cba", time_spent_seconds: expect.any(Number) });
    expect(text()).toContain("{A, B, C}");
    expect(container.querySelector<HTMLInputElement>(`input[id^="short-"]`)!.disabled).toBe(true);
  });

  it("a wrong short answer also locks and reveals the answer", async () => {
    await startSession();
    await goTo(2);
    await typeInto(container.querySelector(`input[id^="short-"]`)!, "AB");
    await click(byText("button", "Check answer"));
    await waitFor(() => text().includes("Not quite"));
  });

  it("the check button is disabled until something is typed", async () => {
    await startSession();
    await goTo(2);
    expect((byText("button", "Check answer") as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("SQL editor interactions", () => {
  async function toSql() { await startSession(); await goTo(3); }

  it("shows the task, expected columns and an accessible editor", async () => {
    await toSql();
    expect(editor()).not.toBeNull();
    expect(container.querySelector(`label[for="${editor().id}"]`)?.textContent).toContain("SQL query");
    expect(text()).toContain("Return column: name");
    expect(text()).toContain("row order does not matter");
    expect(text()).toContain("SQLite");
    expect(text()).not.toContain(REFERENCE);
  });

  it("Run query sends the SQL to the sandbox and renders the result table with NULL shown in words", async () => {
    await toSql();
    await typeInto(editor(), "SELECT name FROM employees");
    await click(byText("button", "Run query"));
    await waitFor(() => !!container.querySelector("table"));
    expect(requests.find((r) => r.url === "/dbms-sql/sandbox/run")!.body).toEqual({ sql: "SELECT name FROM employees", dataset_id: "practice" });
    const table = container.querySelector("table")!;
    expect(table.querySelector("caption")?.textContent).toBe("Your query result");
    expect([...table.querySelectorAll('th[scope="col"]')].map((h) => h.textContent)).toEqual(["name"]);
    expect([...table.querySelectorAll("tbody td")].map((c) => c.textContent)).toEqual(["Asha", "Neha", "NULL"]);
    expect(text()).toContain("3 rows");
  });

  it("Ctrl+Enter runs the query", async () => {
    await toSql();
    await typeInto(editor(), "SELECT 1");
    await act(async () => { editor().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", ctrlKey: true, bubbles: true })); });
    await waitFor(() => requests.some((r) => r.url === "/dbms-sql/sandbox/run"));
  });

  it("explains a rejected statement in plain language", async () => {
    await toSql();
    await typeInto(editor(), "DROP TABLE employees");
    await click(byText("button", "Run query"));
    await waitFor(() => text().includes("Not allowed in the practice sandbox"));
    expect(text()).toContain("Only read-only SELECT queries can be run");
    expect(container.querySelector("table")).toBeNull();
  });

  it("an empty query is refused locally without calling the server", async () => {
    await toSql();
    await click(byText("button", "Run query"));
    await waitFor(() => text().includes("Write a query first."));
    expect(requests.some((r) => r.url === "/dbms-sql/sandbox/run")).toBe(false);
  });

  it("a wrong answer shows feedback with expected-versus-yours tables and allows a retry", async () => {
    await toSql();
    await typeInto(editor(), "SELECT name FROM employees");
    await click(byText("button", "Check answer"));
    await waitFor(() => text().includes("Not matching yet"));
    expect(text()).toContain("Possible cause: no filter");
    expect(container.querySelector('table caption')).not.toBeNull();
    expect([...container.querySelectorAll("caption")].map((c) => c.textContent)).toEqual(expect.arrayContaining(["Expected result", "Your result"]));
    expect(text()).not.toContain(REFERENCE);
    expect(text()).toContain("1 check");
    expect(editor().disabled).toBe(false);
    expect(posts("/check").at(-1)!.body).toMatchObject({ sql: "SELECT name FROM employees" });
  });

  it("hints are requested one at a time and persist", async () => {
    await toSql();
    await click(byText("button", "Show a hint"));
    await waitFor(() => text().includes(HINTS[0]));
    expect(text()).not.toContain(HINTS[1]);
    await click(byText("button", "Show another hint"));
    await waitFor(() => text().includes(HINTS[1]));
    expect(posts("/hint")).toHaveLength(2);
    expect(byText("button", "another hint")).toBeUndefined();
  });

  it("a correct query locks the editor and reveals the reference solution and explanation", async () => {
    await toSql();
    await typeInto(editor(), REFERENCE);
    await click(byText("button", "Check answer"));
    await waitFor(() => text().includes("Reference solution"));
    expect(text()).toContain("Correct: your result matches");
    expect(text()).toContain(SQL_EXPLANATION);
    expect(editor().disabled).toBe(true);
    expect(byText("button", "Check answer")).toBeUndefined();
  });

  it("Show solution reveals the reference, locks the question and warns it scores 0", async () => {
    await toSql();
    expect(text()).toContain("scores this question 0");
    await click(byText("button", "Show solution"));
    await waitFor(() => text().includes("Solution revealed (this question scores 0)"));
    expect(text()).toContain(REFERENCE);
    expect(editor().disabled).toBe(true);
  });

  it("the sample-table viewer lists tables, key markers and rows on demand", async () => {
    await toSql();
    await click(byText("button", "Show sample tables"));
    await waitFor(() => text().includes("employees"));
    expect(container.querySelector('[aria-label="employees columns"]')).not.toBeNull();
    expect(container.querySelector('svg[aria-label="primary key"]')).not.toBeNull();
    expect(container.querySelector('svg[aria-label="foreign key to departments.dept_id"]')).not.toBeNull();
    await click(byText("button", "Show 2 rows"));
    expect([...container.querySelectorAll("#rows-employees tbody td")].map((c) => c.textContent)).toContain("NULL");
  });

  it("the sample tables have an error state with retry", async () => {
    fake.datasetStatus = 503;
    await toSql();
    await click(byText("button", "Show sample tables"));
    await waitFor(() => text().includes("Sample tables are unavailable."));
    fake.datasetStatus = 200;
    useDbmsSqlStore.setState({ datasets: {} });
    await click(byText("button", "Retry"));
    await waitFor(() => !!container.querySelector('[aria-label="employees columns"]'));
  });

  it("a rate-limited run shows an error instead of failing silently", async () => {
    await toSql();
    fake.sandboxStatus = 429;
    await typeInto(editor(), "SELECT 1");
    await click(byText("button", "Run query"));
    await waitFor(() => text().includes("Too many requests."));
  });

  it("unsaved SQL is saved when moving to another question and restored on return", async () => {
    await toSql();
    await typeInto(editor(), "SELECT name FROM employees WHERE 1=1");
    await goTo(1);
    await waitFor(() => puts().some((p) => p.body?.sql === "SELECT name FROM employees WHERE 1=1"));
    await goTo(3);
    expect(editor().value).toBe("SELECT name FROM employees WHERE 1=1");
  });
});

describe("timed mock interview", () => {
  it("shows a countdown, never colours or explains anything, and offers no checking, hints or reveal", async () => {
    await startSession("timed_mock");
    expect(container.querySelector('[role="timer"], [aria-label*="remaining" i], time')).not.toBeNull();
    await click(option(1));
    await waitFor(() => puts().length > 0);
    expect(text()).not.toContain("SECRET_EXPLANATION");
    expect(option(1).className).not.toContain("border-success");
    expect(option(1).className).not.toContain("border-danger");
    await goTo(2);
    expect(byText("button", "Check answer")).toBeUndefined();
    await goTo(3);
    for (const label of ["Check answer", "Show solution", "Show a hint"]) expect(byText("button", label)).toBeUndefined();
    expect(text()).toContain("graded when you submit");
    expect(text()).not.toContain(REFERENCE);
  });

  it("the navigator reflects answered, marked and current questions with text, not colour alone", async () => {
    await startSession("timed_mock");
    await click(option(0));
    await waitFor(() => puts().length > 0);
    await click(byText("button", "Mark for review"));
    await waitFor(() => puts().some((p) => p.body?.marked_for_review === true));
    expect(navButton(1).getAttribute("aria-label")).toContain("marked for review");
    expect(navButton(1).getAttribute("aria-label")).toContain("answered");
    expect(navButton(3).getAttribute("aria-label")).toContain("(SQL)");
    expect(navButton(2).getAttribute("aria-label")).toContain("short answer");
    expect(navButton(1).getAttribute("aria-current")).toBe("step");
  });
});

describe("session completion", () => {
  it("submit asks for confirmation, sends no score, and lands on a result with the review", async () => {
    await startSession();
    await click(option(KEY));
    await waitFor(() => text().includes("SECRET_EXPLANATION"));
    await click(byText("button", "Submit"));
    expect(container.querySelector('[role="alertdialog"]')?.textContent).toContain("2 questions are unanswered");
    await click(byText("button", "Keep working"));
    expect(container.querySelector('[role="alertdialog"]')).toBeNull();
    await click(byText("button", "Submit"));
    await click(byText("button", "Submit now"));
    await waitFor(() => lastPath === `/dbms-sql/result/${SID}` && text().includes("Question review"));
    const submit = requests.find((r) => r.url === `/dbms-sql/sessions/${SID}/submit`)!;
    expect(submit.body).toBeUndefined();
    expect(text()).toContain("1 / 3");
    expect(text()).toContain("33.3% accuracy");
    expect(text()).toContain("Topics to revise");
    expect(text()).toContain("Your query");
    expect(container.querySelectorAll('[aria-label="Reference solution"]').length).toBeGreaterThan(0);
  });

  it("the result explains an incorrect SQL answer with your query, both tables and the reference", async () => {
    await startSession();
    await goTo(3);
    await typeInto(editor(), "SELECT name FROM employees");
    await click(byText("button", "Check answer"));
    await waitFor(() => text().includes("Not matching yet"));
    await click(byText("button", "Submit"));
    await click(byText("button", "Submit now"));
    await waitFor(() => lastPath === `/dbms-sql/result/${SID}` && text().includes("Question review"));
    expect([...container.querySelectorAll("caption")].map((c) => c.textContent)).toEqual(expect.arrayContaining(["Your result", "Expected result"]));
    expect(text()).toContain("Your query returned 3 row(s)");
    expect(text()).toContain(REFERENCE);
    expect(text()).toContain("1 check");
  });

  it("revealed solutions are reported as such in the review", async () => {
    await startSession();
    await goTo(3);
    await click(byText("button", "Show solution"));
    await waitFor(() => text().includes("Solution revealed (this question scores 0)"));
    await click(byText("button", "Submit"));
    await click(byText("button", "Submit now"));
    await waitFor(() => text().includes("Solution revealed before it was solved."));
  });

  it("the review can be filtered to incorrect answers", async () => {
    await startSession();
    await click(option(0));
    await waitFor(() => text().includes("Not quite"));
    await click(byText("button", "Submit"));
    await click(byText("button", "Submit now"));
    await waitFor(() => text().includes("Question review"));
    await click(byText('[role="radio"]', /^Incorrect/));
    expect(container.querySelectorAll("section[aria-labelledby='review-title'] > ol > li")).toHaveLength(1);
  });

  it("a double click on submit sends one request", async () => {
    await startSession();
    await click(byText("button", "Submit"));
    const confirm = byText("button", "Submit now")!;
    await act(async () => { confirm.click(); confirm.click(); });
    await waitFor(() => lastPath === `/dbms-sql/result/${SID}`);
    expect(requests.filter((r) => r.url === `/dbms-sql/sessions/${SID}/submit`)).toHaveLength(1);
  });

  it("resuming lands on the first unanswered question and restores saved SQL; a completed session redirects to its result", async () => {
    fake.answers[QIDS[0]] = { ...blank(), selected: 0 };
    fake.answers[QIDS[2]] = { ...blank(), sql: "SELECT name FROM employees" };
    await visit(`/dbms-sql/session/${SID}`);
    await waitFor(() => text().includes("Question 2 of 3"));
    await goTo(3);
    expect(editor().value).toBe("SELECT name FROM employees");
    fake.status = "completed";
    await act(async () => root.render(<div />)); // leave the page, as a real navigation would
    useDbmsSqlStore.getState().reset();
    await visit(`/dbms-sql/session/${SID}`);
    await waitFor(() => lastPath === `/dbms-sql/result/${SID}`);
  });

  it("shows an error with retry when the session cannot be loaded, and when the result is not ready", async () => {
    await visit(`/dbms-sql/session/${"f".repeat(24)}`);
    await waitFor(() => text().includes("Back to the DBMS & SQL Interview Lab"));
    expect(container.querySelector('[role="alert"]')).not.toBeNull();
    useDbmsSqlStore.getState().reset();
    fake.resultStatus = 409;
    await visit(`/dbms-sql/result/${SID}`);
    await waitFor(() => text().includes("Results are available after the session is submitted."));
    fake.resultStatus = 200;
    await click(byText("button", "Retry"));
    await waitFor(() => text().includes("Question review"));
  });
});

describe("history and analytics display", () => {
  it("the progress tab shows an honest empty state before any practice", async () => {
    await visit("/dbms-sql?tab=progress");
    await waitFor(() => text().includes("No DBMS & SQL practice recorded yet"));
    expect(text()).not.toMatch(/\d+%/);
  });

  it("the progress tab shows real analytics: accuracy, SQL success, weak topics, repeated mistakes and mock scores", async () => {
    fake.progress = "data";
    await visit("/dbms-sql?tab=progress");
    await waitFor(() => text().includes("Weak topics and revision"));
    expect(text()).toContain("44.4%");
    expect(text()).toContain("SQL practice");
    expect(text()).toContain("37.5%");
    expect(text()).toContain("21");
    expect(text()).toContain("25% accuracy over 12 answered questions");
    expect(text()).toContain("missed 3 times");
    expect(text()).toContain("Mock interview scores");
    expect(container.querySelector('[role="progressbar"][aria-label="INNER, LEFT, RIGHT, and other supported joins accuracy"]')?.getAttribute("aria-valuenow")).toBe("25");
    const practise = container.querySelector<HTMLAnchorElement>('a[aria-label^="Practise INNER"]');
    expect(practise?.getAttribute("href")).toContain("topic=joins");
  });

  it("the playground runs a free query, is clearly unscored, and supports clicking a table name", async () => {
    await visit("/dbms-sql?tab=playground");
    await waitFor(() => text().includes("SQL playground") && !!container.querySelector('[aria-label="employees columns"]'));
    expect(text()).toContain("Not scored or saved");
    expect(text()).toContain("Rejected:");
    await click(container.querySelector('button[aria-label="Insert employees into the editor"]'));
    expect(container.querySelector<HTMLTextAreaElement>("#playground-sql")!.value).toMatch(/employees$/);
    await click(byText("button", "Run query"));
    await waitFor(() => !!container.querySelector("table"));
    expect(requests.some((r) => r.url === "/dbms-sql/sandbox/run")).toBe(true);
  });

  it("tabs are keyboard operable", async () => {
    await visit("/dbms-sql");
    await waitFor(() => text().includes("Practice mode"));
    const tab = container.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')!;
    await act(async () => { tab.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true })); });
    await waitFor(() => container.querySelector('[role="tab"][aria-selected="true"]')?.textContent === "SQL playground");
  });
});
