import { beforeEach, describe, expect, it, vi } from "vitest";
import * as svc from "@/services/pythonPracticeService";
import { usePythonPracticeStore } from "@/store/pythonPracticeStore";
import type { PyResult, PySession, SessionQuestion } from "@/types/pythonPractice";

vi.mock("@/services/pythonPracticeService");
const mocked = vi.mocked(svc);

const STARTER = "def f(x):\n    pass\n";
const question = (id: string, over: Partial<SessionQuestion> = {}): SessionQuestion => ({
  question_id: id, unit_id: "unit-g", topic_id: "hash-maps", format: "coding", interaction: "code", difficulty: "easy", title: "T", statement: "Do the thing, a long statement.", code: null, options: [],
  est_time_seconds: 60, tags: [], python_version: null, short: null,
  code_spec: { mode: "function", entry: "f", signature: "def f(x):", starter: STARTER, constraints: [], examples: [], visible_count: 1, hidden_count: 3 },
  selected_index: null, text_answer: null, code_answer: null, marked_for_review: false, locked: false, checks: 0, runs: 0, hints_total: 2, hints_used: 0, hints: [], last_check: null, last_run: null, can_reveal: false, feedback: null, ...over,
});
const session = (over: Partial<PySession> = {}): PySession => ({
  session_id: "s".repeat(24), mode: "coding", status: "in_progress", difficulty: null, question_count: 2, requested_count: 2, unit_ids: [], topic_ids: [], immediate_feedback: true, exam_mode: false,
  started_at: new Date().toISOString(), expires_at: null, server_time: new Date().toISOString(), remaining_seconds: null, timer_minutes: null, scoring_policy: "p",
  questions: [question("pyq-0000000001"), question("pyq-0000000002", { interaction: "mcq", code_spec: null, options: ["a", "b", "c", "d"], hints_total: 0 })], ...over,
});
const result = (): PyResult => ({ session_id: "s".repeat(24), mode: "coding", status: "completed", total_questions: 2, correct: 1, incorrect: 1, unanswered: 0, score: 1, accuracy: 50, time_taken_seconds: 10, average_seconds_per_question: 5, auto_submitted: false,
  started_at: "", finished_at: "", topic_performance: [], revision_topics: [], questions: [], scoring_policy: "p" });

const store = () => usePythonPracticeStore.getState();
beforeEach(() => { vi.resetAllMocks(); store().reset(); });

describe("drafts and saving", () => {
  it("never auto-saves an untouched starter template", async () => {
    mocked.createSession.mockResolvedValue(session());
    await store().startSession({ mode: "coding", question_count: 2 });
    mocked.saveAnswer.mockResolvedValue({ question_id: "x", selected_index: null, marked_for_review: false, locked: false, feedback: null, remaining_seconds: null });
    store().setDraft("pyq-0000000001", STARTER);
    await store().goTo(1);
    expect(mocked.saveAnswer).not.toHaveBeenCalled();
  });
  it("saves edited code with the code field, not text", async () => {
    mocked.createSession.mockResolvedValue(session());
    await store().startSession({ mode: "coding", question_count: 2 });
    mocked.saveAnswer.mockResolvedValue({ question_id: "x", selected_index: null, marked_for_review: false, locked: false, feedback: null, remaining_seconds: null });
    store().setDraft("pyq-0000000001", "def f(x):\n    return x");
    await store().goTo(1);
    expect(mocked.saveAnswer).toHaveBeenCalledWith(expect.any(String), "pyq-0000000001", expect.objectContaining({ code: "def f(x):\n    return x" }));
    expect(mocked.saveAnswer.mock.calls[0][2]).not.toHaveProperty("text");
    expect(mocked.saveAnswer.mock.calls[0][2]).not.toHaveProperty("is_correct");
  });
});

