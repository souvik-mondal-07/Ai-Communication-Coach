// @vitest-environment jsdom
/**
 * Phase 26 UI tests. The REAL <App /> (routes, guards, layout, Python practice pages, store, service) runs in jsdom; only HTTP is faked, by an
 * in-memory backend that keeps its own answer key, reference solution and hidden-test verdicts. That lets the tests prove what the browser sends
 * (never a score, user id, correctness flag, test result or answer key) and what it shows at each stage (no answer, explanation or reference
 * solution before it is earned), including editor interactions, test results, hints, timed-test restrictions, completion, history and analytics.
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
import { usePythonPracticeStore } from "@/store/pythonPracticeStore";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const SID = "c".repeat(24);
const QIDS = ["pyq-0000000001", "pyq-0000000002", "pyq-0000000003"];
const KEY = 1; // displayed correct option of the MCQ: the fake server's secret
const MCQ_EXPLANATION = "SECRET_EXPLANATION: default arguments are evaluated once at definition time.";
const REFERENCE = "def two_sum(nums, target):\n    seen = {}  # SECRET_REFERENCE_SOLUTION";
const CODE_EXPLANATION = "Store complements in a dict for one pass.";
const GOOD = "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i\n    return []";
const HINTS = ["What have you already seen?", "A dict from value to index."];
const STARTER = "def two_sum(nums, target):\n    \"\"\"Return [i, j].\"\"\"\n    # your code here\n    pass\n";
const HIDDEN_SECRET_INPUT = "HIDDEN_INPUT_SECRET";

interface Ans { selected: number | null; text: string | null; code: string | null; marked: boolean; locked: boolean; solved: boolean; revealed: boolean; checks: number; runs: number; hints: number }
interface Fake {
  runnerAvailable: boolean; syllabusStatus: number; totalQuestions: number; progress: "empty" | "data"; coverageStatus: number; historyEmpty: boolean;
  mode: "coding" | "timed_mock"; answers: Record<string, Ans>; status: "in_progress" | "completed"; failAnswers: false | { status: number; code: string };
  runStatus: number; checkRunnerDown: boolean; resultStatus: number;
}
let fake: Fake;
let requests: { method: string; url: string; body: Record<string, unknown> | undefined }[] = [];
let root: Root;
let container: HTMLDivElement;
let lastPath = "";

const fresh = (): Fake => ({ runnerAvailable: true, syllabusStatus: 200, totalQuestions: 331, progress: "empty", coverageStatus: 200, historyEmpty: false, mode: "coding", answers: {}, status: "in_progress", failAnswers: false, runStatus: 200, checkRunnerDown: false, resultStatus: 200 });
const blank = (): Ans => ({ selected: null, text: null, code: null, marked: false, locked: false, solved: false, revealed: false, checks: 0, runs: 0, hints: 0 });

const RUNNER = () => ({ available: fake.runnerAvailable, reason: fake.runnerAvailable ? null : "Code execution needs Linux namespaces and is not available on this operating system.", platform: "linux", python_version: "3.12.3",
  layers: ["Separate OS process (never in the API process)", "Network namespace with no interfaces"], limits: { wall_seconds: 6, cpu_seconds: 4, memory_mb: 384, processes: 12, source_chars: 10000, output_bytes: 400000, per_case_seconds: 1.5 } });
const topic = (id: string, title: string, n: number, status: string) => ({ id, title, question_count: n, by_difficulty: { easy: 1, medium: 1, hard: 0 }, by_format: { concept: 1, coding: 1 }, by_interaction: { mcq: 1, code: 1 }, status });
const SYLLABUS = (total: number) => ({
  units: [
    { id: "unit-a", code: "A", title: "Python fundamentals", summary: "The language and its execution model.", question_count: total ? 32 : 0, topics_implemented: total ? 1 : 0, topics_total: 2, topics: [topic("mutability", "Mutable versus immutable objects", total ? 4 : 0, total ? "implemented" : "missing"), topic("loops", "for and while loops", total ? 1 : 0, total ? "partial" : "missing")] },
    { id: "unit-g", code: "G", title: "Algorithms and coding interviews", summary: "Interview patterns.", question_count: total ? 53 : 0, topics_implemented: total ? 1 : 0, topics_total: 1, topics: [topic("hash-maps", "Hash maps and sets", total ? 6 : 0, total ? "implemented" : "missing")] },
  ],
  question_total: total, min_questions_per_topic: 2, topics_implemented: total ? 2 : 0, topics_total: 3, runner: RUNNER(),
});
const COVERAGE = () => ({ rows: [{ unit: "A", topic_id: "mutability", topic: "Mutable versus immutable objects", covers: "Mutable versus immutable objects", count: 4, easy: 2, medium: 2, hard: 0, formats: { concept: 2, output: 2 }, interactions: { mcq: 4 }, status: "implemented", machine_verified: 2, manual_review: 2 }],
  gaps: ["Closures: only 1 question(s); at least 2 are required."], total_questions: 331, machine_verified: 200, manual_review: 131, topics_implemented: 143, topics_total: 144, runner: RUNNER() });

const codeSpec = () => ({ mode: "function", entry: "two_sum", signature: "def two_sum(nums, target):", starter: STARTER, constraints: ["0 <= len(nums) <= 10**4"],
  examples: [{ id: 0, label: "Example 1", input: "two_sum([2, 7, 11, 15], 9)", expected: "[0, 1]" }, { id: 1, label: "Example 2", input: "two_sum([3, 2, 4], 6)", expected: "[1, 2]" }], visible_count: 2, hidden_count: 5 });
const base = { unit_id: "unit-g", est_time_seconds: 60, tags: [], python_version: null, title: null, code: null, short: null, code_spec: null };
const questionsPublic = () => [
  { ...base, question_id: QIDS[0], topic_id: "default-arguments", format: "concept", interaction: "mcq", difficulty: "medium", statement: "Fake Python question 1: why does a mutable default argument persist?", options: ["It is copied", "It is created once", "It is global", "It is a tuple"] },
  { ...base, question_id: QIDS[1], topic_id: "hash-maps", format: "coding", interaction: "code", difficulty: "easy", title: "Two Sum", statement: "Return the indices of the two numbers that add up to the target.", options: [], code_spec: codeSpec() },
  { ...base, question_id: QIDS[2], topic_id: "exceptions", format: "output", interaction: "short", difficulty: "easy", statement: "Fake Python question 3: type the exception class this code raises.", code: "1 / 0", options: [], short: { kind: "text", help: "Type the exception class name." } },
];
const feedbackFor = (i: number, a: Ans) => i === 0 ? { kind: "mcq", is_correct: a.selected === KEY, correct_index: KEY, explanation: MCQ_EXPLANATION }
  : i === 1 ? { kind: "code", is_correct: a.solved, revealed: a.revealed, reference_source: REFERENCE, time_complexity: "O(n)", space_complexity: "O(n)", explanation: CODE_EXPLANATION }
  : { kind: "short", is_correct: a.solved, answer: "ZeroDivisionError", explanation: "Division by zero." };

function sessionPayload() {
  const exam = fake.mode === "timed_mock";
  return {
    session_id: SID, mode: fake.mode, status: fake.status, difficulty: null, question_count: 3, requested_count: 3, unit_ids: ["unit-g"], topic_ids: ["hash-maps"], immediate_feedback: !exam, exam_mode: exam,
    started_at: new Date().toISOString(), expires_at: exam ? new Date(Date.now() + 900_000).toISOString() : null, server_time: new Date().toISOString(), remaining_seconds: exam ? 900 : null, timer_minutes: exam ? 15 : null,
    scoring_policy: "Each correct answer scores 1 mark.",
    questions: questionsPublic().map((q, i) => {
      const a = fake.answers[q.question_id] ?? blank();
      return { ...q, selected_index: a.selected, text_answer: a.text, code_answer: a.code, marked_for_review: a.marked, locked: a.locked, checks: a.checks, runs: a.runs, hints_total: exam || i === 0 ? 0 : 2, hints_used: exam ? 0 : a.hints,
        hints: exam ? [] : HINTS.slice(0, a.hints), last_check: null, last_run: null, can_reveal: !exam && i === 1 && (a.checks >= 1 || a.hints >= 2), feedback: a.locked && !exam ? feedbackFor(i, a) : null };
    }),
  };
}
function resultPayload() {
  const a = (i: number) => fake.answers[QIDS[i]] ?? blank();
  const outcomes = [a(0).selected === null ? "unanswered" : a(0).selected === KEY ? "correct" : "incorrect", a(1).solved ? "correct" : a(1).revealed || a(1).code ? "incorrect" : "unanswered", a(2).text ? (a(2).solved ? "correct" : "incorrect") : "unanswered"];
  const correct = outcomes.filter((o) => o === "correct").length;
  const incorrect = outcomes.filter((o) => o === "incorrect").length;
  return {
    session_id: SID, mode: fake.mode, status: "completed", total_questions: 3, correct, incorrect, unanswered: 3 - correct - incorrect, score: correct, accuracy: Math.round((correct / 3) * 1000) / 10, time_taken_seconds: 95,
    average_seconds_per_question: 31.7, auto_submitted: false, started_at: new Date().toISOString(), finished_at: new Date().toISOString(),
    topic_performance: [{ topic_id: "hash-maps", topic_title: "Hash maps and sets", unit_id: "unit-g", total: 3, correct, incorrect, unanswered: 3 - correct - incorrect, accuracy: 33.3 }],
    revision_topics: correct < 3 ? [{ topic_id: "hash-maps", topic_title: "Hash maps and sets", accuracy: 33.3 }] : [], scoring_policy: "Each correct answer scores 1 mark.",
    questions: questionsPublic().map((q, i) => ({ unit_id: q.unit_id, topic_id: q.topic_id, format: q.format, interaction: q.interaction, difficulty: q.difficulty, title: q.title, statement: q.statement, code: q.code, python_version: null, options: q.options,
      selected_index: a(i).selected, correct_index: i === 0 ? KEY : null, question_id: q.question_id, outcome: outcomes[i], explanation: i === 0 ? MCQ_EXPLANATION : i === 1 ? CODE_EXPLANATION : "Division by zero.", marked_for_review: a(i).marked, time_spent_seconds: 5, hints_used: a(i).hints,
      text_answer: a(i).text, code_answer: a(i).code, code_checks: a(i).checks, tests_passed: i === 1 ? (a(1).solved ? 7 : 3) : 0, tests_total: i === 1 ? 7 : 0, revealed: a(i).revealed, note: a(i).revealed && !a(i).solved ? "Reference solution revealed before it was solved." : null,
      verdict: null, correct_answer: i === 2 ? "ZeroDivisionError" : null, reference_source: i === 1 ? REFERENCE : null, time_complexity: i === 1 ? "O(n)" : null, space_complexity: i === 1 ? "O(n)" : null })),
  };
}
const grade = (code: string, visibleOnly: boolean) => {
  const good = code.includes("target - n in seen");
  const tests: Array<{ id: number; label: string; visible: boolean; passed: boolean; status: string; message: string | null; stdout: string | null; ms: number | null }> = [{ id: 0, label: "Example 1", visible: true, passed: good, status: good ? "passed" : "failed", message: good ? null : "Input: two_sum([2, 7, 11, 15], 9)\nExpected: [0, 1]\nGot: None", stdout: null, ms: 1 },
    { id: 1, label: "Example 2", visible: true, passed: good, status: good ? "passed" : "failed", message: good ? null : "Input: two_sum([3, 2, 4], 6)\nExpected: [1, 2]\nGot: None", stdout: null, ms: 1 }];
  if (!visibleOnly) for (let i = 2; i < 7; i++) tests.push({ id: i, label: `Hidden test ${i}`, visible: false, passed: good, status: good ? "passed" : "failed", message: null, stdout: null, ms: null });
  const passed = tests.filter((t) => t.passed).length;
  return { verdict: good ? "accepted" : "wrong_answer", message: good ? "All tests passed." : "Some tests failed.", passed, total: tests.length, accepted: good, tests, setup_error: null, wall_ms: 12 };
};

const PROGRESS = () => fake.progress === "empty"
  ? { sessions_completed: 0, questions_presented: 0, questions_answered: 0, correct: 0, incorrect: 0, unanswered: 0, accuracy: 0, average_seconds_per_answered_question: null, topic_accuracy: [], unit_accuracy: [], difficulty_accuracy: [],
      coding: { questions_answered: 0, solved: 0, submissions: 0, trial_runs: 0, tests_passed: 0, tests_total: 0, solutions_revealed: 0, success_rate: 0, test_pass_rate: 0 }, mock_interviews: [], recent_sessions: [], trend: [], improvement_points: null, weak_topics: [], repeated_mistakes: [] }
  : { sessions_completed: 3, questions_presented: 30, questions_answered: 27, correct: 12, incorrect: 15, unanswered: 3, accuracy: 44.4, average_seconds_per_answered_question: 41,
      topic_accuracy: [{ topic_id: "closures", topic_title: "Closures", unit_id: "unit-c", answered: 12, correct: 3, presented: 12, accuracy: 25 }], unit_accuracy: [{ unit_id: "unit-c", unit_title: "Functions and functional programming", answered: 12, correct: 3, accuracy: 25 }],
      difficulty_accuracy: [{ difficulty: "easy", answered: 27, correct: 12, accuracy: 44.4 }], coding: { questions_answered: 8, solved: 3, submissions: 21, trial_runs: 30, tests_passed: 40, tests_total: 56, solutions_revealed: 2, success_rate: 37.5, test_pass_rate: 71.4 },
      mock_interviews: [{ session_id: SID, score: 9, total: 20, accuracy: 45, time_taken_seconds: 900, finished_at: new Date().toISOString() }], recent_sessions: [{ session_id: SID, mode: "timed_mock", score: 9, total: 20, accuracy: 45, time_taken_seconds: 900, finished_at: new Date().toISOString() }], trend: [], improvement_points: null,
      weak_topics: [{ topic_id: "closures", topic_title: "Closures", unit_id: "unit-c", answered: 12, correct: 3, accuracy: 25, reason: "25% accuracy over 12 answered questions (below 60%)." }], repeated_mistakes: [] };

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
  const U = "/python-practice";
  if (url === `${U}/syllabus`) return fake.syllabusStatus === 200 ? respond(config, ok(SYLLABUS(fake.totalQuestions))) : respond(config, err("Syllabus service is down.", "SERVICE_UNAVAILABLE"), fake.syllabusStatus);
  if (url === `${U}/runner`) return respond(config, ok(RUNNER()));
  if (url === `${U}/coverage`) return fake.coverageStatus === 200 ? respond(config, ok(COVERAGE())) : respond(config, err("Coverage is unavailable.", "SERVICE_UNAVAILABLE"), fake.coverageStatus);
  if (url === `${U}/progress`) return respond(config, ok(PROGRESS()));
  if (url === `${U}/recommendations`) return respond(config, ok({ has_history: fake.progress === "data", weak_topics: PROGRESS().weak_topics, incorrect_question_count: 0, repeated_mistake_count: 0, message: fake.progress === "data" ? "1 topic(s) need revision." : "Complete a few practice sessions first.", thresholds: { min_answered: 5, accuracy_below: 60 } }));
  if (method === "get" && url === `${U}/sessions`) return respond(config, ok(fake.historyEmpty ? { items: [], page: 1, limit: 10, total: 0, has_next: false }
    : { items: [{ session_id: SID, mode: "coding", status: "completed", started_at: new Date().toISOString(), finished_at: new Date().toISOString(), question_count: 3, unit_ids: [], topic_ids: [], score: 2, accuracy: 66.7, time_taken_seconds: 120, timer_minutes: null },
        { session_id: "d".repeat(24), mode: "topic", status: "in_progress", started_at: new Date().toISOString(), finished_at: null, question_count: 5, unit_ids: [], topic_ids: [], score: null, accuracy: null, time_taken_seconds: null, timer_minutes: null }], page: 1, limit: 10, total: 2, has_next: false }));
  if (method === "post" && url === `${U}/sessions`) return respond(config, ok(sessionPayload()), 201);
  if (method === "get" && url === `${U}/sessions/${SID}`) return respond(config, ok(sessionPayload()));
  if (method === "put" && url.startsWith(`${U}/sessions/${SID}/answers/`)) {
    if (fake.failAnswers) return respond(config, err("Answer rejected.", fake.failAnswers.code), fake.failAnswers.status);
    const qid = url.split("/").pop()!;
    const i = QIDS.indexOf(qid);
    const b = body as { selected_index?: number | null; text?: string | null; code?: string | null; marked_for_review: boolean };
    const prev = fake.answers[qid] ?? blank();
    const locked = fake.mode === "coding" && i === 0 && b.selected_index !== null && b.selected_index !== undefined;
    fake.answers[qid] = { ...prev, selected: i === 0 ? (b.selected_index ?? null) : null, text: i === 2 ? (b.text ?? null) : null, code: i === 1 ? (b.code ?? null) : null, marked: b.marked_for_review, locked };
    return respond(config, ok({ question_id: qid, selected_index: fake.answers[qid].selected, marked_for_review: b.marked_for_review, locked, feedback: locked ? feedbackFor(i, fake.answers[qid]) : null, remaining_seconds: 100 }));
  }
  if (method === "post" && url.endsWith("/run")) {
    if (fake.runStatus !== 200) return respond(config, err("Too many requests.", "RATE_LIMITED"), fake.runStatus);
    const qid = url.split("/").slice(-2)[0];
    const prev = fake.answers[qid] ?? blank();
    fake.answers[qid] = { ...prev, code: (body as { code: string }).code, runs: prev.runs + 1 };
    return respond(config, ok({ question_id: qid, kind: "run", result: grade((body as { code: string }).code, true), remaining_seconds: 100 }));
  }
  if (method === "post" && url.endsWith("/check")) {
    const qid = url.split("/").slice(-2)[0];
    const i = QIDS.indexOf(qid);
    const prev = fake.answers[qid] ?? blank();
    if (fake.mode === "timed_mock") return respond(config, err("Checking answers is not available in this session.", "CHECK_NOT_ALLOWED"), 409);
    if (i === 2) {
      const correct = String((body as { text?: string }).text ?? "").trim() === "ZeroDivisionError";
      fake.answers[qid] = { ...prev, text: (body as { text: string }).text, locked: true, solved: correct, checks: prev.checks + 1 };
      return respond(config, ok({ question_id: qid, kind: "short", correct, locked: true, checks: prev.checks + 1, feedback: feedbackFor(2, fake.answers[qid]), remaining_seconds: 100 }));
    }
    if (fake.checkRunnerDown) return respond(config, err("The code runner is unavailable.", "RUNNER_UNAVAILABLE"), 409);
    const code = String((body as { code?: string }).code ?? "");
    const result = grade(code, false);
    fake.answers[qid] = { ...prev, code, locked: result.accepted, solved: result.accepted, checks: prev.checks + 1 };
    return respond(config, ok({ question_id: qid, kind: "code", correct: result.accepted, result, locked: result.accepted, checks: prev.checks + 1, can_reveal: true, feedback: result.accepted ? feedbackFor(1, fake.answers[qid]) : null, remaining_seconds: 100 }));
  }
  if (method === "post" && url.endsWith("/hint")) {
    const qid = url.split("/").slice(-2)[0];
    const prev = fake.answers[qid] ?? blank();
    fake.answers[qid] = { ...prev, hints: prev.hints + 1 };
    return respond(config, ok({ question_id: qid, hint: HINTS[prev.hints], hint_number: prev.hints + 1, hints_total: 2, hints: HINTS.slice(0, prev.hints + 1) }));
  }
  if (method === "post" && url.endsWith("/reveal")) {
    const qid = url.split("/").slice(-2)[0];
    const prev = fake.answers[qid] ?? blank();
    if (prev.checks < 1 && prev.hints < 2) return respond(config, err("Try submitting a solution before revealing the reference solution.", "REVEAL_TOO_EARLY"), 409);
    fake.answers[qid] = { ...prev, locked: true, revealed: true };
    return respond(config, ok({ question_id: qid, locked: true, feedback: feedbackFor(1, fake.answers[qid]), remaining_seconds: 100 }));
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
const navButton = (n: number) => container.querySelector<HTMLElement>(`nav[aria-label="Question navigator"] ol li:nth-child(${n}) button`)!;
const editor = () => container.querySelector<HTMLTextAreaElement>('textarea[id^="code-"]')!;
const goTo = async (n: number) => { await click(navButton(n)); await waitFor(() => text().includes(`Question ${n} of 3`)); };

async function typeInto(el: HTMLTextAreaElement | HTMLInputElement, value: string) {
  await act(async () => {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value")!.set!.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function startSession(mode: Fake["mode"] = "coding") {
  fake.mode = mode;
  await visit("/python-practice");
  await waitFor(() => text().includes("Practice mode"));
  await click(byText('[role="radio"]', mode === "timed_mock" ? "Timed mock interview" : "Coding challenges"));
  await click(byText("button", "Start"));
  await waitFor(() => lastPath === `/python-practice/session/${SID}` && text().includes("Question 1 of 3"));
}

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
  usePythonPracticeStore.getState().reset();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => { root.unmount(); });
  container.remove();
  clearStoredToken();
});

describe("module access and routing", () => {
  it("is reachable from the sidebar, the dashboard quick links and the /practice/python alias", async () => {
    await visit("/dashboard");
    await waitFor(() => Boolean(container.querySelector('a[href="/python-practice"]')));
    expect(container.querySelectorAll('a[href="/python-practice"]').length).toBeGreaterThanOrEqual(1);
    await visit("/practice/python");
    await waitFor(() => lastPath === "/python-practice");
    await waitFor(() => text().includes("Python Interview Lab"));
  });
  it("shows the four sections and switches with the keyboard", async () => {
    await visit("/python-practice");
    await waitFor(() => text().includes("Practice mode"));
    const tabs = [...container.querySelectorAll('[role="tab"]')].map((t) => t.textContent);
    expect(tabs).toEqual(["Practice", "Syllabus & coverage", "My progress", "History"]);
    const first = container.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')!;
    await act(async () => { first.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true })); });
    await waitFor(() => container.querySelector('[role="tab"][aria-selected="true"]')?.textContent === "Syllabus & coverage");
  });
});

describe("practice setup", () => {
  it("lists all fourteen modes and the honest runner banner", async () => {
    await visit("/python-practice");
    await waitFor(() => text().includes("Practice mode"));
    expect(container.querySelectorAll('[role="radiogroup"] [role="radio"]').length).toBeGreaterThanOrEqual(14);
    expect(text()).toContain("Code runner available");
    expect(text()).toContain("isolated");
  });
  it("says plainly when code cannot run and does not pretend otherwise", async () => {
    fake.runnerAvailable = false;
    await visit("/python-practice");
    await waitFor(() => text().includes("Code runner unavailable"));
    expect(text()).toContain("not available on this operating system");
    expect(text()).toContain("Coding exercises are turned off");
    expect(text()).not.toContain("Isolation was verified");
  });
  it("shows a loading state, then an error with retry, then recovers", async () => {
    fake.syllabusStatus = 503;
    await visit("/python-practice");
    await waitFor(() => text().includes("Syllabus service is down."));
    fake.syllabusStatus = 200;
    await click(byText("button", "Try again") ?? byText("button", "Retry"));
    await waitFor(() => text().includes("Practice mode"));
  });
  it("shows an empty state when the bank has no questions", async () => {
    fake.totalQuestions = 0;
    await visit("/python-practice");
    await waitFor(() => text().includes("No questions are available yet"));
  });
  it("sends only whitelisted fields when starting a session", async () => {
    await startSession();
    const create = posts("/sessions")[0];
    expect(Object.keys(create.body!).sort()).toEqual(["immediate_feedback", "mode", "question_count"]);
    expect(create.body).toMatchObject({ mode: "coding" });
    const serialised = JSON.stringify(requests.map((r) => r.body));
    for (const banned of ["score", "user_id", "is_correct", "correct_index", "passed", "outcome", "status"]) expect(serialised).not.toContain(`"${banned}"`);
  });
  it("requires a topic for topic practice before it will start", async () => {
    await visit("/python-practice");
    await waitFor(() => text().includes("Practice mode"));
    await click(byText('[role="radio"]', "Topic practice"));
    await click(byText("button", "Start"));
    await waitFor(() => text().toLowerCase().includes("choose at least one topic"));
    expect(posts("/sessions")).toHaveLength(0);
  });
});

describe("syllabus, coverage, progress and history", () => {
  it("renders real counts, statuses and the coverage matrix with honest gaps", async () => {
    await visit("/python-practice?tab=syllabus");
    await waitFor(() => text().includes("Python fundamentals") && text().includes("Coverage matrix"));
    expect(text()).toContain("Ready");
    expect(text()).toContain("Few questions");
    await waitFor(() => text().includes("Closures: only 1 question(s)"));
    expect(text()).toContain("131 manual-review only");
  });
  it("shows an error with retry when coverage fails", async () => {
    fake.coverageStatus = 503;
    await visit("/python-practice?tab=syllabus");
    await waitFor(() => text().includes("Coverage is unavailable."));
    fake.coverageStatus = 200;
    await click(byText("button", /Try again|Retry/));
    await waitFor(() => text().includes("Closures: only 1 question(s)"));
  });
  it("shows an empty progress state and never invents numbers", async () => {
    await visit("/python-practice?tab=progress");
    await waitFor(() => text().includes("No Python practice recorded yet"));
    expect(text()).not.toMatch(/\d+% accuracy/);
  });
  it("renders recorded progress, coding statistics and weak topics from the server", async () => {
    fake.progress = "data";
    await visit("/python-practice?tab=progress");
    await waitFor(() => text().includes("Coding practice"));
    expect(text()).toContain("40/56");
    expect(text()).toContain("37.5%");
    expect(text()).toContain("Closures");
    expect(text()).toContain("25% accuracy over 12 answered questions");
  });
  it("lists previous sessions with result and resume links, and handles an empty history", async () => {
    await visit("/python-practice?tab=history");
    await waitFor(() => text().includes("Coding challenges") && text().includes("View result"));
    expect(text()).toContain("2/3 · 66.7%");
    expect(byText("a", "Resume")?.getAttribute("href")).toContain("/python-practice/session/");
    fake.historyEmpty = true;
    usePythonPracticeStore.getState().reset();
    await visit("/python-practice?tab=history&x=1");
    await waitFor(() => text().includes("No sessions yet"));
  });
});

describe("answering questions", () => {
  it("shows no answer, explanation or reference solution before they are earned", async () => {
    await startSession();
    expect(text()).not.toContain("SECRET_EXPLANATION");
    expect(text()).not.toContain("SECRET_REFERENCE_SOLUTION");
    expect(text()).not.toContain(HIDDEN_SECRET_INPUT);
    expect(text()).toContain("Question 1 of 3");
  });
  it("saves only the displayed option position and reveals feedback once locked", async () => {
    await startSession();
    await click(option(0));
    await waitFor(() => text().includes("SECRET_EXPLANATION"));
    expect(text()).toContain("Not quite");
    const put = puts().find((p) => p.url.endsWith(QIDS[0]))!;
    expect(Object.keys(put.body!).sort()).toEqual(["marked_for_review", "selected_index", "time_spent_seconds"]);
    expect(put.body!.selected_index).toBe(0);
    await click(option(2));
    expect(puts().filter((p) => p.url.endsWith(QIDS[0]))).toHaveLength(1); // a locked answer cannot be changed
  });
  it("rolls back the selection and shows an alert when saving fails", async () => {
    await startSession();
    fake.failAnswers = { status: 500, code: "INTERNAL" };
    await click(option(1));
    await waitFor(() => Boolean(container.querySelector('[role="alert"]')));
    expect(option(1).getAttribute("aria-checked")).toBe("false");
    expect(text()).toContain("Answer rejected.");
  });
  it("grades a typed short answer on the server and shows the correct answer", async () => {
    await startSession();
    await goTo(3);
    const input = container.querySelector<HTMLInputElement>('input[id^="short-"]')!;
    await typeInto(input, "ValueError");
    await click(byText("button", "Check answer"));
    await waitFor(() => text().includes("ZeroDivisionError"));
    expect(text()).toContain("Not quite");
    expect(posts("/check")[0].body).toEqual({ text: "ValueError", time_spent_seconds: expect.any(Number) });
  });
  it("supports marking for review and keyboard navigation", async () => {
    await startSession();
    await click(byText("button", "Mark for review"));
    await waitFor(() => puts().some((p) => p.body?.marked_for_review === true));
    await act(async () => { window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true })); });
    await waitFor(() => text().includes("Question 2 of 3"));
  });
});

describe("coding workspace", () => {
  async function openCode() { await startSession(); await goTo(2); await waitFor(() => Boolean(editor())); }

  it("shows the problem, signature, constraints, examples and the starter code without hidden data", async () => {
    await openCode();
    expect(text()).toContain("Two Sum");
    expect(text()).toContain("def two_sum(nums, target):");
    expect(text()).toContain("0 <= len(nums) <= 10**4");
    expect(text()).toContain("two_sum([2, 7, 11, 15], 9)");
    expect(text()).toContain("[0, 1]");
    expect(text()).toContain("5 hidden tests");
    expect(editor().value).toBe(STARTER);
    expect(text()).not.toContain("SECRET_REFERENCE_SOLUTION");
  });
  it("types into the editor, inserts four spaces on Tab and lets Escape-then-Tab leave", async () => {
    await openCode();
    await typeInto(editor(), "x = 1");
    editor().setSelectionRange(0, 0);
    const tab = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    await act(async () => { editor().dispatchEvent(tab); });
    expect(tab.defaultPrevented).toBe(true);
    await waitFor(() => editor().value === "    x = 1");
    await act(async () => { editor().dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); });
    const free = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    await act(async () => { editor().dispatchEvent(free); });
    expect(free.defaultPrevented).toBe(false);
  });
  it("shows a character counter and blocks over-long code", async () => {
    await openCode();
    await typeInto(editor(), "x".repeat(10001));
    expect(text()).toContain("10001/10000");
    expect(byText("button", "Run examples")!.hasAttribute("disabled")).toBe(true);
    expect(byText("button", "Submit solution")!.hasAttribute("disabled")).toBe(true);
  });
  it("runs only the examples and shows per-test failures with a bounded message", async () => {
    await openCode();
    await typeInto(editor(), "def two_sum(nums, target):\n    return None");
    await click(byText("button", "Run examples"));
    await waitFor(() => text().includes("Wrong answer"));
    expect(posts("/run")[0].body).toEqual({ code: "def two_sum(nums, target):\n    return None" });
    expect(text()).toContain("0 of 2 tests passed");
    expect(text()).toContain("Expected: [0, 1]");
    expect(text()).not.toContain("Hidden test");
    expect(text()).not.toContain("SECRET_REFERENCE_SOLUTION");
  });
  it("submits to every test: hidden results show only a verdict and the reference stays locked until earned", async () => {
    await openCode();
    expect(text()).toContain("unlocks after your first submission");
    expect(byText("button", "Show reference solution")).toBeUndefined();
    await typeInto(editor(), "def two_sum(nums, target):\n    return None");
    await click(byText("button", "Submit solution"));
    await waitFor(() => text().includes("Hidden test 2"));
    expect(text()).toContain("0 of 7 tests passed");
    expect(text()).toContain("Hidden: details are not shown");
    expect(text()).not.toContain(HIDDEN_SECRET_INPUT);
    expect(text()).not.toContain("SECRET_REFERENCE_SOLUTION");
    expect(posts("/check")[0].body).toEqual({ code: "def two_sum(nums, target):\n    return None", time_spent_seconds: expect.any(Number) });
    await waitFor(() => Boolean(byText("button", "Show reference solution")));
  });
  it("accepts a correct solution, locks the editor and then shows the reference, complexity and explanation", async () => {
    await openCode();
    await typeInto(editor(), GOOD);
    await click(byText("button", "Submit solution"));
    await waitFor(() => text().includes("Solved: every test passed"));
    expect(text()).toContain("Accepted");
    expect(text()).toContain("7 of 7 tests passed");
    expect(text()).toContain("SECRET_REFERENCE_SOLUTION");
    expect(text()).toContain("time O(n), space O(n)");
    expect(text()).toContain(CODE_EXPLANATION);
    expect(editor().disabled).toBe(true);
    expect(byText("button", "Submit solution")!.hasAttribute("disabled")).toBe(true);
  });
  it("lets you give up after a try: the reference is shown and the question is marked as scoring zero", async () => {
    await openCode();
    await typeInto(editor(), "def two_sum(nums, target):\n    return None");
    await click(byText("button", "Submit solution"));
    await waitFor(() => Boolean(byText("button", "Show reference solution")));
    await click(byText("button", "Show reference solution"));
    await waitFor(() => text().includes("Reference solution revealed: this question scores 0"));
    expect(text()).toContain("SECRET_REFERENCE_SOLUTION");
    expect(editor().disabled).toBe(true);
  });
  it("reveals hints one at a time and counts them", async () => {
    await openCode();
    await click(byText("button", "Show a hint"));
    await waitFor(() => text().includes(HINTS[0]));
    expect(text()).not.toContain(HINTS[1]);
    await click(byText("button", "Show another hint"));
    await waitFor(() => text().includes(HINTS[1]));
    expect(posts("/hint")).toHaveLength(2);
    await waitFor(() => Boolean(byText("button", "Show reference solution")));
  });
  it("does not save an untouched starter template as an answer", async () => {
    await openCode();
    await goTo(1);
    await goTo(2);
    expect(puts().filter((p) => p.url.endsWith(QIDS[1]))).toHaveLength(0);
    await typeInto(editor(), "def two_sum(nums, target):\n    return []");
    await goTo(1);
    await waitFor(() => puts().some((p) => p.url.endsWith(QIDS[1]) && p.body?.code === "def two_sum(nums, target):\n    return []"));
  });
  it("resets to the starter code", async () => {
    await openCode();
    await typeInto(editor(), "something else");
    await click(byText("button", "Reset to starter"));
    await waitFor(() => editor().value === STARTER);
  });
  it("reports a runner outage without counting the attempt and keeps the code", async () => {
    await openCode();
    fake.checkRunnerDown = true;
    await typeInto(editor(), GOOD);
    await click(byText("button", "Submit solution"));
    await waitFor(() => text().includes("The code runner is unavailable."));
    expect(editor().value).toBe(GOOD);
    expect(editor().disabled).toBe(false);
  });
  it("shows a rate-limit message and keeps working", async () => {
    await openCode();
    fake.runStatus = 429;
    await typeInto(editor(), GOOD);
    await click(byText("button", "Run examples"));
    await waitFor(() => text().includes("Too many requests."));
    fake.runStatus = 200;
    await click(byText("button", "Run examples"));
    await waitFor(() => text().includes("Accepted"));
  });
});

describe("timed mock interview", () => {
  it("allows trial runs but offers no checking, hints or reveal", async () => {
    await startSession("timed_mock");
    await goTo(2);
    await waitFor(() => Boolean(editor()));
    expect(byText("button", "Run examples")).toBeDefined();
    expect(byText("button", "Submit solution")).toBeUndefined();
    expect(byText("button", "Show a hint")).toBeUndefined();
    expect(byText("button", "Show reference solution")).toBeUndefined();
    expect(text()).toContain("graded against every test when you submit the test");
    await typeInto(editor(), GOOD);
    await click(byText("button", "Run examples"));
    await waitFor(() => text().includes("Accepted"));
    expect(text()).not.toContain("SECRET_REFERENCE_SOLUTION");
    expect(container.querySelector('[role="timer"], [aria-label*="remaining" i], time')).not.toBeNull();
  });
  it("never colours or explains an MCQ during the test", async () => {
    await startSession("timed_mock");
    await click(option(0));
    await waitFor(() => puts().length > 0);
    expect(text()).not.toContain("SECRET_EXPLANATION");
    expect(text()).not.toContain("Correct answer");
  });
});

describe("completion", () => {
  it("submits once, shows the server's score, tests, explanations and the reference solution", async () => {
    await startSession();
    await click(option(KEY));
    await waitFor(() => text().includes("SECRET_EXPLANATION"));
    await goTo(2);
    await typeInto(editor(), GOOD);
    await click(byText("button", "Submit solution"));
    await waitFor(() => text().includes("Solved: every test passed"));
    await click(byText("button", "Submit"));
    await click(byText("button", "Submit now"));
    await waitFor(() => lastPath === `/python-practice/result/${SID}` && text().includes("Question review"));
    expect(text()).toContain("2 / 3");
    expect(text()).toContain("66.7% accuracy");
    expect(text()).toContain("Tests passed: 7 of 7");
    expect(text()).toContain("SECRET_REFERENCE_SOLUTION");
    expect(text()).toContain("Complexity: time O(n), space O(n)");
    expect(posts("/submit")).toHaveLength(1);
    expect(posts("/submit")[0].body).toBeUndefined();
  });
  it("filters the review to incorrect answers and links to topic practice", async () => {
    await startSession();
    await click(option(0));
    await waitFor(() => text().includes("SECRET_EXPLANATION"));
    await click(byText("button", "Submit"));
    await click(byText("button", "Submit now"));
    await waitFor(() => text().includes("Question review"));
    await click(byText('[role="radio"]', /^Incorrect/));
    expect(container.querySelectorAll("ol > li.space-y-3").length).toBe(1);
    expect(byText("a", "Practise")?.getAttribute("href")).toContain("/python-practice?mode=topic&topic=hash-maps");
  });
  it("shows an error with retry when a result cannot be loaded", async () => {
    fake.resultStatus = 409;
    await visit(`/python-practice/result/${SID}`);
    await waitFor(() => text().includes("Results are available after the session is submitted."));
    fake.resultStatus = 200;
    await click(byText("button", /Try again|Retry/));
    await waitFor(() => text().includes("Question review"));
  });
  it("returns to the result page when the server says time is up", async () => {
    await startSession();
    fake.failAnswers = { status: 409, code: "SESSION_EXPIRED" };
    fake.status = "completed";
    await click(option(1));
    await waitFor(() => lastPath === `/python-practice/result/${SID}`);
  });
});
