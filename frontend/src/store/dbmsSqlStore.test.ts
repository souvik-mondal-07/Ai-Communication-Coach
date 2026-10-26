import { beforeEach, describe, expect, it, vi } from "vitest";
import { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { installSessionReset } from "@/store/sessionReset";
import { useAuthStore } from "@/store/authStore";
import { useDbmsSqlStore } from "@/store/dbmsSqlStore";
import type { DbmsResult, DbmsSession, SessionQuestion } from "@/types/dbmsSql";

vi.mock("@/services/dbmsSqlService", () => ({
  getSyllabus: vi.fn(), getDataset: vi.fn(), runSandbox: vi.fn(), createSession: vi.fn(), getSession: vi.fn(), saveAnswer: vi.fn(), checkAnswer: vi.fn(), revealSolution: vi.fn(),
  requestHint: vi.fn(), submitSession: vi.fn(), getResult: vi.fn(), getProgress: vi.fn(), getRecommendations: vi.fn(),
}));
import * as svc from "@/services/dbmsSqlService";
const m = vi.mocked(svc);

const mcq = (id: string, over: Partial<SessionQuestion> = {}): SessionQuestion => ({
  question_id: id, unit_id: "unit-a", topic_id: "keys", format: "concept", interaction: "mcq", dialect: "standard", difficulty: "easy", statement: "s", code: null, options: ["a", "b", "c", "d"],
  dataset_id: null, est_time_seconds: 30, tags: [], short: null, sql: null, selected_index: null, text_answer: null, sql_answer: null, marked_for_review: false, locked: false, checks: 0,
  hints_total: 0, hints_used: 0, hints: [], last_check: null, feedback: null, ...over,
});
const sqlQ = (id: string, over: Partial<SessionQuestion> = {}) => mcq(id, { interaction: "sql", format: "query", dialect: "sqlite", options: [], dataset_id: "practice",
  sql: { dataset_id: "practice", starter: null, ordered: false, check_column_names: false, expected_columns: ["name"] }, hints_total: 2, ...over });
const shortQ = (id: string, over: Partial<SessionQuestion> = {}) => mcq(id, { interaction: "short", options: [], short: { kind: "attrs", help: "letters" }, ...over });
const session = (questions: SessionQuestion[], over: Partial<DbmsSession> = {}): DbmsSession => ({
  session_id: "s1", mode: "sql_lab", status: "in_progress", difficulty: null, question_count: questions.length, requested_count: questions.length, unit_ids: [], topic_ids: [], immediate_feedback: true,
  exam_mode: false, started_at: new Date().toISOString(), expires_at: null, server_time: new Date().toISOString(), remaining_seconds: null, timer_minutes: null, questions, scoring_policy: "p", ...over,
});
const result = { session_id: "s1", total_questions: 2 } as DbmsResult;
function fail(status: number, error_code: string, message = "nope") {
  const config = {} as InternalAxiosRequestConfig;
  return new AxiosError("x", "ERR", config, null, { data: { message, error_code }, status, statusText: "", headers: {}, config } as never);
}
const st = () => useDbmsSqlStore.getState();

beforeEach(() => { vi.resetAllMocks(); st().reset(); });

describe("starting and resuming", () => {
  it("startSession stores the session and returns its id", async () => {
    m.createSession.mockResolvedValue(session([mcq("a")]));
    expect(await st().startSession({ mode: "mixed", question_count: 1 })).toBe("s1");
    expect(st().session?.questions).toHaveLength(1);
    expect(st().currentIndex).toBe(0);
  });
  it("a failed start reports the server message and returns null", async () => {
    m.createSession.mockRejectedValue(fail(409, "NO_QUESTIONS", "No questions match these filters yet."));
    expect(await st().startSession({ mode: "mixed", question_count: 1 })).toBeNull();
    expect(st().startError).toBe("No questions match these filters yet.");
    expect(st().isStarting).toBe(false);
  });
  it("a second start while one is running is ignored", async () => {
    let resolve!: (s: DbmsSession) => void;
    m.createSession.mockReturnValue(new Promise((r) => { resolve = r; }));
    const first = st().startSession({ mode: "mixed", question_count: 1 });
    expect(await st().startSession({ mode: "mixed", question_count: 1 })).toBeNull();
    resolve(session([mcq("a")]));
    await first;
    expect(m.createSession).toHaveBeenCalledTimes(1);
  });
  it("loadSession lands on the first unanswered question and restores saved SQL and text into drafts", async () => {
    m.getSession.mockResolvedValue(session([mcq("a", { selected_index: 1 }), shortQ("b"), sqlQ("c", { sql_answer: "SELECT 1" })]));
    await st().loadSession("s1");
    expect(st().currentIndex).toBe(1);
    expect(st().drafts.c).toBe("SELECT 1");
    expect(st().sessionStatus).toBe("ready");
  });
  it("loadSession of a completed session marks it ended", async () => {
    m.getSession.mockResolvedValue(session([mcq("a")], { status: "completed" }));
    await st().loadSession("s1");
    expect(st().ended).toBe(true);
  });
  it("a load error is surfaced", async () => {
    m.getSession.mockRejectedValue(fail(404, "NOT_FOUND", "Session not found."));
    await st().loadSession("s1");
    expect(st().sessionStatus).toBe("error");
    expect(st().sessionError).toBe("Session not found.");
  });
});

describe("answering", () => {
  beforeEach(async () => {
    m.createSession.mockResolvedValue(session([mcq("a"), shortQ("b"), sqlQ("c")]));
    await st().startSession({ mode: "sql_lab", question_count: 3 });
  });
  it("selectAnswer sends only the option position, then applies the server's lock and feedback", async () => {
    m.saveAnswer.mockResolvedValue({ question_id: "a", selected_index: 2, marked_for_review: false, locked: true, remaining_seconds: null, feedback: { kind: "mcq", is_correct: true, correct_index: 2, explanation: "e" } });
    await st().selectAnswer("a", 2);
    const body = m.saveAnswer.mock.calls[0][2];
    expect(Object.keys(body).sort()).toEqual(["marked_for_review", "selected_index", "time_spent_seconds"]);
    expect(st().session!.questions[0]).toMatchObject({ selected_index: 2, locked: true });
  });
  it("selectAnswer reverts when the save fails", async () => {
    m.saveAnswer.mockRejectedValue(fail(500, "SERVER_ERROR", "boom"));
    await st().selectAnswer("a", 1);
    expect(st().session!.questions[0].selected_index).toBeNull();
    expect(st().answerError).toBe("boom");
    expect(st().ended).toBe(false);
  });
  it("an expired or completed session ends the run instead of reverting", async () => {
    m.saveAnswer.mockRejectedValue(fail(409, "SESSION_EXPIRED", "Time is up."));
    await st().selectAnswer("a", 1);
    expect(st().ended).toBe(true);
  });
  it("a locked question makes no request", async () => {
    st().session!.questions[0].locked = true;
    await st().selectAnswer("a", 1);
    expect(m.saveAnswer).not.toHaveBeenCalled();
  });
  it("drafts are kept locally, saved on demand, and the saved text is stored on the question", async () => {
    st().setDraft("c", "SELECT 1");
    m.saveAnswer.mockResolvedValue({ question_id: "c", selected_index: null, marked_for_review: false, locked: false, remaining_seconds: null, feedback: null });
    await st().saveDraft("c");
    expect(m.saveAnswer.mock.calls[0][2]).toMatchObject({ sql: "SELECT 1" });
    expect(st().session!.questions[2].sql_answer).toBe("SELECT 1");
    st().setDraft("b", "ABC");
    await st().saveDraft("b");
    expect(m.saveAnswer.mock.calls[1][2]).toMatchObject({ text: "ABC" });
  });
  it("goTo saves a changed typed answer before leaving", async () => {
    m.saveAnswer.mockResolvedValue({ question_id: "b", selected_index: null, marked_for_review: false, locked: false, remaining_seconds: null, feedback: null });
    st().goTo(1);
    st().setDraft("b", "AB");
    st().goTo(2);
    await vi.waitFor(() => expect(m.saveAnswer).toHaveBeenCalled());
    expect(st().currentIndex).toBe(2);
  });
  it("goTo ignores out-of-range indexes", () => {
    st().goTo(-1);
    st().goTo(99);
    expect(st().currentIndex).toBe(0);
  });
  it("toggleMark is optimistic and reverts on failure", async () => {
    m.saveAnswer.mockRejectedValue(fail(500, "SERVER_ERROR"));
    await st().toggleMark("a");
    expect(st().session!.questions[0].marked_for_review).toBe(false);
  });
});

describe("running, checking, hints and reveal", () => {
  beforeEach(async () => {
    m.createSession.mockResolvedValue(session([sqlQ("c"), shortQ("b")]));
    await st().startSession({ mode: "sql_lab", question_count: 2 });
  });
  it("runQuery with an empty draft never calls the server", async () => {
    await st().runQuery("c");
    expect(m.runSandbox).not.toHaveBeenCalled();
    expect(st().runs.c.error?.message).toBe("Write a query first.");
  });
  it("runQuery sends the SQL and dataset and stores the output", async () => {
    st().setDraft("c", "SELECT 1");
    m.runSandbox.mockResolvedValue({ ok: true, columns: ["1"], rows: [[1]], row_count: 1, truncated: false, elapsed_ms: 1, error: null });
    await st().runQuery("c");
    expect(m.runSandbox).toHaveBeenCalledWith("SELECT 1", "practice");
    expect(st().runs.c.rows).toEqual([[1]]);
    expect(st().busy.c).toBeUndefined();
  });
  it("a rejected statement is stored as a normal run result", async () => {
    st().setDraft("c", "DROP TABLE x");
    m.runSandbox.mockResolvedValue({ ok: false, columns: [], rows: [], row_count: 0, truncated: false, elapsed_ms: 1, error: { kind: "not_allowed", message: "no" } });
    await st().runQuery("c");
    expect(st().runs.c.error?.kind).toBe("not_allowed");
    expect(st().answerError).toBeNull();
  });
  it("a failed run request reports an error and clears the busy flag", async () => {
    st().setDraft("c", "SELECT 1");
    m.runSandbox.mockRejectedValue(fail(429, "RATE_LIMITED", "Too many requests."));
    await st().runQuery("c");
    expect(st().answerError).toBe("Too many requests.");
    expect(st().busy.c).toBeUndefined();
  });
  it("checkAnswer applies the verdict, comparison, lock and feedback from the server", async () => {
    st().setDraft("c", "SELECT name FROM employees");
    const outcome = { question_id: "c", kind: "sql" as const, correct: true, locked: true, checks: 2, verdict: { code: "correct", messages: ["ok"] }, run: { ok: true, columns: ["name"], rows: [["Neha"]], row_count: 1, truncated: false, elapsed_ms: 1, error: null },
      comparison: null, feedback: { kind: "sql" as const, is_correct: true, revealed: false, reference_sql: "R", expected: { columns: ["name"], rows: [["Neha"]], row_count: 1, truncated: false }, explanation: "e" }, remaining_seconds: null };
    m.checkAnswer.mockResolvedValue(outcome);
    await st().checkAnswer("c");
    expect(m.checkAnswer.mock.calls[0][2]).toMatchObject({ sql: "SELECT name FROM employees" });
    expect(Object.keys(m.checkAnswer.mock.calls[0][2]).sort()).toEqual(["sql", "time_spent_seconds"]);
    expect(st().session!.questions[0]).toMatchObject({ locked: true, checks: 2, sql_answer: "SELECT name FROM employees" });
    expect(st().session!.questions[0].feedback?.kind).toBe("sql");
    expect(st().runs.c.rows).toEqual([["Neha"]]);
  });
  it("short answers are checked with text, not sql", async () => {
    st().setDraft("b", "ABC");
    m.checkAnswer.mockResolvedValue({ question_id: "b", kind: "short", correct: true, locked: true, checks: 1, feedback: { kind: "short", is_correct: true, answer: "{A, B, C}", explanation: "e" }, remaining_seconds: null });
    await st().checkAnswer("b");
    expect(m.checkAnswer.mock.calls[0][2]).toMatchObject({ text: "ABC" });
    expect(m.checkAnswer.mock.calls[0][2]).not.toHaveProperty("sql");
  });
  it("a check on a locked question makes no request", async () => {
    st().session!.questions[0].locked = true;
    await st().checkAnswer("c");
    expect(m.checkAnswer).not.toHaveBeenCalled();
  });
  it("requestHint stores the hints the server returns and stops at the total", async () => {
    m.requestHint.mockResolvedValueOnce({ question_id: "c", hint: "h1", hint_number: 1, hints_total: 2, hints: ["h1"] });
    await st().requestHint("c");
    expect(st().session!.questions[0]).toMatchObject({ hints: ["h1"], hints_used: 1 });
    m.requestHint.mockResolvedValueOnce({ question_id: "c", hint: "h2", hint_number: 2, hints_total: 2, hints: ["h1", "h2"] });
    await st().requestHint("c");
    await st().requestHint("c");
    expect(m.requestHint).toHaveBeenCalledTimes(2);
  });
  it("revealSolution locks the question with the server's feedback", async () => {
    m.revealSolution.mockResolvedValue({ question_id: "c", locked: true, remaining_seconds: null, feedback: { kind: "sql", is_correct: false, revealed: true, reference_sql: "R", expected: { columns: ["name"], rows: [], row_count: 0, truncated: false }, explanation: "e" } });
    await st().revealSolution("c");
    expect(st().session!.questions[0].locked).toBe(true);
    expect((st().session!.questions[0].feedback as { revealed: boolean }).revealed).toBe(true);
  });
  it("busy flags prevent a duplicate in-flight request", async () => {
    st().setDraft("c", "SELECT 1");
    let finish!: () => void;
    m.runSandbox.mockReturnValue(new Promise((r) => { finish = () => r({ ok: true, columns: [], rows: [], row_count: 0, truncated: false, elapsed_ms: 0, error: null }); }));
    const a = st().runQuery("c");
    await st().runQuery("c");
    finish();
    await a;
    expect(m.runSandbox).toHaveBeenCalledTimes(1);
  });
});

describe("submitting", () => {
  it("saves a changed typed answer first, then submits once even if called twice", async () => {
    m.createSession.mockResolvedValue(session([sqlQ("c")]));
    await st().startSession({ mode: "sql_lab", question_count: 1 });
    st().setDraft("c", "SELECT 1");
    m.saveAnswer.mockResolvedValue({ question_id: "c", selected_index: null, marked_for_review: false, locked: false, remaining_seconds: null, feedback: null });
    m.submitSession.mockImplementation(() => new Promise((r) => setTimeout(() => r(result), 10)));
    const [a, b] = await Promise.all([st().submit(), st().submit()]);
    expect(m.submitSession).toHaveBeenCalledTimes(1);
    expect(m.saveAnswer).toHaveBeenCalled();
    expect(a).toBe(result);
    expect(b === null || b === undefined || b === result).toBe(true);
    expect(st().ended).toBe(true);
  });
  it("a failed submit keeps the session open and reports the error", async () => {
    m.createSession.mockResolvedValue(session([mcq("a")]));
    await st().startSession({ mode: "mixed", question_count: 1 });
    m.submitSession.mockRejectedValue(fail(500, "SERVER_ERROR", "Try later."));
    expect(await st().submit()).toBeNull();
    expect(st().ended).toBe(false);
    expect(st().answerError).toBe("Try later.");
    expect(st().isSubmitting).toBe(false);
  });
  it("loadResult stores or reports", async () => {
    m.getResult.mockResolvedValueOnce(result);
    await st().loadResult("s1");
    expect(st().result).toBe(result);
    m.getResult.mockRejectedValueOnce(fail(409, "SESSION_NOT_FINISHED", "Results are available after the session is submitted."));
    await st().loadResult("s1");
    expect(st().resultStatus).toBe("error");
    expect(st().resultError).toContain("after the session is submitted");
  });
});

describe("syllabus, datasets, playground, progress", () => {
  it("loads and reports errors for each resource", async () => {
    m.getSyllabus.mockRejectedValueOnce(fail(503, "X", "down"));
    await st().loadSyllabus();
    expect(st().syllabusStatus).toBe("error");
    m.getSyllabus.mockResolvedValueOnce({ units: [], question_total: 0 } as never);
    await st().loadSyllabus();
    expect(st().syllabusStatus).toBe("ready");
    m.getProgress.mockRejectedValueOnce(fail(500, "X", "bad"));
    m.getRecommendations.mockResolvedValue({} as never);
    await st().loadProgress();
    expect(st().progressStatus).toBe("error");
  });
  it("datasets are cached after the first load", async () => {
    m.getDataset.mockResolvedValue({ id: "practice", tables: [] } as never);
    await st().loadDataset();
    await st().loadDataset();
    expect(m.getDataset).toHaveBeenCalledTimes(1);
  });
  it("the playground stores output and reports request failures", async () => {
    m.runSandbox.mockResolvedValueOnce({ ok: true, columns: ["a"], rows: [[1]], row_count: 1, truncated: false, elapsed_ms: 1, error: null });
    await st().runPlayground("SELECT 1");
    expect(st().playground?.rows).toEqual([[1]]);
    m.runSandbox.mockRejectedValueOnce(fail(429, "RATE_LIMITED", "Slow down."));
    await st().runPlayground("SELECT 1");
    expect(st().playgroundError).toBe("Slow down.");
    expect(st().playgroundBusy).toBe(false);
  });
});

describe("per-user privacy", () => {
  it("wipes session answers, SQL drafts and results when the user changes or logs out", async () => {
    installSessionReset();
    useAuthStore.setState({ user: { id: "a", name: "A", email: "a@example.com" }, isAuthenticated: true });
    m.getSession.mockResolvedValue(session([sqlQ("c", { sql_answer: "secret query by A" })]));
    await st().loadSession("s1");
    useDbmsSqlStore.setState({ result });
    expect(st().drafts.c).toBe("secret query by A");
    useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false });
    expect(st().session).toBeNull();
    expect(st().drafts).toEqual({});
    expect(st().result).toBeNull();
  });
});
