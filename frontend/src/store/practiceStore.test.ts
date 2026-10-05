import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PracticeSessionState } from "@/features/cybersecurity/cybersecurityTypes";

vi.mock("@/services/cybersecurityService", () => ({
  startPractice: vi.fn(),
  startPracticeSession: vi.fn(),
  getPracticeSession: vi.fn(),
  submitAnswer: vi.fn(),
  requestPracticeHint: vi.fn(),
  requestNextQuestion: vi.fn(),
  completePractice: vi.fn(),
}));

import * as svc from "@/services/cybersecurityService";
import { usePracticeStore } from "./practiceStore";

const mocked = vi.mocked(svc);

function session(over: Partial<PracticeSessionState> = {}): PracticeSessionState {
  return {
    session_id: "s1", mode: "scenario", status: "in_progress", topic_slug: "t", topic_title: "T",
    category: "SOC", categories: ["SOC"], difficulty: "beginner", difficulty_mode: "fixed",
    question_type: "scenario", question_count: 2, started_at: null, time_limit_seconds: null,
    remaining_seconds: null, note: null, focus: [], has_more_questions: true, can_request_next: false,
    summary: null,
    questions: [{
      question_id: "q1", index: 0, question: "?", type: "scenario", options: null, topic_title: "T",
      category: "SOC", difficulty: "beginner", hints_available: 3, hints_used: 0, hints: [], answered: false,
      result: null,
    }],
    ...over,
  };
}

const result = { score: 80, correct: true, feedback: "ok", ideal_answer: null, missing_points: [] };

beforeEach(() => {
  vi.clearAllMocks();
  usePracticeStore.getState().reset();
});

describe("practiceStore", () => {
  it("resumes a session from the server and opens the first unanswered question", async () => {
    const s = session();
    s.questions[0].answered = true;
    s.questions.push({ ...s.questions[0], question_id: "q2", index: 1, answered: false });
    mocked.getPracticeSession.mockResolvedValue(s);
    await usePracticeStore.getState().load("s1");
    expect(usePracticeStore.getState().currentIndex).toBe(1);
  });

  it("derives a timer deadline from the server's remaining seconds", async () => {
    mocked.getPracticeSession.mockResolvedValue(session({ remaining_seconds: 600, time_limit_seconds: 900 }));
    const before = Date.now();
    await usePracticeStore.getState().load("s1");
    const deadline = usePracticeStore.getState().deadlineMs!;
    expect(deadline).toBeGreaterThanOrEqual(before + 599_000);
  });

  it("prevents duplicate answer submissions while one is in flight", async () => {
    mocked.getPracticeSession.mockResolvedValue(session());
    await usePracticeStore.getState().load("s1");
    let release!: (v: typeof result) => void;
    mocked.submitAnswer.mockReturnValue(new Promise((r) => { release = r; }));

    const first = usePracticeStore.getState().submitCurrentAnswer("a");
    await usePracticeStore.getState().submitCurrentAnswer("a"); // ignored
    release(result);
    await first;

    expect(mocked.submitAnswer).toHaveBeenCalledTimes(1);
    expect(usePracticeStore.getState().session!.questions[0].answered).toBe(true);
    // and an answered question can't be submitted again
    await usePracticeStore.getState().submitCurrentAnswer("b");
    expect(mocked.submitAnswer).toHaveBeenCalledTimes(1);
  });

  it("appends hints in order and keeps the question unanswered", async () => {
    mocked.getPracticeSession.mockResolvedValue(session());
    await usePracticeStore.getState().load("s1");
    mocked.requestPracticeHint.mockResolvedValueOnce({
      kind: "hint", hint_number: 1, hint: "h1", hints_used: 1, hints_remaining: 2, max_score: 95,
    });
    await usePracticeStore.getState().requestHint();
    const q = usePracticeStore.getState().session!.questions[0];
    expect(q.hints).toEqual(["h1"]);
    expect(q.hints_used).toBe(1);
    expect(q.answered).toBe(false);
  });

  it("generates the next question only after the last one is answered, then finishes", async () => {
    const s = session();
    mocked.getPracticeSession.mockResolvedValue(s);
    await usePracticeStore.getState().load("s1");
    const next = session({
      has_more_questions: false,
      questions: [{ ...s.questions[0], answered: true, result }, { ...s.questions[0], question_id: "q2", index: 1 }],
    });
    mocked.requestNextQuestion.mockResolvedValue({ question: next.questions[1], state: next });
    await usePracticeStore.getState().goToNext();
    expect(mocked.requestNextQuestion).toHaveBeenCalledTimes(1);
    expect(usePracticeStore.getState().currentIndex).toBe(1);

    mocked.completePractice.mockResolvedValue({} as never);
    mocked.getPracticeSession.mockResolvedValue({ ...next, status: "completed" });
    // answer q2 locally, then Finish
    usePracticeStore.setState((st) => ({
      session: { ...st.session!, questions: st.session!.questions.map((x) => ({ ...x, answered: true, result })) },
    }));
    await usePracticeStore.getState().goToNext();
    expect(mocked.completePractice).toHaveBeenCalledTimes(1);
    expect(usePracticeStore.getState().session!.status).toBe("completed");
  });

  it("keeps the typed draft so a timer expiry can still save it", () => {
    usePracticeStore.getState().setDraft("q1", "my draft");
    expect(usePracticeStore.getState().drafts.q1).toBe("my draft");
  });
});
