// @vitest-environment jsdom
/**
 * Phase 23 UI tests. The REAL <App /> (routes, guards, layout, aptitude pages, store, service) runs in jsdom;
 * only HTTP is faked, by an in-memory aptitude backend that keeps its own answer key. That lets the tests prove
 * what the browser sends (never a score, user id or answer key) and what it shows at each stage.
 */
import { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter, useLocation } from "react-router-dom";
import { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "@/App";
import { api } from "@/services/api";
import { clearStoredToken } from "@/services/tokenStorage";
import { useAptitudeStore } from "@/store/aptitudeStore";
import { useAuthStore } from "@/store/authStore";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const SID = "a".repeat(24);
const KEY = [1, 0, 2]; // displayed correct option per question (the fake server's secret)
const QIDS = ["apt-0000000001", "apt-0000000002", "apt-0000000003"];
const EXPLAIN = ["Because 7 cycles 7, 9, 3, 1.", "HCF is 6.", "Product over sum."];

interface Fake {
  syllabusStatus: number;
  syllabusDelayMs: number;
  totalQuestions: number;
  progress: "empty" | "data";
  expiresInMs: number | null;
  immediate: boolean;
  answers: Record<string, { selected: number | null; marked: boolean }>;
  status: "in_progress" | "completed";
  autoSubmitted: boolean;
  failAnswers: false | { status: number; code: string };
  resultStatus: number;
  submitDelayMs: number;
}
let fake: Fake;
let requests: { method: string; url: string; body: unknown }[] = [];
let root: Root;
let container: HTMLDivElement;
let lastPath = "";

const fresh = (): Fake => ({ syllabusStatus: 200, syllabusDelayMs: 0, totalQuestions: 13, progress: "empty", expiresInMs: 1_800_000, immediate: false, answers: {}, status: "in_progress", autoSubmitted: false, failAnswers: false, resultStatus: 200, submitDelayMs: 0 });

const SYLLABUS = (total: number) => ({
  totals: { topics: 2, subtopics: 4, subtopics_implemented: total ? 2 : 0, questions: total, min_questions_per_subtopic: 4 },
  topics: [
    { id: "number-system", code: "B", title: "Number System", section: "Quantitative Aptitude", summary: "Properties of numbers.", question_count: total ? 8 : 0, items: [], subtopics_implemented: 1, subtopics_total: 3, status: "partial", subtopics: [
      { id: "unit-digit", title: "Unit digit calculation", question_count: total ? 6 : 0, by_difficulty: { easy: 3, medium: 2, hard: 1 }, status: "implemented" },
      { id: "hcf-lcm", title: "HCF and LCM", question_count: total ? 2 : 0, by_difficulty: { easy: 2, medium: 0, hard: 0 }, status: "partial" },
      { id: "factorials", title: "Factorials", question_count: 0, by_difficulty: { easy: 0, medium: 0, hard: 0 }, status: "missing" }] },
    { id: "percentage", code: "D", title: "Percentage", section: "Quantitative Aptitude", summary: "Percent problems.", question_count: total ? 5 : 0, items: [], subtopics_implemented: 1, subtopics_total: 1, status: "implemented", subtopics: [
      { id: "percentage-calculations", title: "Percentage calculations", question_count: total ? 5 : 0, by_difficulty: { easy: 5, medium: 0, hard: 0 }, status: "implemented" }] },
  ],
});

const baseQuestion = (i: number) => ({
  question_id: QIDS[i], topic_id: "number-system", subtopic_id: "unit-digit", question_type: "direct", difficulty: "easy", statement: `Fake question number ${i + 1}: pick the right option.`,
  options: ["Option A", "Option B", "Option C", "Option D"].map((o) => `${o} (q${i + 1})`), est_time_seconds: 30, data: null,
});

function sessionPayload() {
  const now = Date.now();
  return {
    session_id: SID, mode: fake.immediate ? "topic" : "timed_mock", status: fake.status, difficulty: null, question_count: 3, requested_count: 3, topic_ids: ["number-system"],
    immediate_feedback: fake.immediate, exam_mode: !fake.immediate, started_at: new Date(now).toISOString(), expires_at: fake.expiresInMs === null ? null : new Date(now + fake.expiresInMs).toISOString(),
    server_time: new Date(now).toISOString(), remaining_seconds: fake.expiresInMs === null ? null : Math.max(0, Math.ceil(fake.expiresInMs / 1000)), timer_minutes: fake.expiresInMs === null ? null : 30,
    scoring_policy: "Each correct answer scores 1 mark; no negative marking.",
    questions: QIDS.map((id, i) => {
      const a = fake.answers[id];
      const locked = fake.immediate && !!a && a.selected !== null;
      return { ...baseQuestion(i), selected_index: a?.selected ?? null, marked_for_review: a?.marked ?? false, locked,
        feedback: locked ? { is_correct: a!.selected === KEY[i], correct_index: KEY[i], explanation: EXPLAIN[i], formula: null } : null };
    }),
  };
}

function resultPayload() {
  const questions = QIDS.map((id, i) => {
    const sel = fake.answers[id]?.selected ?? null;
    return { question_id: id, topic_id: "number-system", subtopic_id: "unit-digit", difficulty: "easy", statement: baseQuestion(i).statement, options: baseQuestion(i).options, data: null,
      selected_index: sel, correct_index: KEY[i], outcome: sel === null ? "unanswered" : sel === KEY[i] ? "correct" : "incorrect", explanation: EXPLAIN[i], formula: null, marked_for_review: fake.answers[id]?.marked ?? false, time_spent_seconds: 0 };
  });
  const correct = questions.filter((q) => q.outcome === "correct").length;
  const incorrect = questions.filter((q) => q.outcome === "incorrect").length;
  return {
    session_id: SID, mode: "timed_mock", status: "completed", total_questions: 3, correct, incorrect, unanswered: 3 - correct - incorrect, score: correct, accuracy: Math.round((1000 * correct) / 3) / 10,
    time_taken_seconds: 95, average_seconds_per_question: 31.7, auto_submitted: fake.autoSubmitted, started_at: new Date().toISOString(), finished_at: new Date().toISOString(),
    topic_performance: [{ topic_id: "number-system", topic_title: "Number System", total: 3, correct, incorrect, unanswered: 3 - correct - incorrect, accuracy: Math.round((1000 * correct) / 3) / 10 }],
    revision_topics: correct < 3 ? [{ topic_id: "number-system", topic_title: "Number System", accuracy: 33.3, subtopics: [{ subtopic_id: "unit-digit", title: "Unit digit calculation" }] }] : [],
    questions, scoring_policy: "Each correct answer scores 1 mark; no negative marking.",
  };
}

const PROGRESS = () => fake.progress === "empty"
  ? { sessions_completed: 0, questions_presented: 0, questions_answered: 0, correct: 0, incorrect: 0, unanswered: 0, accuracy: 0, average_seconds_per_question: null, topic_accuracy: [], difficulty_accuracy: [], recent_sessions: [], trend: [], improvement_points: null, weak_topics: [] }
  : { sessions_completed: 2, questions_presented: 20, questions_answered: 18, correct: 9, incorrect: 9, unanswered: 2, accuracy: 50, average_seconds_per_question: 42, topic_accuracy: [{ topic_id: "number-system", topic_title: "Number System", answered: 18, correct: 9, presented: 20, accuracy: 50 }],
      difficulty_accuracy: [{ difficulty: "easy", answered: 18, correct: 9, accuracy: 50 }], recent_sessions: [{ session_id: SID, mode: "timed_mock", score: 9, total: 18, accuracy: 50, time_taken_seconds: 600, finished_at: new Date().toISOString() }],
      trend: [{ session_id: SID, accuracy: 40, finished_at: "x" }, { session_id: SID, accuracy: 60, finished_at: "y" }], improvement_points: null,
      weak_topics: [{ topic_id: "number-system", topic_title: "Number System", answered: 18, correct: 5, accuracy: 28, reason: "28% accuracy over 18 answered questions (below 60%).", weak_subtopics: [] }] };

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
  if (url === "/aptitude/syllabus" && fake.syllabusDelayMs) await new Promise((r) => setTimeout(r, fake.syllabusDelayMs));
  if (url === "/aptitude/syllabus") return fake.syllabusStatus === 200 ? respond(config, ok(SYLLABUS(fake.totalQuestions))) : respond(config, err("Syllabus service is down.", "SERVICE_UNAVAILABLE"), fake.syllabusStatus);
  if (url === "/aptitude/progress") return respond(config, ok(PROGRESS()));
  if (url === "/aptitude/recommendations") return respond(config, ok({ has_history: fake.progress === "data", weak_topics: PROGRESS().weak_topics, incorrect_question_count: 0, message: "ok", thresholds: { min_answered: 5, accuracy_below: 60 } }));
  if (method === "post" && url === "/aptitude/sessions") return respond(config, ok(sessionPayload()), 201);
  if (method === "get" && url === `/aptitude/sessions/${SID}`) return respond(config, ok(sessionPayload()));
  if (method === "put" && url.startsWith(`/aptitude/sessions/${SID}/answers/`)) {
    if (fake.failAnswers) return respond(config, err("Answer rejected.", fake.failAnswers.code), fake.failAnswers.status);
    const qid = url.split("/").pop()!;
    fake.answers[qid] = { selected: body.selected_index, marked: body.marked_for_review };
    const i = QIDS.indexOf(qid);
    const locked = fake.immediate && body.selected_index !== null;
    return respond(config, ok({ question_id: qid, selected_index: body.selected_index, marked_for_review: body.marked_for_review, locked, remaining_seconds: 100,
      feedback: locked ? { is_correct: body.selected_index === KEY[i], correct_index: KEY[i], explanation: EXPLAIN[i], formula: null } : null }));
  }
  if (method === "post" && url === `/aptitude/sessions/${SID}/submit`) {
    if (fake.submitDelayMs) await new Promise((r) => setTimeout(r, fake.submitDelayMs));
    fake.status = "completed";
    return respond(config, ok(resultPayload()));
  }
  if (method === "get" && url === `/aptitude/sessions/${SID}/result`) return fake.resultStatus === 200 ? respond(config, ok(resultPayload())) : respond(config, err("Results are available after the session is submitted.", "SESSION_NOT_FINISHED"), fake.resultStatus);
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

beforeEach(() => {
  fake = fresh();
  requests = [];
  lastPath = "";
  window.scrollTo = vi.fn();
  window.matchMedia = window.matchMedia ?? ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, onchange: null, dispatchEvent: () => false }) as MediaQueryList);
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
  // jsdom has no Web Animations API; AppLayout animates route changes with element.animate().
  (window.HTMLElement.prototype as unknown as { animate: unknown }).animate = vi.fn(() => ({ cancel() {}, finished: Promise.resolve() }));
  (globalThis as Record<string, unknown>).ResizeObserver ??= class { observe() {} unobserve() {} disconnect() {} };
  (globalThis as Record<string, unknown>).IntersectionObserver ??= class { observe() {} unobserve() {} disconnect() {} takeRecords() { return []; } };
  api.defaults.adapter = handler as never;
  useAuthStore.setState({ isAuthenticated: true, user: { id: "u1", name: "Ada Lovelace", email: "ada@example.com" }, accessToken: "tok", isLoading: false, loadCurrentUser: async () => undefined });
  useAptitudeStore.getState().reset();
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
  it("shows a loading state, then the five practice modes", async () => {
    fake.syllabusDelayMs = 150;
    await visit("/aptitude");
    await waitFor(() => !!container.querySelector('[role="status"][aria-label="Loading practice options"]')); // lazy page mounts, then waits for the syllabus
    await waitFor(() => text().includes("Practice mode"));
    const modes = [...container.querySelectorAll('[role="radiogroup"][aria-label="Practice mode"] [role="radio"]')].map((b) => b.textContent ?? "");
    expect(modes).toHaveLength(5);
    for (const t of ["Topic practice", "Scenario practice", "Timed mock test", "Mixed practice", "Weak topic practice"]) expect(modes.some((m) => m.includes(t))).toBe(true);
    expect(container.querySelector("h1")?.textContent).toContain("Aptitude Practice");
    expect(text()).toContain("no negative marking");
  });

  it("appears in the sidebar navigation", async () => {
    await visit("/aptitude");
    await waitFor(() => text().includes("Practice mode"));
    expect([...container.querySelectorAll("a")].some((a) => a.getAttribute("href") === "/aptitude" && a.textContent?.includes("Aptitude Practice"))).toBe(true);
  });

  it("shows an error with a working retry when the syllabus cannot load", async () => {
    fake.syllabusStatus = 503;
    await visit("/aptitude");
    await waitFor(() => text().includes("Syllabus service is down."));
    expect(container.querySelector('[role="alert"]')).not.toBeNull();
    fake.syllabusStatus = 200;
    await click(byText("button", "Retry"));
    await waitFor(() => text().includes("Practice mode"));
  });

  it("shows an honest empty state when the question bank is empty", async () => {
    fake.totalQuestions = 0;
    await visit("/aptitude");
    await waitFor(() => text().includes("No questions are available yet"));
    expect(text()).not.toContain("Start practice");
  });

  it("syllabus tab reports real coverage, including subtopics with no questions", async () => {
    await visit("/aptitude?tab=syllabus");
    await waitFor(() => text().includes("Syllabus coverage"));
    expect(text()).toContain("2 of 4 subtopics ready");
    expect(text()).toContain("13 questions in the bank");
    expect(text()).toContain("No questions yet");
    expect(text()).toContain("Few questions");
    expect(text()).toContain("Not available"); // no Practice link for an empty subtopic
    const links = [...container.querySelectorAll("a")].map((a) => a.getAttribute("href"));
    expect(links).toContain("/aptitude?mode=topic&subtopic=unit-digit");
    expect(links).not.toContain("/aptitude?mode=topic&subtopic=factorials");
  });

  it("progress tab shows an empty state without inventing numbers", async () => {
    await visit("/aptitude?tab=progress");
    await waitFor(() => text().includes("No aptitude practice recorded yet"));
    expect(text()).toContain("Nothing is estimated");
  });

  it("progress tab shows real analytics and weak-topic reasons", async () => {
    fake.progress = "data";
    await visit("/aptitude?tab=progress");
    await waitFor(() => text().includes("Revision recommendations"));
    expect(text()).toContain("28% accuracy over 18 answered questions");
    expect(text()).toContain("Sessions completed");
    expect(text()).not.toContain("Complete at least two sessions"); // two trend points exist
  });

  it("tabs are keyboard operable", async () => {
    await visit("/aptitude");
    await waitFor(() => text().includes("Practice mode"));
    const tab = container.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')!;
    await act(async () => { tab.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true })); });
    await waitFor(() => container.querySelector('[role="tab"][aria-selected="true"]')?.textContent === "Syllabus");
  });
});

