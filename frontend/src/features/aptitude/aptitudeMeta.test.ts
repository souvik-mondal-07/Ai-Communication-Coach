import { describe, expect, it } from "vitest";
import {
  availableQuestions, buildSessionRequest, completionPercent, defaultForm, formatClock, formatDuration, MODES, navState, remainingSeconds, sessionCounts, accuracyTone, apiErrorCode,
} from "./aptitudeMeta";
import type { SessionQuestion, Syllabus } from "@/types/aptitude";

const q = (over: Partial<SessionQuestion> = {}): SessionQuestion => ({
  question_id: "apt-0000000001", topic_id: "t", subtopic_id: "s", question_type: "direct", difficulty: "easy", statement: "x", options: ["a", "b", "c", "d"],
  est_time_seconds: 30, data: null, selected_index: null, marked_for_review: false, locked: false, feedback: null, ...over,
});
const syllabus = (): Syllabus => ({
  totals: { topics: 2, subtopics: 3, subtopics_implemented: 2, questions: 14, min_questions_per_subtopic: 4 },
  topics: [
    { id: "a", code: "A", title: "A", section: "S", summary: "", question_count: 9, items: [], subtopics_implemented: 1, subtopics_total: 2, status: "partial", subtopics: [
      { id: "a1", title: "a1", question_count: 6, by_difficulty: { easy: 3, medium: 2, hard: 1 }, status: "implemented" },
      { id: "a2", title: "a2", question_count: 3, by_difficulty: { easy: 3, medium: 0, hard: 0 }, status: "partial" }] },
    { id: "b", code: "B", title: "B", section: "S", summary: "", question_count: 5, items: [], subtopics_implemented: 1, subtopics_total: 1, status: "implemented", subtopics: [
      { id: "b1", title: "b1", question_count: 5, by_difficulty: { easy: 0, medium: 5, hard: 0 }, status: "implemented" }] },
  ],
});

describe("formatting", () => {
  it("formats the countdown clock", () => {
    expect(formatClock(0)).toBe("0:00");
    expect(formatClock(59)).toBe("0:59");
    expect(formatClock(600)).toBe("10:00");
    expect(formatClock(3725)).toBe("1:02:05");
    expect(formatClock(-5)).toBe("0:00");
  });
  it("formats durations", () => {
    expect(formatDuration(45)).toBe("45 s");
    expect(formatDuration(120)).toBe("2 min");
    expect(formatDuration(150)).toBe("2 min 30 s");
  });
  it("tones accuracy with explicit bands", () => {
    expect([accuracyTone(100), accuracyTone(70), accuracyTone(69.9), accuracyTone(40), accuracyTone(39.9)]).toEqual(["success", "success", "warn", "warn", "danger"]);
  });
});

describe("remainingSeconds", () => {
  const exp = "2026-10-18T10:00:00Z";
  const t = Date.parse("2026-10-18T09:58:30Z");
  it("is null for untimed sessions", () => expect(remainingSeconds(null, t, 0)).toBeNull());
  it("counts down to the server's expiry and never goes negative", () => {
    expect(remainingSeconds(exp, t, 0)).toBe(90);
    expect(remainingSeconds(exp, t + 500, 0)).toBe(90); // rounds up partial seconds
    expect(remainingSeconds(exp, t + 91_000, 0)).toBe(0);
  });
  it("uses the server clock offset, so a wrong device clock cannot add time", () => {
    // the device is 10 minutes slow; the offset corrects it back to server time
    expect(remainingSeconds(exp, t - 600_000, 600_000)).toBe(90);
    // without the offset the (slow) device would think there are 11.5 minutes left
    expect(remainingSeconds(exp, t - 600_000, 0)).toBe(690);
  });
});

