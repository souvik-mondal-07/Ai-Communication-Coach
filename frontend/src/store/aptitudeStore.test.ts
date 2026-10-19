import { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AptitudeResult, AptitudeSession, SessionQuestion } from "@/types/aptitude";

vi.mock("@/services/aptitudeService", () => ({
  getSyllabus: vi.fn(), createSession: vi.fn(), getSession: vi.fn(), saveAnswer: vi.fn(), submitSession: vi.fn(), getResult: vi.fn(), getProgress: vi.fn(), getRecommendations: vi.fn(),
}));

import * as svc from "@/services/aptitudeService";
import { useAptitudeStore } from "./aptitudeStore";

const q = (n: number, over: Partial<SessionQuestion> = {}): SessionQuestion => ({
  question_id: `apt-${String(n).padStart(10, "0")}`, topic_id: "number-system", subtopic_id: "unit-digit", question_type: "direct", difficulty: "easy", statement: `Question ${n}?`,
  options: ["a", "b", "c", "d"], est_time_seconds: 30, data: null, selected_index: null, marked_for_review: false, locked: false, feedback: null, ...over,
});
const session = (over: Partial<AptitudeSession> = {}): AptitudeSession => ({
  session_id: "s".repeat(24), mode: "timed_mock", status: "in_progress", difficulty: null, question_count: 3, requested_count: 3, topic_ids: ["number-system"], immediate_feedback: false, exam_mode: true,
  started_at: "2026-10-18T10:00:00Z", expires_at: "2026-10-18T10:30:00Z", server_time: "2026-10-18T10:00:05Z", remaining_seconds: 1795, timer_minutes: 30, questions: [q(1), q(2), q(3)], scoring_policy: "p", ...over,
});
const result = (): AptitudeResult => ({
  session_id: "s".repeat(24), mode: "timed_mock", status: "completed", total_questions: 3, correct: 1, incorrect: 1, unanswered: 1, score: 1, accuracy: 33.3, time_taken_seconds: 90, average_seconds_per_question: 30,
  auto_submitted: false, started_at: "x", finished_at: "y", topic_performance: [], revision_topics: [], questions: [], scoring_policy: "p",
});
const apiError = (status: number, error_code: string, message: string) => {
  const config = { headers: {} } as InternalAxiosRequestConfig;
  return new AxiosError(message, "ERR_BAD_REQUEST", config, null, { data: { success: false, message, error_code }, status, statusText: "", headers: {}, config } as never);
};
const state = () => useAptitudeStore.getState();
const answer = (idx: number | null, over = {}) => ({ question_id: "x", selected_index: idx, marked_for_review: false, locked: false, feedback: null, remaining_seconds: 100, ...over });

beforeEach(() => {
  vi.clearAllMocks();
  state().reset();
});

describe("loading", () => {
  it("loads the syllabus and reports errors with a retry path", async () => {
    vi.mocked(svc.getSyllabus).mockRejectedValueOnce(apiError(500, "X", "Server exploded"));
    await state().loadSyllabus();
    expect(state().syllabusStatus).toBe("error");
    expect(state().syllabusError).toBe("Server exploded");
    vi.mocked(svc.getSyllabus).mockResolvedValueOnce({ topics: [], totals: { topics: 0, subtopics: 0, subtopics_implemented: 0, questions: 0, min_questions_per_subtopic: 4 } });
    await state().loadSyllabus();
    expect(state().syllabusStatus).toBe("ready");
    expect(state().syllabusError).toBeNull();
  });

  it("resumes on the first unanswered question after a refresh", async () => {
    vi.mocked(svc.getSession).mockResolvedValue(session({ questions: [q(1, { selected_index: 2 }), q(2, { selected_index: 0 }), q(3)] }));
    await state().loadSession("s".repeat(24));
    expect(state().currentIndex).toBe(2);
    expect(state().session?.questions[0].selected_index).toBe(2);
    expect(state().ended).toBe(false);
  });

  it("marks a completed session as ended so the page can show the result", async () => {
    vi.mocked(svc.getSession).mockResolvedValue(session({ status: "completed" }));
    await state().loadSession("s".repeat(24));
    expect(state().ended).toBe(true);
  });

  it("derives a clock offset from the server's time", async () => {
    vi.mocked(svc.getSession).mockResolvedValue(session({ server_time: new Date(Date.now() + 60_000).toISOString() }));
    await state().loadSession("s".repeat(24));
    expect(state().clockOffsetMs).toBeGreaterThan(55_000);
  });

  it("surfaces a load failure", async () => {
    vi.mocked(svc.getSession).mockRejectedValue(apiError(404, "NOT_FOUND", "Session not found."));
    await state().loadSession("s".repeat(24));
    expect(state().sessionStatus).toBe("error");
    expect(state().sessionError).toBe("Session not found.");
  });
});

