import { beforeEach, describe, expect, it, vi } from "vitest";
import { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { installSessionReset } from "@/store/sessionReset";
import { useAuthStore } from "@/store/authStore";
import { useDsaStore } from "@/store/dsaStore";
import type { DsaResult, DsaSession, SessionQuestion } from "@/types/dsa";

vi.mock("@/services/dsaService", () => ({
  getSyllabus: vi.fn(), createSession: vi.fn(), getSession: vi.fn(), saveAnswer: vi.fn(), submitSession: vi.fn(),
  getResult: vi.fn(), setSelfAssessment: vi.fn(), getProgress: vi.fn(), getRecommendations: vi.fn(),
}));
import * as svc from "@/services/dsaService";
const m = vi.mocked(svc);

const mcq = (id: string, over: Partial<SessionQuestion> = {}): SessionQuestion => ({
  question_id: id, topic_id: "arrays", subtopic_id: "array-memory", format: "conceptual", interaction: "mcq", coding_type: null, difficulty: "easy", statement: "s", code: null,
  options: ["a", "b", "c", "d"], constraints: null, est_time_seconds: 30, coding: null, selected_index: null, code_answer: null, marked_for_review: false, locked: false, hints: [], feedback: null, ...over,
});
const code = (id: string, over: Partial<SessionQuestion> = {}): SessionQuestion => mcq(id, {
  interaction: "code", format: "coding", coding_type: "write_function", options: [],
  coding: { function_name: "f", template: "def f():\n    pass\n", sample_io: null, visible_tests: [], hidden_test_count: 1 }, ...over,
});
const session = (questions: SessionQuestion[], over: Partial<DsaSession> = {}): DsaSession => ({
  session_id: "s1", mode: "timed_mock", status: "in_progress", difficulty: null, question_count: questions.length, requested_count: questions.length, topic_ids: [], immediate_feedback: false,
  exam_mode: true, started_at: new Date().toISOString(), expires_at: null, server_time: new Date().toISOString(), remaining_seconds: null, timer_minutes: null, questions, scoring_policy: "p", ...over,
});
const result = { session_id: "s1", total_questions: 2 } as DsaResult;

function fail(status: number, error_code: string, message = "nope") {
  const config = {} as InternalAxiosRequestConfig;
  return new AxiosError("x", "ERR", config, null, { data: { message, error_code }, status, statusText: "", headers: {}, config } as never);
}

beforeEach(() => {
  vi.resetAllMocks();
  useDsaStore.getState().reset();
});

describe("resuming a session", () => {
  it("lands on the first unanswered question and restores saved code into drafts", async () => {
    m.getSession.mockResolvedValue(session([mcq("a", { selected_index: 1 }), code("b", { code_answer: "def f(): return 1" }), mcq("c")]));
    await useDsaStore.getState().loadSession("s1");
    const s = useDsaStore.getState();
    expect(s.currentIndex).toBe(2);
    expect(s.drafts).toEqual({ b: "def f(): return 1" });
    expect(s.ended).toBe(false);
  });
  it("a session the server has already completed is marked ended", async () => {
    m.getSession.mockResolvedValue(session([mcq("a")], { status: "completed" }));
    await useDsaStore.getState().loadSession("s1");
    expect(useDsaStore.getState().ended).toBe(true);
  });
  it("reports a load failure without crashing", async () => {
    m.getSession.mockRejectedValue(fail(404, "NOT_FOUND", "Not found."));
    await useDsaStore.getState().loadSession("zzz");
    expect(useDsaStore.getState().sessionStatus).toBe("error");
    expect(useDsaStore.getState().sessionError).toBe("Not found.");
  });
});

describe("saving answers", () => {
  beforeEach(async () => {
    m.getSession.mockResolvedValue(session([mcq("a"), code("b")]));
    await useDsaStore.getState().loadSession("s1");
  });

  it("applies an option optimistically and sends only the position", async () => {
    m.saveAnswer.mockResolvedValue({ question_id: "a", selected_index: 2, code_answer: null, marked_for_review: false, locked: false, feedback: null, remaining_seconds: 5 });
    await useDsaStore.getState().selectAnswer("a", 2);
    expect(useDsaStore.getState().session!.questions[0].selected_index).toBe(2);
    expect(Object.keys(m.saveAnswer.mock.calls[0][2]).sort()).toEqual(["marked_for_review", "selected_index", "time_spent_seconds"]);
  });

  it("rolls back and reports when saving fails", async () => {
    m.saveAnswer.mockRejectedValue(fail(500, "SERVER_ERROR", "Boom."));
    await useDsaStore.getState().selectAnswer("a", 3);
    expect(useDsaStore.getState().session!.questions[0].selected_index).toBeNull();
    expect(useDsaStore.getState().answerError).toBe("Boom.");
  });

  it("stores feedback and locks the question when the server reveals it", async () => {
    m.saveAnswer.mockResolvedValue({ question_id: "a", selected_index: 1, code_answer: null, marked_for_review: false, locked: true, remaining_seconds: 5,
      feedback: { kind: "mcq", is_correct: true, correct_index: 1, explanation: "why", complexity: null, trace: null } });
    await useDsaStore.getState().selectAnswer("a", 1);
    const q = useDsaStore.getState().session!.questions[0];
    expect(q.locked).toBe(true);
    expect(q.feedback).toMatchObject({ kind: "mcq", explanation: "why" });
    await useDsaStore.getState().selectAnswer("a", 2); // locked: ignored, no second request
    expect(m.saveAnswer).toHaveBeenCalledTimes(1);
  });

  it("an 'expired' rejection ends the session instead of rolling back", async () => {
    m.saveAnswer.mockRejectedValue(fail(409, "SESSION_EXPIRED", "Time is up."));
    await useDsaStore.getState().selectAnswer("a", 0);
    expect(useDsaStore.getState().ended).toBe(true);
  });

  it("refuses to send an option for a coding question, or code for an MCQ", async () => {
    await useDsaStore.getState().selectAnswer("b", 1);
    await useDsaStore.getState().saveCode("a");
    expect(m.saveAnswer).not.toHaveBeenCalled();
  });

  it("saves code with reveal=false by default and true on request", async () => {
    m.saveAnswer.mockResolvedValue({ question_id: "b", selected_index: null, code_answer: "x = 1", marked_for_review: false, locked: false, feedback: null, remaining_seconds: 5 });
    useDsaStore.getState().setDraft("b", "x = 1");
    await useDsaStore.getState().saveCode("b");
    await useDsaStore.getState().saveCode("b", { reveal: true });
    expect(m.saveAnswer.mock.calls[0][2]).toMatchObject({ code: "x = 1", reveal: false });
    expect(m.saveAnswer.mock.calls[1][2]).toMatchObject({ code: "x = 1", reveal: true });
  });

  it("keeps unsaved code in the editor when saving fails", async () => {
    m.saveAnswer.mockRejectedValue(fail(500, "SERVER_ERROR"));
    useDsaStore.getState().setDraft("b", "precious work");
    await useDsaStore.getState().saveCode("b");
    expect(useDsaStore.getState().drafts.b).toBe("precious work");
    expect(useDsaStore.getState().answerError).toBeTruthy();
  });

  it("leaving a coding question with unsaved edits saves them first", async () => {
    m.saveAnswer.mockResolvedValue({ question_id: "b", selected_index: null, code_answer: "y", marked_for_review: false, locked: false, feedback: null, remaining_seconds: 5 });
    useDsaStore.getState().goTo(1);
    useDsaStore.getState().setDraft("b", "y");
    useDsaStore.getState().goTo(0);
    await vi.waitFor(() => expect(m.saveAnswer).toHaveBeenCalled());
    expect(m.saveAnswer.mock.calls[0][2]).toMatchObject({ code: "y" });
  });
});

describe("submitting", () => {
  it("ignores a second submit while one is in flight", async () => {
    m.getSession.mockResolvedValue(session([mcq("a")]));
    await useDsaStore.getState().loadSession("s1");
    let finish!: (r: DsaResult) => void;
    m.submitSession.mockReturnValue(new Promise<DsaResult>((res) => { finish = res; }));
    const first = useDsaStore.getState().submit();
    const second = useDsaStore.getState().submit();
    finish(result);
    await first;
    await second;
    expect(m.submitSession).toHaveBeenCalledTimes(1);
    expect(useDsaStore.getState().ended).toBe(true);
    expect(useDsaStore.getState().result).toEqual(result);
  });

  it("a failed submit keeps the session and says answers are saved", async () => {
    m.getSession.mockResolvedValue(session([mcq("a")]));
    await useDsaStore.getState().loadSession("s1");
    m.submitSession.mockRejectedValue(fail(500, "SERVER_ERROR", ""));
    expect(await useDsaStore.getState().submit()).toBeNull();
    expect(useDsaStore.getState().isSubmitting).toBe(false);
    expect(useDsaStore.getState().answerError).toBeTruthy();
    expect(useDsaStore.getState().ended).toBe(false);
  });
});

describe("self-assessment", () => {
  it("updates only the chosen question in the result", async () => {
    useDsaStore.setState({ result: { session_id: "s1", questions: [{ question_id: "a", self_assessment: null }, { question_id: "b", self_assessment: null }] } as unknown as DsaResult });
    m.setSelfAssessment.mockResolvedValue({ question_id: "b", self_assessment: "failed", counts_toward_score: false });
    await useDsaStore.getState().assessCode("b", "failed");
    expect(useDsaStore.getState().result!.questions.map((q) => q.self_assessment)).toEqual([null, "failed"]);
  });
});

describe("per-user privacy", () => {
  it("wipes session answers, code drafts and results when the user changes or logs out", async () => {
    installSessionReset();
    useAuthStore.setState({ user: { id: "a", name: "A", email: "a@example.com" }, isAuthenticated: true });
    m.getSession.mockResolvedValue(session([code("b", { code_answer: "secret solution by A" })]));
    await useDsaStore.getState().loadSession("s1");
    useDsaStore.setState({ result });
    expect(useDsaStore.getState().drafts.b).toBe("secret solution by A");
    useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false });
    const s = useDsaStore.getState();
    expect(s.session).toBeNull();
    expect(s.result).toBeNull();
    expect(s.drafts).toEqual({});
    expect(s.progress).toBeNull();
  });
});