describe("setup form", () => {
  it("requires a topic for topic practice and sends nothing", async () => {
    await visit("/aptitude");
    await waitFor(() => text().includes("Practice mode"));
    await click(byText("button", "Start practice"));
    expect(text()).toContain("Choose at least one topic or subtopic.");
    expect(requests.filter((r) => r.method === "post")).toHaveLength(0);
  });

  it("a mock test requires a time limit and says it auto-submits", async () => {
    await visit("/aptitude?mode=timed_mock");
    await waitFor(() => text().includes("Time limit (minutes)"));
    expect(text()).toContain("submitted automatically when time runs out");
    expect(text()).not.toContain("Show the answer and explanation after each question");
    expect(container.querySelector<HTMLInputElement>("#apt-timer")?.value).toBe("30");
  });

  it("warns when fewer questions match than requested", async () => {
    await visit("/aptitude?mode=topic&subtopic=hcf-lcm");
    await waitFor(() => text().includes("questions available") || text().includes("match"));
    const count = container.querySelector<HTMLInputElement>("#apt-count")!;
    expect(count.value).toBe("10");
    expect(text()).toContain("Only 2 questions match - the session will be that long.");
  });

  it("starts a session with a clean request and opens the runner", async () => {
    await visit("/aptitude");
    await waitFor(() => text().includes("Practice mode"));
    await click(container.querySelector('input[aria-label="Number System (all subtopics)"]'));
    await click(byText("button", "Start practice"));
    await waitFor(() => lastPath === `/aptitude/session/${SID}`);
    const post = requests.find((r) => r.method === "post" && r.url === "/aptitude/sessions")!;
    expect(post.body).toMatchObject({ mode: "topic", topic_ids: ["number-system"], subtopic_ids: [], question_count: 10 });
    expect(Object.keys(post.body as object)).not.toEqual(expect.arrayContaining(["user_id", "score"]));
    await waitFor(() => text().includes("Question 1 of 3"));
  });
});