describe("starting", () => {
  it("returns the new session id and ignores a double start", async () => {
    let release!: (s: AptitudeSession) => void;
    vi.mocked(svc.createSession).mockReturnValue(new Promise((r) => { release = r; }));
    const first = state().startSession({ mode: "mixed", topic_ids: [], subtopic_ids: [], question_count: 3 });
    expect(await state().startSession({ mode: "mixed", topic_ids: [], subtopic_ids: [], question_count: 3 })).toBeNull();
    release(session());
    expect(await first).toBe("s".repeat(24));
    expect(svc.createSession).toHaveBeenCalledTimes(1);
  });

  it("reports why a session could not start", async () => {
    vi.mocked(svc.createSession).mockRejectedValue(apiError(409, "NO_HISTORY", "There is no practice history yet."));
    expect(await state().startSession({ mode: "weak", topic_ids: [], subtopic_ids: [], question_count: 5 })).toBeNull();
    expect(state().startError).toBe("There is no practice history yet.");
    expect(state().isStarting).toBe(false);
  });
});

describe("answering", () => {
  beforeEach(async () => {
    vi.mocked(svc.getSession).mockResolvedValue(session());
    await state().loadSession("s".repeat(24));
  });
  const first = () => state().session!.questions[0];

  it("shows the choice immediately and sends only the position, mark flag and time", async () => {
    vi.mocked(svc.saveAnswer).mockResolvedValue(answer(1));
    const p = state().selectAnswer(first().question_id, 1);
    expect(first().selected_index).toBe(1); // optimistic
    await p;
    const [sid, qid, body] = vi.mocked(svc.saveAnswer).mock.calls[0];
    expect([sid, qid]).toEqual(["s".repeat(24), first().question_id]);
    expect(Object.keys(body).sort()).toEqual(["marked_for_review", "selected_index", "time_spent_seconds"]);
    expect(body.selected_index).toBe(1);
  });

  it("rolls back the choice and tells the user when saving fails", async () => {
    vi.mocked(svc.saveAnswer).mockResolvedValueOnce(answer(0)).mockRejectedValueOnce(apiError(500, "X", "Could not save."));
    await state().selectAnswer(first().question_id, 0);
    await state().selectAnswer(first().question_id, 3);
    expect(first().selected_index).toBe(0);
    expect(state().answerError).toBe("Could not save.");
    state().clearAnswerError();
    expect(state().answerError).toBeNull();
  });

  it("can clear an answer", async () => {
    vi.mocked(svc.saveAnswer).mockResolvedValue(answer(null));
    await state().selectAnswer(first().question_id, 2);
    await state().selectAnswer(first().question_id, null);
    expect(first().selected_index).toBeNull();
    expect(vi.mocked(svc.saveAnswer).mock.calls[1][2].selected_index).toBeNull();
  });

  it("toggles review marks and keeps the existing answer", async () => {
    vi.mocked(svc.saveAnswer).mockResolvedValue(answer(2, { marked_for_review: true }));
    await state().selectAnswer(first().question_id, 2);
    await state().toggleMark(first().question_id);
    expect(first().marked_for_review).toBe(true);
    expect(vi.mocked(svc.saveAnswer).mock.calls[1][2]).toMatchObject({ selected_index: 2, marked_for_review: true });
    await state().toggleMark(first().question_id);
    expect(first().marked_for_review).toBe(false);
  });

  it("reverts a mark that failed to save", async () => {
    vi.mocked(svc.saveAnswer).mockRejectedValue(apiError(500, "X", "nope"));
    await state().toggleMark(first().question_id);
    expect(first().marked_for_review).toBe(false);
  });

  it("stores feedback and refuses to change a locked answer", async () => {
    vi.mocked(svc.getSession).mockResolvedValue(session({ immediate_feedback: true, exam_mode: false }));
    await state().loadSession("s".repeat(24));
    const fb = { is_correct: false, correct_index: 2, explanation: "Because.", formula: null };
    vi.mocked(svc.saveAnswer).mockResolvedValue(answer(0, { locked: true, feedback: fb }));
    await state().selectAnswer(first().question_id, 0);
    expect(first().locked).toBe(true);
    expect(first().feedback).toEqual(fb);
    await state().selectAnswer(first().question_id, 1);
    expect(svc.saveAnswer).toHaveBeenCalledTimes(1);
    expect(first().selected_index).toBe(0);
  });

  it("flags the session as ended when the server says time is up, and does not roll back", async () => {
    vi.mocked(svc.saveAnswer).mockRejectedValue(apiError(409, "SESSION_EXPIRED", "Time is up."));
    await state().selectAnswer(first().question_id, 1);
    expect(state().ended).toBe(true);
    expect(first().selected_index).toBe(1);
  });

  it("does nothing once the session has ended", async () => {
    useAptitudeStore.setState({ ended: true });
    await state().selectAnswer(first().question_id, 1);
    await state().toggleMark(first().question_id);
    expect(svc.saveAnswer).not.toHaveBeenCalled();
  });

  it("navigates within bounds", () => {
    state().goTo(2);
    expect(state().currentIndex).toBe(2);
    state().goTo(3);
    state().goTo(-1);
    expect(state().currentIndex).toBe(2);
  });
});