describe("run, check, hint and reveal", () => {
  const grade = (accepted: boolean) => ({ verdict: accepted ? "accepted" : "wrong_answer", message: "m", passed: accepted ? 4 : 1, total: 4, accepted, tests: [], setup_error: null, wall_ms: 1 }) as never;
  beforeEach(async () => {
    mocked.createSession.mockResolvedValue(session());
    await store().startSession({ mode: "coding", question_count: 2 });
  });
  it("runs trial code, stores the server's result and counts the run", async () => {
    mocked.runCode.mockResolvedValue({ question_id: "pyq-0000000001", kind: "run", result: grade(false), remaining_seconds: null });
    store().setDraft("pyq-0000000001", "code");
    await store().runCode("pyq-0000000001");
    expect(mocked.runCode).toHaveBeenCalledWith(expect.any(String), "pyq-0000000001", "code");
    expect(store().runs["pyq-0000000001"].passed).toBe(1);
    expect(store().session?.questions[0].runs).toBe(1);
  });
  it("refuses to run empty code without calling the server", async () => {
    store().setDraft("pyq-0000000001", "   ");
    await store().runCode("pyq-0000000001");
    expect(mocked.runCode).not.toHaveBeenCalled();
    expect(store().answerError).toContain("Write some code");
  });
  it("ignores a second run while one is in flight", async () => {
    let release: (v: never) => void = () => {};
    mocked.runCode.mockReturnValue(new Promise((r) => { release = r as never; }));
    store().setDraft("pyq-0000000001", "code");
    const a = store().runCode("pyq-0000000001");
    void store().runCode("pyq-0000000001");
    expect(mocked.runCode).toHaveBeenCalledTimes(1);
    release({ question_id: "x", kind: "run", result: grade(true), remaining_seconds: null } as never);
    await a;
  });
  it("locks on an accepted submission and unlocks reveal after a failed one", async () => {
    store().setDraft("pyq-0000000001", "code");
    mocked.checkAnswer.mockResolvedValueOnce({ question_id: "pyq-0000000001", kind: "code", correct: false, locked: false, checks: 1, result: grade(false), can_reveal: true, feedback: null, remaining_seconds: null });
    await store().checkAnswer("pyq-0000000001");
    let q = store().session!.questions[0];
    expect(q.locked).toBe(false);
    expect(q.can_reveal).toBe(true);
    expect(q.last_check).toEqual({ verdict: "wrong_answer", passed: 1, total: 4 });
    mocked.checkAnswer.mockResolvedValueOnce({ question_id: "pyq-0000000001", kind: "code", correct: true, locked: true, checks: 2, result: grade(true), can_reveal: true,
      feedback: { kind: "code", is_correct: true, revealed: false, reference_source: "ref", time_complexity: "O(n)", space_complexity: "O(1)", explanation: "e" }, remaining_seconds: null });
    await store().checkAnswer("pyq-0000000001");
    q = store().session!.questions[0];
    expect(q.locked).toBe(true);
    expect(q.feedback?.kind).toBe("code");
  });
  it("requests hints and unlocks the reference only once every hint was seen", async () => {
    mocked.requestHint.mockResolvedValueOnce({ question_id: "pyq-0000000001", hint: "h1", hint_number: 1, hints_total: 2, hints: ["h1"] });
    await store().requestHint("pyq-0000000001");
    expect(store().session!.questions[0].can_reveal).toBe(false);
    mocked.requestHint.mockResolvedValueOnce({ question_id: "pyq-0000000001", hint: "h2", hint_number: 2, hints_total: 2, hints: ["h1", "h2"] });
    await store().requestHint("pyq-0000000001");
    expect(store().session!.questions[0].can_reveal).toBe(true);
  });
  it("never unlocks reveal from hints in a timed mock", async () => {
    mocked.createSession.mockResolvedValue(session({ exam_mode: true, immediate_feedback: false, mode: "timed_mock" }));
    store().reset();
    await store().startSession({ mode: "timed_mock", question_count: 2, timer_minutes: 5 });
    mocked.requestHint.mockResolvedValue({ question_id: "pyq-0000000001", hint: "h", hint_number: 2, hints_total: 2, hints: ["a", "b"] });
    await store().requestHint("pyq-0000000001");
    expect(store().session!.questions[0].can_reveal).toBe(false);
  });
});

describe("submission and lifecycle", () => {
  it("submits once even when called repeatedly", async () => {
    mocked.createSession.mockResolvedValue(session());
    await store().startSession({ mode: "coding", question_count: 2 });
    let release: (v: PyResult) => void = () => {};
    mocked.submitSession.mockReturnValue(new Promise((r) => { release = r; }));
    const first = store().submit();
    void store().submit();
    void store().submit();
    expect(mocked.submitSession).toHaveBeenCalledTimes(1);
    release(result());
    await first;
    expect(store().result?.score).toBe(1);
    expect(store().ended).toBe(true);
  });
  it("clears everything on reset, which logout calls", async () => {
    mocked.createSession.mockResolvedValue(session());
    await store().startSession({ mode: "coding", question_count: 2 });
    store().setDraft("pyq-0000000001", "secret work");
    store().reset();
    expect(store().session).toBeNull();
    expect(store().drafts).toEqual({});
    expect(store().result).toBeNull();
    expect(store().runs).toEqual({});
  });
  it("loads history and reports failures", async () => {
    mocked.getHistory.mockResolvedValueOnce({ items: [], page: 1, limit: 10, total: 0, has_next: false });
    await store().loadHistory();
    expect(store().historyStatus).toBe("ready");
    mocked.getHistory.mockRejectedValueOnce(new Error("boom"));
    await store().loadHistory();
    expect(store().historyStatus).toBe("error");
    expect(store().historyError).toBeTruthy();
  });
});