describe("session request building", () => {
  it("requires a topic for topic practice", () => {
    expect(buildSessionRequest(defaultForm("topic"))).toEqual({ ok: false, error: "Choose at least one topic or subtopic." });
    expect(buildSessionRequest({ ...defaultForm("topic"), subtopicIds: ["a1"] }).ok).toBe(true);
  });
  it("needs no topic for mixed, scenario or mock modes", () => {
    for (const m of ["mixed", "scenario", "timed_mock"] as const) expect(buildSessionRequest(defaultForm(m)).ok).toBe(true);
  });
  it("always sends a timer for mock tests and never sends feedback for them", () => {
    const r = buildSessionRequest(defaultForm("timed_mock"));
    expect(r.ok && r.request.timer_minutes).toBe(30);
    expect(r.ok && "immediate_feedback" in r.request).toBe(false);
  });
  it("only sends a timer for optional modes when switched on", () => {
    expect(buildSessionRequest({ ...defaultForm("mixed"), useTimer: false }).ok && "timer_minutes" in (buildSessionRequest({ ...defaultForm("mixed"), useTimer: false }) as { request: object }).request).toBe(false);
    const on = buildSessionRequest({ ...defaultForm("mixed"), useTimer: true, timerMinutes: 12 });
    expect(on.ok && on.request.timer_minutes).toBe(12);
  });
  it("rejects out-of-range counts and timers", () => {
    for (const n of [0, 61, 2.5, NaN]) expect(buildSessionRequest({ ...defaultForm("mixed"), questionCount: n }).ok).toBe(false);
    for (const n of [0, 181, NaN]) expect(buildSessionRequest({ ...defaultForm("timed_mock"), timerMinutes: n }).ok).toBe(false);
  });
  it("drops topic filters for weak-topic practice and omits 'any' difficulty", () => {
    const w = buildSessionRequest({ ...defaultForm("weak"), topicIds: ["a"] });
    expect(w.ok && w.request.topic_ids).toEqual([]);
    expect(w.ok && "difficulty" in w.request).toBe(false);
    const h = buildSessionRequest({ ...defaultForm("mixed"), difficulty: "hard" });
    expect(h.ok && h.request.difficulty).toBe("hard");
  });
  it("never includes a user id, score or answer key", () => {
    const r = buildSessionRequest({ ...defaultForm("timed_mock"), topicIds: ["a"] });
    expect(r.ok && Object.keys(r.request).sort()).toEqual(["mode", "question_count", "subtopic_ids", "timer_minutes", "topic_ids"]);
  });
  it("describes five practice modes", () => expect(MODES.map((m) => m.id)).toEqual(["topic", "scenario", "timed_mock", "mixed", "weak"]));
});

describe("coverage numbers come from real counts", () => {
  it("counts available questions by scope and difficulty", () => {
    const s = syllabus();
    expect(availableQuestions(s, defaultForm("mixed"))).toBe(14);
    expect(availableQuestions(s, { ...defaultForm("mixed"), topicIds: ["a"] })).toBe(9);
    expect(availableQuestions(s, { ...defaultForm("topic"), subtopicIds: ["a2"] })).toBe(3);
    expect(availableQuestions(s, { ...defaultForm("mixed"), difficulty: "medium" })).toBe(7);
    expect(availableQuestions(null, defaultForm("mixed"))).toBeNull();
  });
  it("computes syllabus completion and handles an empty syllabus", () => {
    expect(completionPercent(syllabus())).toBe(67);
    expect(completionPercent(null)).toBe(0);
    expect(completionPercent({ ...syllabus(), totals: { ...syllabus().totals, subtopics: 0 } })).toBe(0);
  });
});

describe("question navigator state", () => {
  it("prioritises marked, then current, then answered", () => {
    expect(navState(q({ marked_for_review: true, selected_index: 1 }), true)).toBe("marked");
    expect(navState(q(), true)).toBe("current");
    expect(navState(q({ selected_index: 0 }), false)).toBe("answered");
    expect(navState(q(), false)).toBe("unanswered");
  });
  it("counts answered, unanswered and marked", () => {
    expect(sessionCounts([q({ selected_index: 0 }), q({ marked_for_review: true }), q()])).toEqual({ total: 3, answered: 1, unanswered: 2, marked: 1 });
  });
  it("reads the server's error code only from API errors", () => {
    expect(apiErrorCode(new Error("x"))).toBeNull();
  });
});