describe("submitting", () => {
  beforeEach(async () => {
    vi.mocked(svc.getSession).mockResolvedValue(session());
    await state().loadSession("s".repeat(24));
  });

  it("submits once even when clicked repeatedly or raced by the auto-submit", async () => {
    let release!: (r: AptitudeResult) => void;
    vi.mocked(svc.submitSession).mockReturnValue(new Promise((r) => { release = r; }));
    const a = state().submit();
    const b = state().submit();
    const c = state().submit();
    expect(state().isSubmitting).toBe(true);
    release(result());
    const [ra] = await Promise.all([a, b, c]);
    expect(svc.submitSession).toHaveBeenCalledTimes(1);
    expect(ra?.score).toBe(1);
    expect(state().ended).toBe(true);
    expect(state().isSubmitting).toBe(false);
  });

  it("keeps the session open and shows an error if submission fails, so it can be retried", async () => {
    vi.mocked(svc.submitSession).mockRejectedValueOnce(apiError(500, "X", "Server down")).mockResolvedValueOnce(result());
    expect(await state().submit()).toBeNull();
    expect(state().ended).toBe(false);
    expect(state().answerError).toBe("Server down");
    expect((await state().submit())?.session_id).toBe("s".repeat(24));
  });

  it("loads a stored result and reports failures", async () => {
    vi.mocked(svc.getResult).mockRejectedValueOnce(apiError(409, "SESSION_NOT_FINISHED", "Results are available after the session is submitted."));
    await state().loadResult("s".repeat(24));
    expect(state().resultStatus).toBe("error");
    vi.mocked(svc.getResult).mockResolvedValueOnce(result());
    await state().loadResult("s".repeat(24));
    expect(state().result?.score).toBe(1);
  });
});

describe("progress and reset", () => {
  it("loads progress and recommendations together", async () => {
    vi.mocked(svc.getProgress).mockResolvedValue({ sessions_completed: 0 } as never);
    vi.mocked(svc.getRecommendations).mockResolvedValue({ has_history: false, weak_topics: [] } as never);
    await state().loadProgress();
    expect(state().progressStatus).toBe("ready");
    expect(state().recommendations?.has_history).toBe(false);
  });
  it("one failing request puts progress in an error state", async () => {
    vi.mocked(svc.getProgress).mockResolvedValue({} as never);
    vi.mocked(svc.getRecommendations).mockRejectedValue(apiError(500, "X", "boom"));
    await state().loadProgress();
    expect(state().progressStatus).toBe("error");
  });
  it("reset wipes everything belonging to the previous user", async () => {
    vi.mocked(svc.getSession).mockResolvedValue(session());
    await state().loadSession("s".repeat(24));
    state().reset();
    expect(state().session).toBeNull();
    expect(state().sessionStatus).toBe("idle");
    expect(state().result).toBeNull();
  });
});
