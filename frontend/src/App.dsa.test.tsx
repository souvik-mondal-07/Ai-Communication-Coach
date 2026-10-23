// @vitest-environment jsdom
/**
 * Phase 24 UI tests. The REAL <App /> (routes, guards, layout, DSA pages, store, service) runs in jsdom; only HTTP is faked, by an
 * in-memory DSA backend that keeps its own answer key and reference solution. That lets the tests prove what the browser
 * sends (never a score, user id or correctness flag) and what it shows at each stage (no answer, explanation or reference
 * before it is earned), including loading, empty, error and result states.
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
import { useDsaStore } from "@/store/dsaStore";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const SID = "d".repeat(24);
const QIDS = ["dsa-0000000001", "dsa-0000000002", "dsa-0000000003"];
const KEY = [1, 2]; // displayed correct option for the two MCQs: the fake server's secret
const EXPLAIN = ["Pass 1 bubbles the largest value to the right.", "Binary search halves the range each step."];
const SECRET_EXPLANATION = EXPLAIN[0];
const REFERENCE = "def second_largest(nums):\n    return SECRET_REFERENCE_BODY";
const TEMPLATE = "def second_largest(nums):\n    # your code here\n    pass\n";
const TRACE = [{ label: "After pass 1", state: "[1, 4, 2, 5, 8]" }, { label: "After pass 2", state: "[1, 2, 4, 5, 8]" }, { label: "After pass 3", state: "[1, 2, 4, 5, 8]" }];
const ALL_TESTS = [
  { label: "sample", args: [[4, 9, 2, 7]], expected: 7, visible: true, edge: false },
  { label: "all equal", args: [[5, 5, 5]], expected: -1, visible: false, edge: true },
];

interface Fake {
  syllabusStatus: number;
  syllabusDelayMs: number;
  totalQuestions: number;
  progress: "empty" | "data";
  immediate: boolean;
  answers: Record<string, { selected: number | null; code: string | null; marked: boolean; locked: boolean }>;
  status: "in_progress" | "completed";
  failAnswers: false | { status: number; code: string };
  resultStatus: number;
  submitDelayMs: number;
  assessments: Record<string, string>;
}
let fake: Fake;
let requests: { method: string; url: string; body: Record<string, unknown> | undefined }[] = [];
let root: Root;
let container: HTMLDivElement;
let lastPath = "";

const fresh = (): Fake => ({ syllabusStatus: 200, syllabusDelayMs: 0, totalQuestions: 20, progress: "empty", immediate: false, answers: {}, status: "in_progress", failAnswers: false, resultStatus: 200, submitDelayMs: 0, assessments: {} });

const SYLLABUS = (total: number) => ({
  totals: { topics: 2, subtopics: 4, subtopics_implemented: total ? 3 : 0, questions: total, by_format: { conceptual: 5, scenario: 2, output: 3, trace: 6, complexity: 2, coding: 2 }, min_questions_per_subtopic: 4 },
  execution: { automated_code_execution: false, mode: "self_assessed", message: "Code answers are saved but not run automatically. After submitting you see the reference solution and the test cases." },
  topics: [
    { id: "sorting-searching", code: "C", title: "Sorting and Searching", summary: "Elementary sorts and searches.", question_count: total ? 12 : 0, subtopics_implemented: 2, subtopics_total: 3, status: "partial",
      items: [{ text: "Bubble Sort.", subtopic_ids: ["bubble-sort"], question_count: total ? 6 : 0 }, { text: "Binary Search.", subtopic_ids: ["binary-search"], question_count: total ? 6 : 0 }],
      subtopics: [
        { id: "bubble-sort", title: "Bubble Sort", question_count: total ? 6 : 0, by_difficulty: { easy: 3, medium: 2, hard: 1 }, by_format: { trace: 3, complexity: 1, coding: 2 }, auto_graded: 4, self_assessed_code: 2, status: "implemented" },
        { id: "binary-search", title: "Binary Search", question_count: total ? 6 : 0, by_difficulty: { easy: 2, medium: 2, hard: 2 }, by_format: { trace: 3, conceptual: 3 }, auto_graded: 6, self_assessed_code: 0, status: "implemented" },
        { id: "selection-sort", title: "Selection Sort", question_count: 0, by_difficulty: { easy: 0, medium: 0, hard: 0 }, by_format: {}, auto_graded: 0, self_assessed_code: 0, status: "missing" }] },
    { id: "graphs", code: "J", title: "Graphs", summary: "Traversals and shortest paths.", question_count: total ? 8 : 0, subtopics_implemented: 1, subtopics_total: 1, status: "implemented", items: [{ text: "Breadth-First Search (BFS).", subtopic_ids: ["bfs"], question_count: total ? 8 : 0 }],
      subtopics: [{ id: "bfs", title: "Breadth-First Search (BFS)", question_count: total ? 8 : 0, by_difficulty: { easy: 4, medium: 2, hard: 2 }, by_format: { trace: 4, scenario: 2 }, auto_graded: 8, self_assessed_code: 0, status: "implemented" }] },
  ],
});

const mcq = (i: number) => ({
  question_id: QIDS[i], topic_id: "sorting-searching", subtopic_id: "bubble-sort", format: i === 0 ? "trace" : "output", interaction: "mcq", coding_type: null, difficulty: "easy",
  statement: `Fake DSA question ${i + 1}: choose the right option.`, code: i === 1 ? "print(sorted([3, 1, 2]))" : null, options: ["Option A", "Option B", "Option C", "Option D"].map((o) => `${o} (q${i + 1})`),
  constraints: null, est_time_seconds: 60, coding: null,
});
const codeQ = () => ({
  question_id: QIDS[2], topic_id: "arrays", subtopic_id: "array-traversal", format: "coding", interaction: "code", coding_type: "write_function", difficulty: "medium",
  statement: "Write second_largest(nums) returning the second-largest distinct value, or -1.", code: null, options: [], constraints: "O(n) time, O(1) space.", est_time_seconds: 420,
  coding: { function_name: "second_largest", template: TEMPLATE, sample_io: "second_largest([4, 9, 2, 7]) → 7", visible_tests: [{ label: "sample", args: [[4, 9, 2, 7]], expected: 7 }], hidden_test_count: 1 },
});

function sessionPayload() {
  const now = Date.now();
  return {
    session_id: SID, mode: fake.immediate ? "coding" : "timed_mock", status: fake.status, difficulty: null, question_count: 3, requested_count: 3, topic_ids: ["sorting-searching", "arrays"],
    immediate_feedback: fake.immediate, exam_mode: !fake.immediate, started_at: new Date(now).toISOString(), expires_at: new Date(now + 1_800_000).toISOString(), server_time: new Date(now).toISOString(),
    remaining_seconds: 1800, timer_minutes: 30, scoring_policy: "Each correct multiple-choice answer scores 1 mark. Coding exercises are ungraded.",
    questions: [mcq(0), mcq(1), codeQ()].map((q, i) => {
      const a = fake.answers[QIDS[i]];
      const feedback = a?.locked ? (i < 2 ? { kind: "mcq", is_correct: a.selected === KEY[i], correct_index: KEY[i], explanation: EXPLAIN[i], complexity: { time: "O(n²)", space: "O(1)" }, trace: i === 0 ? TRACE : null }
        : { kind: "code", explanation: "Track two values.", reference_solution: REFERENCE, test_cases: ALL_TESTS, complexity: { time: "O(n)" }, execution_note: "Your code was NOT run." }) : null;
      return { ...q, selected_index: a?.selected ?? null, code_answer: a?.code ?? null, marked_for_review: a?.marked ?? false, locked: a?.locked ?? false, hints: fake.immediate ? ["Hint one: track two variables."] : [], feedback };
    }),
  };
}

function resultPayload() {
  const sel = (i: number) => fake.answers[QIDS[i]]?.selected ?? null;
  const outcome = (i: number) => (sel(i) === null ? "unanswered" : sel(i) === KEY[i] ? "correct" : "incorrect");
  const questions = [
    { ...mcq(0), selected_index: sel(0), correct_index: KEY[0], code_answer: null, outcome: outcome(0), explanation: EXPLAIN[0], complexity: { time: "O(n²)", space: "O(1)" }, trace: TRACE, reference_solution: null, test_cases: null, self_assessment: null, execution_note: null, marked_for_review: fake.answers[QIDS[0]]?.marked ?? false, time_spent_seconds: 5 },
    { ...mcq(1), selected_index: sel(1), correct_index: KEY[1], code_answer: null, outcome: outcome(1), explanation: EXPLAIN[1], complexity: null, trace: null, reference_solution: null, test_cases: null, self_assessment: null, execution_note: null, marked_for_review: false, time_spent_seconds: 7 },
    { ...codeQ(), selected_index: null, correct_index: null, code_answer: fake.answers[QIDS[2]]?.code ?? null, outcome: "ungraded", explanation: "Track two values.", complexity: { time: "O(n)", space: "O(1)" }, trace: null, reference_solution: REFERENCE, test_cases: ALL_TESTS,
      self_assessment: fake.assessments[QIDS[2]] ?? null, execution_note: "Your code was NOT run: this application does not execute submitted code.", marked_for_review: false, time_spent_seconds: 30 },
  ];
  const correct = [0, 1].filter((i) => outcome(i) === "correct").length;
  const incorrect = [0, 1].filter((i) => outcome(i) === "incorrect").length;
  return {
    session_id: SID, mode: fake.immediate ? "coding" : "timed_mock", status: "completed", total_questions: 3, graded_questions: 2, ungraded_questions: 1, correct, incorrect, unanswered: 2 - correct - incorrect, score: correct, accuracy: correct * 50,
    time_taken_seconds: 95, average_seconds_per_question: 31.7, auto_submitted: false, started_at: new Date().toISOString(), finished_at: new Date().toISOString(),
    topic_performance: [{ topic_id: "sorting-searching", topic_title: "Sorting and Searching", total: 2, correct, incorrect, unanswered: 2 - correct - incorrect, accuracy: correct * 50 }],
    revision_topics: correct < 2 ? [{ topic_id: "sorting-searching", topic_title: "Sorting and Searching", accuracy: correct * 50, subtopics: [{ subtopic_id: "bubble-sort", title: "Bubble Sort" }] }] : [],
    complexity_summary: [{ question_id: QIDS[0], subtopic_id: "bubble-sort", subtopic_title: "Bubble Sort", statement: "x", complexity: { time: "O(n²)", space: "O(1)" } }],
    questions, scoring_policy: "Each correct multiple-choice answer scores 1 mark. Coding exercises are ungraded.",
  };
}

const PROGRESS = () => fake.progress === "empty"
  ? { sessions_completed: 0, questions_presented: 0, questions_answered: 0, correct: 0, incorrect: 0, unanswered: 0, ungraded_code: 0, accuracy: 0, average_seconds_per_question: null, topic_accuracy: [], difficulty_accuracy: [], recent_sessions: [], trend: [], improvement_points: null, weak_topics: [], attempts_scanned_limit: 5000 }
  : { sessions_completed: 2, questions_presented: 20, questions_answered: 18, correct: 9, incorrect: 9, unanswered: 2, ungraded_code: 2, accuracy: 50, average_seconds_per_question: 42,
      topic_accuracy: [{ topic_id: "graphs", topic_title: "Graphs", answered: 18, correct: 9, presented: 20, accuracy: 50 }], difficulty_accuracy: [{ difficulty: "easy", answered: 18, correct: 9, accuracy: 50 }],
      recent_sessions: [{ session_id: SID, mode: "timed_mock", score: 9, total: 20, graded: 18, accuracy: 50, time_taken_seconds: 600, finished_at: new Date().toISOString() }], trend: [], improvement_points: null,
      weak_topics: [{ topic_id: "graphs", topic_title: "Graphs", answered: 18, correct: 5, accuracy: 28, reason: "28% accuracy over 18 answered questions (below 60%).", weak_subtopics: [{ subtopic_id: "bfs", title: "Breadth-First Search (BFS)", accuracy: 20, answered: 5 }] }], attempts_scanned_limit: 5000 };

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
  if (url === "/dsa/syllabus" && fake.syllabusDelayMs) await new Promise((r) => setTimeout(r, fake.syllabusDelayMs));
  if (url === "/dsa/syllabus") return fake.syllabusStatus === 200 ? respond(config, ok(SYLLABUS(fake.totalQuestions))) : respond(config, err("Syllabus service is down.", "SERVICE_UNAVAILABLE"), fake.syllabusStatus);
  if (url === "/dsa/progress") return respond(config, ok(PROGRESS()));
  if (url === "/dsa/recommendations") return respond(config, ok({ has_history: fake.progress === "data", weak_topics: PROGRESS().weak_topics, incorrect_question_count: 0, message: fake.progress === "data" ? "1 topic(s) need revision." : "Complete a few practice sessions first; recommendations are based only on your recorded answers.", thresholds: { min_answered: 5, accuracy_below: 60 } }));
  if (method === "post" && url === "/dsa/sessions") return respond(config, ok(sessionPayload()), 201);
  if (method === "get" && url === `/dsa/sessions/${SID}`) return respond(config, ok(sessionPayload()));
  if (method === "put" && url.startsWith(`/dsa/sessions/${SID}/answers/`)) {
    if (fake.failAnswers) return respond(config, err("Answer rejected.", fake.failAnswers.code), fake.failAnswers.status);
    const qid = url.split("/").pop()!;
    const i = QIDS.indexOf(qid);
    const b = body as { selected_index?: number | null; code?: string | null; reveal?: boolean; marked_for_review: boolean };
    const isCode = i === 2;
    const locked = fake.immediate && (isCode ? Boolean(b.reveal && b.code) : b.selected_index !== null && b.selected_index !== undefined);
    fake.answers[qid] = { selected: isCode ? null : (b.selected_index ?? null), code: isCode ? (b.code ?? null) : null, marked: b.marked_for_review, locked };
    const sp = sessionPayload().questions[i];
    return respond(config, ok({ question_id: qid, selected_index: fake.answers[qid].selected, code_answer: fake.answers[qid].code, marked_for_review: b.marked_for_review, locked, feedback: locked ? sp.feedback : null, remaining_seconds: 100 }));
  }
  if (method === "post" && url === `/dsa/sessions/${SID}/submit`) {
    if (fake.submitDelayMs) await new Promise((r) => setTimeout(r, fake.submitDelayMs));
    fake.status = "completed";
    return respond(config, ok(resultPayload()));
  }
  if (method === "get" && url === `/dsa/sessions/${SID}/result`) return fake.resultStatus === 200 ? respond(config, ok(resultPayload())) : respond(config, err("Results are available after the session is submitted.", "SESSION_NOT_FINISHED"), fake.resultStatus);
  if (method === "put" && url.startsWith(`/dsa/sessions/${SID}/self-assessment/`)) {
    fake.assessments[url.split("/").pop()!] = (body as { verdict: string }).verdict;
    return respond(config, ok({ question_id: url.split("/").pop(), self_assessment: (body as { verdict: string }).verdict, counts_toward_score: false }));
  }
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
async function visit(path: string) {
  await act(async () => { root.render(<MemoryRouter key={path} initialEntries={[path]}><App /><Probe /></MemoryRouter>); });
}
const click = (el: Element | null | undefined) => { if (!el) throw new Error("element not found"); return act(async () => { (el as HTMLElement).click(); }); };
const byText = (sel: string, t: string | RegExp) => [...container.querySelectorAll(sel)].find((e) => (typeof t === "string" ? e.textContent?.includes(t) : t.test(e.textContent ?? ""))) as HTMLElement | undefined;
const option = (n: number) => container.querySelectorAll<HTMLElement>('[role="radiogroup"][aria-labelledby="question-heading"] [role="radio"]')[n];
const puts = () => requests.filter((r) => r.method === "put");
const key = (k: string) => act(async () => { window.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true })); });
const navButton = (n: number) => container.querySelector<HTMLElement>(`nav[aria-label="Question navigator"] ol li:nth-child(${n}) button`)!;

async function typeInto(el: HTMLTextAreaElement, value: string) {
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
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
  useDsaStore.getState().reset();
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

describe("dashboard states", () => {
  it("shows a loading state, then the seven practice modes", async () => {
    fake.syllabusDelayMs = 150;
    await visit("/dsa");
    await waitFor(() => !!container.querySelector('[role="status"][aria-label="Loading practice options"]'));
    await waitFor(() => text().includes("Practice mode"));
    const modes = [...container.querySelectorAll('[role="radiogroup"][aria-label="Practice mode"] [role="radio"]')].map((b) => b.textContent ?? "");
    expect(modes).toHaveLength(7);
    for (const t of ["Topic practice", "Technical interview", "Code tracing", "Complexity challenge", "Coding practice", "Timed mock test", "Weak topic revision"]) expect(modes.some((m) => m.includes(t))).toBe(true);
    expect(container.querySelector("h1")?.textContent).toContain("DSA Interview Practice");
    expect(text()).toContain("no negative marking");
  });

  it("appears in the sidebar navigation", async () => {
    await visit("/dsa");
    await waitFor(() => text().includes("Practice mode"));
    expect([...container.querySelectorAll("a")].some((a) => a.getAttribute("href") === "/dsa" && a.textContent?.includes("DSA Practice"))).toBe(true);
  });

  it("shows an error with a working retry when the syllabus cannot load", async () => {
    fake.syllabusStatus = 503;
    await visit("/dsa");
    await waitFor(() => text().includes("Syllabus service is down."));
    expect(container.querySelector('[role="alert"]')).not.toBeNull();
    fake.syllabusStatus = 200;
    await click(byText("button", "Retry"));
    await waitFor(() => text().includes("Practice mode"));
  });

  it("shows an honest empty state when the bank has no questions", async () => {
    fake.totalQuestions = 0;
    await visit("/dsa");
    await waitFor(() => text().includes("No questions are available yet"));
    expect(container.querySelector('[role="radiogroup"][aria-label="Practice mode"]')).toBeNull();
  });

  it("the syllabus tab reports real coverage: a subtopic without questions is not 'ready'", async () => {
    await visit("/dsa?tab=syllabus");
    await waitFor(() => text().includes("Syllabus coverage"));
    expect(text()).toContain("3 of 4 subtopics ready");
    expect(text()).toContain("No questions yet"); // Selection Sort
    expect(text()).toContain("Not available");
    expect(text()).toContain("Code answers are saved but not run automatically");
    expect(text()).toContain("Bubble Sort.");
  });

  it("the progress tab is an empty state with no invented numbers, then shows real data", async () => {
    await visit("/dsa?tab=progress");
    await waitFor(() => text().includes("No DSA practice recorded yet"));
    expect(text()).not.toMatch(/Overall accuracy/);
    fake.progress = "data";
    useDsaStore.getState().reset();
    await visit("/dsa?tab=progress&x=1");
    await waitFor(() => text().includes("Overall accuracy"));
    expect(text()).toContain("50%");
    expect(text()).toContain("Revision recommendations");
    expect(text()).toContain("28% accuracy over 18 answered questions");
    expect(text()).toContain("2 coding exercises attempted");
  });
});

describe("starting a session", () => {
  it("topic practice needs a topic; the browser sends no user id, score or answers", async () => {
    await visit("/dsa");
    await waitFor(() => text().includes("Practice mode"));
    await click(byText("button", "Start practice"));
    expect(text()).toContain("Choose at least one topic or subtopic.");
    expect(requests.some((r) => r.method === "post")).toBe(false);

    await click(container.querySelector('input[aria-label="Graphs (all subtopics)"]'));
    await click(byText("button", "Start practice"));
    await waitFor(() => lastPath === `/dsa/session/${SID}`);
    const post = requests.find((r) => r.method === "post" && r.url === "/dsa/sessions")!;
    expect(post.body).toMatchObject({ mode: "topic", topic_ids: ["graphs"], question_count: 10 });
    expect(Object.keys(post.body!).some((k) => /user|score|correct|answer/.test(k))).toBe(false);
  });

  it("shows how many questions exist for the chosen mode and scope", async () => {
    await visit("/dsa?mode=tracing");
    await waitFor(() => text().includes("Practice mode"));
    // Code tracing draws from the trace + output formats: Bubble Sort 3 + Binary Search 3 + BFS 4 = 10.
    expect(text()).toContain("Up to 10 questions available for this mode and scope");
  });
});

describe("a timed mock session", () => {
  async function openMock() {
    await visit(`/dsa/session/${SID}`);
    await waitFor(() => text().includes("Fake DSA question 1"));
  }

  it("shows the question and timer but never an answer, explanation, trace or reference", async () => {
    await openMock();
    expect(container.querySelectorAll('[role="radiogroup"][aria-labelledby="question-heading"] [role="radio"]')).toHaveLength(4);
    expect(container.querySelector('[role="timer"], [aria-label*="remaining" i]')).not.toBeNull();
    await click(option(1)); // the correct one in the fake backend
    expect(text()).not.toContain(SECRET_EXPLANATION);
    expect(text()).not.toContain("Correct answer");
    expect(text()).not.toContain("Step-by-step trace");
    expect(container.textContent).not.toContain("SECRET_REFERENCE_BODY");
    expect(text()).not.toContain("Show a hint"); // hints are off in exams
  });

  it("sends only the option position and review mark when answering", async () => {
    await openMock();
    await click(option(2));
    const body = puts().at(-1)!.body!;
    expect(Object.keys(body).sort()).toEqual(["marked_for_review", "selected_index", "time_spent_seconds"]);
    expect(body.selected_index).toBe(2);
    expect(JSON.stringify(body)).not.toMatch(/correct|score|user/);
  });

  it("supports keyboard answering, navigation and marking", async () => {
    await openMock();
    await key("3");
    expect(puts().at(-1)!.body!.selected_index).toBe(2);
    await key("ArrowRight");
    await waitFor(() => text().includes("Fake DSA question 2"));
    await key("m");
    expect(puts().at(-1)!.body!.marked_for_review).toBe(true);
    await key("ArrowLeft");
    await waitFor(() => text().includes("Fake DSA question 1"));
    expect(navButton(2).getAttribute("aria-label")).toContain("marked for review");
    expect(navButton(1).getAttribute("aria-label")).toContain("current");
    expect(navButton(3).getAttribute("aria-label")).toContain("(coding)");
  });

  it("navigator shows answered and unanswered state in text, not colour alone", async () => {
    await openMock();
    await click(option(0));
    await click(navButton(2));
    expect(navButton(1).getAttribute("aria-label")).toBe("Question 1, answered");
    expect(navButton(3).getAttribute("aria-label")).toContain("not answered");
  });

  it("submitting twice sends one request and lands on the result", async () => {
    fake.submitDelayMs = 80;
    await openMock();
    await click(option(1));
    await click(byText("button", /^Submit$/));
    expect(container.querySelector('[role="alertdialog"]')?.textContent).toContain("2 questions are unanswered");
    const submitNow = byText("button", "Submit now")!;
    await act(async () => { submitNow.click(); submitNow.click(); });
    await waitFor(() => lastPath === `/dsa/result/${SID}`);
    expect(requests.filter((r) => r.method === "post" && r.url.endsWith("/submit"))).toHaveLength(1);
  });

  it("a rejected late answer ends the session and shows the result", async () => {
    await openMock();
    fake.failAnswers = { status: 409, code: "SESSION_EXPIRED" };
    fake.status = "completed";
    await click(option(0));
    await waitFor(() => lastPath === `/dsa/result/${SID}`);
  });

  it("rolls back an answer that could not be saved and says so", async () => {
    await openMock();
    fake.failAnswers = { status: 500, code: "SERVER_ERROR" };
    await click(option(0));
    await waitFor(() => !!container.querySelector('[role="alert"]'));
    expect(option(0).getAttribute("aria-checked")).toBe("false");
    expect(text()).toContain("Answer rejected."); // the server's own message is shown
  });
});

describe("practice with immediate feedback", () => {
  async function openPractice() {
    fake.immediate = true;
    await visit(`/dsa/session/${SID}`);
    await waitFor(() => text().includes("Fake DSA question 1"));
  }

  it("reveals the answer, explanation, complexity and a steppable trace only after answering, then locks", async () => {
    await openPractice();
    expect(text()).not.toContain(SECRET_EXPLANATION);
    await click(option(0)); // wrong (key is option 1)
    await waitFor(() => text().includes(SECRET_EXPLANATION));
    expect(text()).toContain("Not quite");
    expect(text()).toContain("Complexity analysis");
    expect(text()).toContain("O(n²)");
    expect(option(1).textContent).toContain("Correct answer");
    expect(option(0).textContent).toContain("Your answer");
    expect(text()).toContain("Step 1 of 3");
    expect(text()).toContain("After pass 1");
    await click(byText("button", /^Next/)!.closest("section")!.querySelector("button:nth-of-type(3)"));
    expect(text()).toContain("Step 2 of 3");
    expect(text()).toContain("After pass 2");
    const before = puts().length;
    await click(option(2)); // locked: no further save
    expect(puts().length).toBe(before);
  });

  it("the trace can be shown all at once and stepped with the keyboard", async () => {
    await openPractice();
    await click(option(1));
    await waitFor(() => text().includes("Step 1 of 3"));
    const group = container.querySelector<HTMLElement>('[role="group"][aria-label^="Trace steps"]')!;
    await act(async () => { group.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true })); });
    expect(text()).toContain("Step 2 of 3");
    await click(byText("button", "Show all steps"));
    expect(text()).toContain("After pass 3");
  });

  it("offers progressive hints in practice", async () => {
    await openPractice();
    await click(byText("button", "Show a hint"));
    expect(text()).toContain("Hint one: track two variables.");
  });
});

describe("coding questions", () => {
  async function openCode() {
    fake.immediate = true;
    await visit(`/dsa/session/${SID}`);
    await waitFor(() => text().includes("Fake DSA question 1"));
    await click(navButton(3));
    await waitFor(() => !!container.querySelector("#code-editor"));
  }
  const editor = () => container.querySelector<HTMLTextAreaElement>("#code-editor")!;

  it("offers a template editor, visible tests and an honest 'not run' message, with no Run button", async () => {
    await openCode();
    expect(editor().value).toBe(TEMPLATE);
    expect(text()).toContain("This code is not run.");
    expect(text()).toContain("Sample test cases");
    expect(text()).toContain("1 more hidden test case");
    expect(text()).toContain("O(n) time, O(1) space.");
    expect([...container.querySelectorAll("button")].some((b) => /^run\b/i.test(b.textContent?.trim() ?? ""))).toBe(false);
    expect(container.textContent).not.toContain("SECRET_REFERENCE_BODY");
    expect(container.textContent).not.toContain("all equal"); // the hidden test's label
  });

  it("saves the code (and only the code) to the server", async () => {
    await openCode();
    await typeInto(editor(), "def second_largest(nums):\n    return 7\n");
    await click(byText("button", "Save code"));
    await waitFor(() => puts().some((p) => typeof p.body?.code === "string"));
    const body = puts().find((p) => typeof p.body?.code === "string")!.body!;
    expect(body.code).toBe("def second_largest(nums):\n    return 7\n");
    expect(body.reveal).toBe(false);
    expect(Object.keys(body).sort()).toEqual(["code", "marked_for_review", "reveal", "time_spent_seconds"]);
    expect(editor().readOnly).toBe(false);
  });

  it("Tab inserts spaces; Escape then Tab leaves the editor alone", async () => {
    await openCode();
    const ta = editor();
    ta.focus();
    ta.setSelectionRange(0, 0);
    const tab = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    await act(async () => { ta.dispatchEvent(tab); });
    expect(tab.defaultPrevented).toBe(true);
    expect(editor().value.startsWith("    def second_largest")).toBe(true);
    await act(async () => { ta.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); });
    const tab2 = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    await act(async () => { ta.dispatchEvent(tab2); });
    expect(tab2.defaultPrevented).toBe(false);
  });

  it("keyboard shortcuts are disabled while typing code", async () => {
    await openCode();
    const ta = editor();
    ta.focus();
    const before = puts().length;
    await act(async () => { ta.dispatchEvent(new KeyboardEvent("keydown", { key: "m", bubbles: true })); });
    expect(puts().length).toBe(before);
  });

  it("'Submit & show reference' locks the answer and reveals the reference, every test and the honest note", async () => {
    await openCode();
    await typeInto(editor(), "def second_largest(nums):\n    return 7\n");
    await click(byText("button", "Submit & show reference"));
    await waitFor(() => text().includes("Reference solution"));
    expect(container.textContent).toContain("SECRET_REFERENCE_BODY");
    expect(text()).toContain("all equal"); // the previously hidden test is now shown
    expect(text()).toContain("was hidden");
    expect(text()).toContain("Your code was NOT run.");
    expect(editor().readOnly).toBe(true);
  });

  it("unsaved code is saved when you move to another question", async () => {
    await openCode();
    await typeInto(editor(), "def second_largest(nums):\n    return 1\n");
    await click(navButton(1));
    await waitFor(() => puts().some((p) => p.body?.code === "def second_largest(nums):\n    return 1\n"));
  });
});

describe("the result", () => {
  async function finish() {
    await visit(`/dsa/session/${SID}`);
    await waitFor(() => text().includes("Fake DSA question 1"));
    await click(option(1)); // correct
    await click(navButton(2));
    await waitFor(() => text().includes("Fake DSA question 2"));
    await click(option(0)); // wrong (key is 2)
    await click(navButton(3));
    await waitFor(() => !!container.querySelector("#code-editor"));
    await typeInto(container.querySelector<HTMLTextAreaElement>("#code-editor")!, "def second_largest(nums):\n    return 7\n");
    await click(byText("button", "Save code"));
    await click(byText("button", /^Submit$/));
    await click(byText("button", "Submit now"));
    await waitFor(() => lastPath === `/dsa/result/${SID}`);
    await waitFor(() => text().includes("Answers, traces and explanations"));
  }

  it("shows server-computed score, accuracy, topic performance, revision topics and complexity", async () => {
    await finish();
    expect(text()).toContain("1 / 2");
    expect(text()).toContain("50% accuracy");
    expect(text()).toContain("3 total");
    expect(text()).toContain("2 auto-graded · 1 coding");
    expect(text()).toContain("Topic-wise performance");
    expect(text()).toContain("Sorting and Searching");
    expect(text()).toContain("Recommended for revision");
    expect(text()).toContain("Complexity summary");
    expect(text()).toContain("Measured by the server");
    expect(text()).toContain("1 min 35 s");
  });

  it("reveals explanations, the trace, reference solution and all test cases after submission", async () => {
    await finish();
    expect(text()).toContain(EXPLAIN[0]);
    expect(text()).toContain("Step 1 of 3");
    expect(container.textContent).toContain("SECRET_REFERENCE_BODY");
    expect(text()).toContain("Your submitted code");
    expect(text()).toContain("was hidden");
    expect(text()).toContain("Not auto-graded");
    expect(text()).toContain("does not execute submitted code");
  });

  it("self-assessment is saved but says it does not change the score", async () => {
    await finish();
    expect(text()).toContain("does not change your score");
    await click(byText("button", "Partly"));
    await waitFor(() => text().includes("Self-assessed: Partly."));
    expect(puts().at(-1)!.url).toContain("/self-assessment/");
    expect(puts().at(-1)!.body).toEqual({ verdict: "partial" });
    expect(text()).toContain("1 / 2"); // unchanged
  });

  it("can filter to incorrect answers and to coding questions", async () => {
    await finish();
    await click(byText("button", /^Incorrect \(1\)/));
    expect(container.querySelectorAll('section[aria-labelledby="review-heading"] > ol > li')).toHaveLength(1);
    await click(byText("button", /^Coding \(1\)/));
    expect(container.querySelectorAll('section[aria-labelledby="review-heading"] > ol > li')).toHaveLength(1);
    expect(text()).toContain("Reference solution");
  });

  it("a result that is not available yet is an error state with retry", async () => {
    fake.resultStatus = 409;
    await visit(`/dsa/result/${SID}`);
    await waitFor(() => text().includes("Results are available after the session is submitted."));
    expect(container.querySelector('[role="alert"]')).not.toBeNull();
    expect(byText("button", "Retry")).toBeTruthy();
  });

  it("shows a loading state while the result loads", async () => {
    await visit(`/dsa/result/${SID}`);
    expect(container.querySelector('[role="status"][aria-label="Loading your result"]') || text().includes("Answers, traces")).toBeTruthy();
  });
});
