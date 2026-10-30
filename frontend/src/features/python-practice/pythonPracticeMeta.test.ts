import { describe, expect, it } from "vitest";
import {
  availableQuestions, buildSessionRequest, CODE_MODES, completionPercent, defaultForm, isAnswered, MAX_CODE_CHARS, MAX_QUESTIONS, MODE_BY_ID, MODES, navState, sessionCounts,
} from "@/features/python-practice/pythonPracticeMeta";
import type { SessionQuestion, Syllabus } from "@/types/pythonPractice";

const topic = (id: string, n: number) => ({ id, title: id, question_count: n, by_difficulty: { easy: n, medium: 0, hard: 0 }, by_format: {}, by_interaction: {}, status: "implemented" as const });
const syllabus = {
  units: [
    { id: "unit-a", code: "A", title: "A", summary: "", question_count: 5, topics_implemented: 2, topics_total: 2, topics: [topic("loops", 2), topic("lists", 3)] },
    { id: "unit-d", code: "D", title: "D", summary: "", question_count: 4, topics_implemented: 1, topics_total: 1, topics: [topic("mro", 4)] },
  ],
  question_total: 9, min_questions_per_topic: 2, topics_implemented: 3, topics_total: 4,
} as unknown as Syllabus;
const q = (over: Partial<SessionQuestion>) => ({ interaction: "mcq", selected_index: null, text_answer: null, code_answer: null, marked_for_review: false, ...over }) as SessionQuestion;

describe("modes", () => {
  it("defines the fourteen required practice modes exactly once", () => {
    expect(MODES.map((m) => m.id).sort()).toEqual(["advanced", "coding", "complete", "complexity", "debug", "interview", "mixed", "oop", "predict_output", "security", "timed_mock", "topic", "trace", "weak"]);
  });
  it("marks exactly the modes that need the code runner", () => {
    expect([...CODE_MODES].sort()).toEqual(["coding", "complete", "debug"]);
  });
  it("only the timed mock requires a timer and hides feedback", () => {
    expect(MODES.filter((m) => m.timer === "required").map((m) => m.id)).toEqual(["timed_mock"]);
    expect(MODES.filter((m) => !m.allowsFeedback).map((m) => m.id)).toEqual(["timed_mock"]);
  });
  it("fixes the unit for OOP, advanced and cybersecurity modes", () => {
    expect(MODE_BY_ID.oop.fixedUnits).toEqual(["unit-d"]);
    expect(MODE_BY_ID.advanced.fixedUnits).toEqual(["unit-f"]);
    expect(MODE_BY_ID.security.fixedUnits).toEqual(["unit-h"]);
  });
});

describe("buildSessionRequest", () => {
  it("requires a topic for topic practice", () => {
    expect(buildSessionRequest(defaultForm("topic"))).toEqual({ ok: false, error: "Choose at least one topic." });
  });
  it("builds a minimal whitelisted request", () => {
    const r = buildSessionRequest({ ...defaultForm("topic"), topicIds: ["loops"], difficulty: "hard", questionCount: 7 });
    expect(r).toEqual({ ok: true, request: { mode: "topic", question_count: 7, topic_ids: ["loops"], difficulty: "hard", immediate_feedback: true } });
  });
  it("prefers topics over units and omits scope for fixed-scope modes", () => {
    const both = buildSessionRequest({ ...defaultForm("mixed"), topicIds: ["loops"], unitIds: ["unit-a"] });
    expect(both.ok && both.request.unit_ids).toBeUndefined();
    const oop = buildSessionRequest({ ...defaultForm("oop"), unitIds: ["unit-a"] });
    expect(oop.ok && "unit_ids" in oop.request).toBe(false);
  });
  it("validates question counts and timers", () => {
    expect(buildSessionRequest({ ...defaultForm("mixed"), questionCount: 0 }).ok).toBe(false);
    expect(buildSessionRequest({ ...defaultForm("mixed"), questionCount: MAX_QUESTIONS + 1 }).ok).toBe(false);
    expect(buildSessionRequest({ ...defaultForm("mixed"), questionCount: 2.5 }).ok).toBe(false);
    expect(buildSessionRequest({ ...defaultForm("timed_mock"), timerMinutes: 0 }).ok).toBe(false);
    expect(buildSessionRequest({ ...defaultForm("timed_mock"), timerMinutes: 181 }).ok).toBe(false);
  });
  it("always sends a timer for the mock and never sends feedback preference for it", () => {
    const r = buildSessionRequest({ ...defaultForm("timed_mock"), timerMinutes: 20 });
    expect(r).toEqual({ ok: true, request: { mode: "timed_mock", question_count: 10, timer_minutes: 20 } });
  });
  it("only sends a timer in other modes when the learner turned it on", () => {
    const off = buildSessionRequest({ ...defaultForm("mixed"), useTimer: false });
    expect(off.ok && off.request.timer_minutes).toBeUndefined();
    const on = buildSessionRequest({ ...defaultForm("mixed"), useTimer: true, timerMinutes: 12 });
    expect(on.ok && on.request.timer_minutes).toBe(12);
  });
  it("never includes a score, user id or correctness field", () => {
    const r = buildSessionRequest({ ...defaultForm("mixed") });
    expect(r.ok && Object.keys(r.request).every((k) => ["mode", "question_count", "immediate_feedback", "unit_ids", "topic_ids", "difficulty", "timer_minutes"].includes(k))).toBe(true);
  });
  it("exposes the source-size limit that mirrors the server", () => {
    expect(MAX_CODE_CHARS).toBe(10000);
  });
});

describe("availableQuestions and completion", () => {
  it("uses real syllabus counts for each scope", () => {
    expect(availableQuestions(syllabus, defaultForm("mixed"))).toBe(9);
    expect(availableQuestions(syllabus, { ...defaultForm("mixed"), unitIds: ["unit-a"] })).toBe(5);
    expect(availableQuestions(syllabus, { ...defaultForm("topic"), topicIds: ["loops", "mro"] })).toBe(6);
    expect(availableQuestions(syllabus, defaultForm("oop"))).toBe(4);
    expect(availableQuestions(null, defaultForm("mixed"))).toBeNull();
  });
  it("computes completion from implemented topics, not a constant", () => {
    expect(completionPercent(syllabus)).toBe(75);
    expect(completionPercent(null)).toBe(0);
    expect(completionPercent({ ...syllabus, topics_total: 0 })).toBe(0);
  });
});

describe("session helpers", () => {
  it("knows when each interaction type counts as answered", () => {
    expect(isAnswered(q({ selected_index: 0 }))).toBe(true);
    expect(isAnswered(q({}))).toBe(false);
    expect(isAnswered(q({ interaction: "short", text_answer: "  x " }))).toBe(true);
    expect(isAnswered(q({ interaction: "short", text_answer: "   " }))).toBe(false);
    expect(isAnswered(q({ interaction: "code", code_answer: "pass" }))).toBe(true);
    expect(isAnswered(q({ interaction: "code", code_answer: " " }))).toBe(false);
  });
  it("gives marked questions priority over current and answered", () => {
    expect(navState(q({ marked_for_review: true, selected_index: 1 }), true)).toBe("marked");
    expect(navState(q({}), true)).toBe("current");
    expect(navState(q({ selected_index: 1 }), false)).toBe("answered");
    expect(navState(q({}), false)).toBe("unanswered");
  });
  it("counts answered, unanswered and marked questions", () => {
    expect(sessionCounts([q({ selected_index: 0 }), q({}), q({ marked_for_review: true })])).toEqual({ total: 3, answered: 1, unanswered: 2, marked: 1 });
  });
});