describe("question runner", () => {
  async function openMock() {
    await visit(`/aptitude/session/${SID}`);
    await waitFor(() => text().includes("Question 1 of 3"));
  }

  it("renders the question, four options, a visible timer and a navigator - with no answer shown", async () => {
    await openMock();
    expect(text()).toContain("Fake question number 1");
    expect(container.querySelectorAll('[role="radiogroup"][aria-labelledby="question-heading"] [role="radio"]')).toHaveLength(4);
    expect(container.querySelector('[role="timer"]')?.textContent).toMatch(/^(29:5\d|30:00)$/);
    expect(container.querySelectorAll('nav[aria-label="Question navigator"] li')).toHaveLength(3);
    expect(text()).not.toContain("Correct answer");
    expect(text()).not.toContain(EXPLAIN[0]);
    expect(container.innerHTML).not.toContain("correct_index");
    expect(container.querySelector(".reveal")).toBeNull(); // no entrance animation while answering
  });

  it("saves an answer by clicking and sends only position, mark flag and time", async () => {
    await openMock();
    await click(option(2));
    await waitFor(() => puts().length === 1);
    expect(option(2).getAttribute("aria-checked")).toBe("true");
    expect(puts()[0].url).toBe(`/aptitude/sessions/${SID}/answers/${QIDS[0]}`);
    expect(Object.keys(puts()[0].body as object).sort()).toEqual(["marked_for_review", "selected_index", "time_spent_seconds"]);
    expect((puts()[0].body as { selected_index: number }).selected_index).toBe(2);
    expect(text()).not.toContain(EXPLAIN[0]); // exam mode: nothing revealed
  });

  it("supports keyboard answering, navigation and marking", async () => {
    await openMock();
    await key("2");
    await waitFor(() => puts().length === 1);
    expect(option(1).getAttribute("aria-checked")).toBe("true");
    await key("ArrowRight");
    await waitFor(() => text().includes("Question 2 of 3"));
    await key("d");
    await waitFor(() => puts().length === 2);
    expect((puts()[1].body as { selected_index: number }).selected_index).toBe(3);
    await key("m");
    await waitFor(() => puts().length === 3);
    expect((puts()[2].body as { marked_for_review: boolean }).marked_for_review).toBe(true);
    expect(container.querySelector('nav[aria-label="Question navigator"] button[aria-label^="Question 2"]')?.getAttribute("aria-label")).toContain("marked for review");
    await key("ArrowLeft");
    await waitFor(() => text().includes("Question 1 of 3"));
    expect(option(1).getAttribute("aria-checked")).toBe("true"); // answer preserved while navigating
  });

  it("marks for review with the button and shows it in the navigator", async () => {
    await openMock();
    await click(byText("button", "Mark for review"));
    await waitFor(() => puts().length === 1);
    expect(byText("button", "Marked for review")?.getAttribute("aria-pressed")).toBe("true");
    expect(container.querySelector('nav button[aria-label^="Question 1"]')?.getAttribute("aria-label")).toContain("marked for review");
    expect(text()).toContain("Marked");
  });

  it("jumps between questions from the navigator", async () => {
    await openMock();
    await click(container.querySelector('nav[aria-label="Question navigator"] button[aria-label^="Question 3"]'));
    await waitFor(() => text().includes("Question 3 of 3"));
    expect(container.querySelector('nav button[aria-current="step"]')?.textContent).toBe("3");
  });

  it("asks for confirmation, reports what is unanswered, and submits exactly once", async () => {
    fake.submitDelayMs = 80;
    await openMock();
    await click(option(KEY[0]));
    await waitFor(() => puts().length === 1);
    await click(byText("button", /^Submit$/));
    expect(container.querySelector('[role="alertdialog"]')).not.toBeNull();
    expect(text()).toContain("2 questions are unanswered");
    expect(requests.filter((r) => r.url.endsWith("/submit"))).toHaveLength(0);
    await click(byText("button", "Keep working"));
    expect(container.querySelector('[role="alertdialog"]')).toBeNull();
    await click(byText("button", /^Submit$/));
    const confirm = byText("button", "Submit now")!;
    await act(async () => { confirm.click(); confirm.click(); confirm.click(); }); // rapid triple click
    await waitFor(() => lastPath === `/aptitude/result/${SID}`);
    expect(requests.filter((r) => r.url.endsWith("/submit"))).toHaveLength(1);
  });

  it("shows the result: score, counts, time, topic breakdown, correct answers and explanations", async () => {
    await openMock();
    await click(option(KEY[0]));
    await waitFor(() => puts().length === 1);
    await key("ArrowRight");
    await key("2"); // question 2's key is option index 0, so index 1 is a wrong answer
    await waitFor(() => puts().length === 2);
    await click(byText("button", /^Submit$/));
    await click(byText("button", "Submit now"));
    await waitFor(() => text().includes("Answers and explanations"));
    const score = text().match(/Score(\d) \/ 3/);
    expect(score?.[1]).toBe("1");
    expect(text()).toContain("Topic-wise performance");
    expect(text()).toContain("Number System");
    expect(text()).toContain("Recommended for revision");
    expect(text()).toContain("Unit digit calculation");
    expect(text()).toContain(EXPLAIN[0]);
    expect(text()).toContain("no negative marking");
    expect(text()).toContain("Measured by the server");
    expect(text()).toContain("Not answered");
    expect(container.querySelectorAll('[role="progressbar"]').length).toBeGreaterThan(1);
  });

  it("result filters narrow the review list", async () => {
    await openMock();
    await click(option(KEY[0]));
    await waitFor(() => puts().length === 1);
    await click(byText("button", /^Submit$/));
    await click(byText("button", "Submit now"));
    await waitFor(() => text().includes("Answers and explanations"));
    expect(container.querySelectorAll("section[aria-labelledby=review-heading] ol > li")).toHaveLength(3);
    await click(byText("button", /^Unanswered/));
    expect(container.querySelectorAll("section[aria-labelledby=review-heading] ol > li")).toHaveLength(2);
    await click(byText("button", /^Marked/));
    expect(text()).toContain("No questions in this view.");
  });

  it("reverts the choice and shows an alert when saving fails", async () => {
    await openMock();
    fake.failAnswers = { status: 500, code: "INTERNAL_ERROR" };
    await click(option(0));
    await waitFor(() => !!container.querySelector('[role="alert"]'));
    expect(option(0).getAttribute("aria-checked")).toBe("false");
    expect(text()).toContain("Answer rejected.");
  });

  it("moves to the result when the server says the time is up", async () => {
    await openMock();
    fake.failAnswers = { status: 409, code: "SESSION_EXPIRED" };
    fake.status = "completed";
    fake.autoSubmitted = true;
    await click(option(1));
    await waitFor(() => lastPath === `/aptitude/result/${SID}`);
    await waitFor(() => text().includes("submitted automatically"));
  });
});

