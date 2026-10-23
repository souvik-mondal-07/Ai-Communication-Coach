import { describe, expect, it } from "vitest";
import {
  availableQuestions, buildSessionRequest, completionPercent, defaultForm, formatArgs, isAnswered, MODE_BY_ID, MODES, navState, sessionCounts,
} from "@/features/dsa/dsaMeta";
import type { SessionQuestion, Syllabus } from "@/types/dsa";

const sub = (id: string, by_format: Record<string, number>, auto: number) => ({
  id, title: id, question_count: Object.values(by_format).reduce((a, b) => a + b, 0), by_difficulty: { easy: 1, medium: 1, hard: 1 }, by_format, auto_graded: auto,
  self_assessed_code: by_format.coding ? 1 : 0, status: "implemented" as const,
});
const SYLLABUS = {
  topics: [
    { id: "arrays", code: "B", title: "Arrays", summary: "", question_count: 0, items: [], subtopics_implemented: 2, subtopics_total: 2, status: "implemented", subtopics: [sub("array-memory", { conceptual: 3, complexity: 1 }, 4), sub("array-traversal", { output: 2, coding: 3 }, 4)] },
    { id: "graphs", code: "J", title: "Graphs", summary: "", question_count: 0, items: [], subtopics_implemented: 1, subtopics_total: 1, status: "implemented", subtopics: [sub("bfs", { trace: 4, scenario: 1, coding: 2 }, 5)] },
  ],
  totals: { topics: 2, subtopics: 3, subtopics_implemented: 3, questions: 20, by_format: {}, min_questions_per_subtopic: 4 },
  execution: { automated_code_execution: false, mode: "self_assessed", message: "x" },
} as unknown as Syllabus;

const q = (over: Partial<SessionQuestion>): SessionQuestion => ({
  question_id: "dsa-0000000001", topic_id: "arrays", subtopic_id: "array-memory", format: "conceptual", interaction: "mcq", coding_type: null, difficulty: "easy", statement: "s", code: null,
  options: ["a", "b", "c", "d"], constraints: null, est_time_seconds: 30, coding: null, selected_index: null, code_answer: null, marked_for_review: false, locked: false, hints: [], feedback: null, ...over,
});

describe("modes", () => {
  it("defines the seven practice modes of the spec", () => {
    expect(MODES.map((m) => m.id)).toEqual(["topic", "interview", "tracing", "complexity", "coding", "timed_mock", "weak"]);
    expect(MODE_BY_ID.timed_mock.timer).toBe("required");
    expect(MODE_BY_ID.timed_mock.allowsFeedback).toBe(false);
    expect(MODE_BY_ID.weak.canPickTopics).toBe(false);
  });
});

describe("buildSessionRequest", () => {
  it("requires a topic for topic practice", () => {
    expect(buildSessionRequest(defaultForm("topic"))).toEqual({ ok: false, error: "Choose at least one topic or subtopic." });
    const r = buildSessionRequest({ ...defaultForm("topic"), topicIds: ["arrays"] });
    expect(r.ok && r.request).toMatchObject({ mode: "topic", topic_ids: ["arrays"], question_count: 10, immediate_feedback: true });
  });
  it("sends only what the server needs: no user id, score or answers", () => {
    const r = buildSessionRequest({ ...defaultForm("interview"), difficulty: "hard", questionCount: 7 });
    expect(r.ok && Object.keys(r.request).sort()).toEqual(["difficulty", "immediate_feedback", "mode", "question_count", "subtopic_ids", "topic_ids"]);
  });
  it("a timed mock always has a timer and never asks for immediate feedback", () => {
    const r = buildSessionRequest(defaultForm("timed_mock"));
    expect(r.ok && r.request.timer_minutes).toBe(30);
    expect(r.ok && "immediate_feedback" in r.request).toBe(false);
  });
  it("only sends a timer for optional modes when it is switched on", () => {
    expect((buildSessionRequest(defaultForm("tracing")) as { ok: true; request: { timer_minutes?: number } }).request.timer_minutes).toBeUndefined();
    const r = buildSessionRequest({ ...defaultForm("tracing"), useTimer: true, timerMinutes: 15 });
    expect(r.ok && r.request.timer_minutes).toBe(15);
  });
  it("weak-topic revision sends no topic filters", () => {
    const r = buildSessionRequest({ ...defaultForm("weak"), topicIds: ["arrays"] });
    expect(r.ok && r.request.topic_ids).toEqual([]);
  });
  it("rejects out-of-range counts and timers", () => {
    for (const questionCount of [0, 51, 2.5, Number.NaN]) expect(buildSessionRequest({ ...defaultForm("interview"), questionCount }).ok).toBe(false);
    expect(buildSessionRequest({ ...defaultForm("timed_mock"), timerMinutes: 0 }).ok).toBe(false);
    expect(buildSessionRequest({ ...defaultForm("timed_mock"), timerMinutes: 181 }).ok).toBe(false);
  });
});

describe("availableQuestions (real counts, never invented)", () => {
  it("is null until the syllabus has loaded", () => expect(availableQuestions(null, defaultForm("interview"))).toBeNull());
  it("uses the mode's formats", () => {
    expect(availableQuestions(SYLLABUS, defaultForm("interview"))).toBe(3 + 1 + 1); // conceptual + complexity + scenario
    expect(availableQuestions(SYLLABUS, defaultForm("tracing"))).toBe(2 + 4); // output + trace
    expect(availableQuestions(SYLLABUS, defaultForm("coding"))).toBe(3 + 2);
    expect(availableQuestions(SYLLABUS, defaultForm("complexity"))).toBe(1);
  });
  it("scored modes count only auto-gradable questions", () => expect(availableQuestions(SYLLABUS, { ...defaultForm("timed_mock") })).toBe(4 + 4 + 5));
  it("respects topic and subtopic scope", () => {
    expect(availableQuestions(SYLLABUS, { ...defaultForm("topic"), topicIds: ["graphs"] })).toBe(5);
    expect(availableQuestions(SYLLABUS, { ...defaultForm("topic"), subtopicIds: ["array-memory"] })).toBe(4);
  });
  it("completion percent comes from implemented subtopics", () => {
    expect(completionPercent(SYLLABUS)).toBe(100);
    expect(completionPercent({ ...SYLLABUS, totals: { ...SYLLABUS.totals, subtopics_implemented: 1 } })).toBe(33);
    expect(completionPercent(null)).toBe(0);
  });
});

describe("answer state", () => {
  it("counts a saved option or non-blank code as answered", () => {
    expect(isAnswered(q({}))).toBe(false);
    expect(isAnswered(q({ selected_index: 0 }))).toBe(true);
    expect(isAnswered(q({ interaction: "code", code_answer: "   " }))).toBe(false);
    expect(isAnswered(q({ interaction: "code", code_answer: "def f(): pass" }))).toBe(true);
  });
  it("navigator states: marked wins, then current, then answered", () => {
    expect(navState(q({ marked_for_review: true, selected_index: 1 }), true)).toBe("marked");
    expect(navState(q({}), true)).toBe("current");
    expect(navState(q({ selected_index: 2 }), false)).toBe("answered");
    expect(navState(q({}), false)).toBe("unanswered");
  });
  it("session counts include coding answers", () => {
    const c = sessionCounts([q({ selected_index: 1 }), q({ interaction: "code", code_answer: "x = 1" }), q({ marked_for_review: true }), q({})]);
    expect(c).toEqual({ total: 4, answered: 2, unanswered: 2, marked: 1 });
  });
  it("formats test arguments compactly", () => expect(formatArgs([[1, 2], "a", null])).toBe('[1,2], "a", null'));
});