describe("timer", () => {
  it("auto-submits and shows the result when the countdown is already over", async () => {
    fake.expiresInMs = -2000;
    fake.autoSubmitted = true;
    await visit(`/aptitude/session/${SID}`);
    await waitFor(() => lastPath === `/aptitude/result/${SID}`);
    await waitFor(() => text().includes("Time ran out, so this test was submitted automatically"));
    expect(requests.filter((r) => r.url.endsWith("/submit"))).toHaveLength(1);
  });

  it("counts down once a second while the test is open", async () => {
    fake.expiresInMs = 125_000;
    await visit(`/aptitude/session/${SID}`);
    await waitFor(() => /2:0\d|2:1\d|2:04/.test(container.querySelector('[role="timer"]')?.textContent ?? ""));
    const first = container.querySelector('[role="timer"]')!.textContent;
    await waitFor(() => container.querySelector('[role="timer"]')!.textContent !== first, 3500);
  });

  it("untimed practice shows no countdown", async () => {
    fake.expiresInMs = null;
    fake.immediate = true;
    await visit(`/aptitude/session/${SID}`);
    await waitFor(() => text().includes("Question 1 of 3"));
    expect(container.querySelector('[role="timer"]')).toBeNull();
  });
});

describe("practice with immediate feedback", () => {
  it("reveals the answer and explanation after answering, and locks it", async () => {
    fake.immediate = true;
    fake.expiresInMs = null;
    await visit(`/aptitude/session/${SID}`);
    await waitFor(() => text().includes("Question 1 of 3"));
    expect(text()).not.toContain(EXPLAIN[0]);
    await click(option(3));
    await waitFor(() => text().includes(EXPLAIN[0]));
    expect(text()).toContain("Not quite");
    expect(text()).toContain("Correct answer");
    expect(text()).toContain("Your answer");
    const before = puts().length;
    await click(option(KEY[0]));
    expect(puts().length).toBe(before); // locked: no second save
    expect(option(3).getAttribute("aria-checked")).toBe("true");
  });
});

describe("refresh and recovery", () => {
  it("resumes a refreshed session on the first unanswered question with saved answers intact", async () => {
    fake.answers[QIDS[0]] = { selected: 2, marked: false };
    fake.answers[QIDS[1]] = { selected: 0, marked: true };
    await visit(`/aptitude/session/${SID}`);
    await waitFor(() => text().includes("Question 3 of 3"));
    expect(text()).toContain("2 of 3 answered");
    await click(container.querySelector('nav button[aria-label^="Question 1"]'));
    await waitFor(() => text().includes("Question 1 of 3"));
    expect(option(2).getAttribute("aria-checked")).toBe("true");
  });

  it("opens the result when a finished session is revisited", async () => {
    fake.status = "completed";
    fake.answers[QIDS[0]] = { selected: KEY[0], marked: false };
    await visit(`/aptitude/session/${SID}`);
    await waitFor(() => lastPath === `/aptitude/result/${SID}`);
    await waitFor(() => text().includes("Answers and explanations"));
  });

  it("shows a clear error with a way back when a session cannot be found", async () => {
    await visit("/aptitude/session/" + "b".repeat(24));
    await waitFor(() => !!container.querySelector('[role="alert"]'));
    expect([...container.querySelectorAll("a")].some((a) => a.getAttribute("href") === "/aptitude")).toBe(true);
  });

  it("result page explains when results are not ready", async () => {
    fake.resultStatus = 409;
    await visit(`/aptitude/result/${SID}`);
    await waitFor(() => text().includes("Results are available after the session is submitted."));
    expect(container.querySelector('[role="alert"]')).not.toBeNull();
  });
});
