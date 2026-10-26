import { describe, expect, it } from "vitest";
import {
  availableQuestions, buildSessionRequest, completionPercent, defaultForm, formatCell, isAnswered, MODE_BY_ID, MODES, navState, sessionCounts, type SetupForm,
} from "@/features/dbms-sql/dbmsSqlMeta";
import type { SessionQuestion, Syllabus } from "@/types/dbmsSql";

const form = (over: Partial<SetupForm> = {}): SetupForm => ({ ...defaultForm("mixed"), ...over });
const q = (over: Partial<SessionQuestion> = {}): SessionQuestion => ({
  question_id: "dbq-0000000001", unit_id: "unit-a", topic_id: "keys", format: "concept", interaction: "mcq", dialect: "standard", difficulty: "easy", statement: "s", code: null, options: ["a", "b", "c", "d"],
  dataset_id: null, est_time_seconds: 30, tags: [], short: null, sql: null, selected_index: null, text_answer: null, sql_answer: null, marked_for_review: false, locked: false, checks: 0, hints_total: 0,
  hints_used: 0, hints: [], last_check: null, feedback: null, ...over,
});
const topic = (id: string, n: number) => ({ id, title: id, question_count: n, by_difficulty: { easy: 0, medium: 0, hard: 0 }, by_format: {}, by_interaction: {}, status: "implemented" as const });
const syllabus = (): Syllabus => ({
  units: [
    { id: "unit-a", code: "A", title: "A", summary: "", question_count: 30, topics_implemented: 2, topics_total: 2, topics: [topic("t1", 10), topic("t2", 20)] },
    { id: "unit-d", code: "D", title: "D", summary: "", question_count: 40, topics_implemented: 1, topics_total: 1, topics: [topic("t3", 40)] },
  ],
  question_total: 70, min_questions_per_topic: 3, topics_implemented: 3, topics_total: 4,
  sql_engine: { engine: "SQLite", version: "3", window_functions: true, right_full_join: true, dialect: "sqlite", read_only: true, limits: { max_sql_chars: 1, max_rows: 1, max_seconds: 1, supported_statements: [] } },
});

describe("practice modes", () => {
  it("defines all twelve modes with unique ids", () => {
    expect(MODES).toHaveLength(12);
    expect(new Set(MODES.map((m) => m.id)).size).toBe(12);
    expect(MODES.map((m) => m.id)).toEqual(expect.arrayContaining(["topic", "mixed", "interview", "sql_lab", "predict_output", "debug", "complete", "design_lab", "transaction_lab", "nosql_lab", "timed_mock", "weak"]));
  });
  it("only the timed mock forbids feedback and requires a timer", () => {
    expect(MODES.filter((m) => !m.allowsFeedback).map((m) => m.id)).toEqual(["timed_mock"]);
    expect(MODES.filter((m) => m.timer === "required").map((m) => m.id)).toEqual(["timed_mock"]);
  });
  it("the three labs pin their unit and take no scope", () => {
    for (const [mode, unit] of [["design_lab", "unit-d"], ["transaction_lab", "unit-f"], ["nosql_lab", "unit-g"]] as const) {
      expect(MODE_BY_ID[mode].fixedUnits).toEqual([unit]);
      expect(MODE_BY_ID[mode].canPickScope).toBe(false);
    }
  });
});

describe("buildSessionRequest", () => {
  it("topic practice needs a topic", () => {
    expect(buildSessionRequest(defaultForm("topic"))).toEqual({ ok: false, error: "Choose at least one topic." });
    const r = buildSessionRequest({ ...defaultForm("topic"), topicIds: ["keys"] });
    expect(r.ok && r.request).toMatchObject({ mode: "topic", topic_ids: ["keys"], question_count: 10, immediate_feedback: true });
  });
  it.each([0, 51, 2.5, NaN, -3])("rejects question count %s", (n) => {
    const r = buildSessionRequest(form({ questionCount: n }));
    expect(r.ok).toBe(false);
    expect(!r.ok && r.error).toContain("between 1 and 50");
  });
  it("accepts the bounds", () => {
    expect(buildSessionRequest(form({ questionCount: 1 })).ok).toBe(true);
    expect(buildSessionRequest(form({ questionCount: 50 })).ok).toBe(true);
  });
  it("topics win over units and neither is sent for fixed-scope modes", () => {
    const both = buildSessionRequest(form({ topicIds: ["t1"], unitIds: ["unit-a"] }));
    expect(both.ok && both.request).toMatchObject({ topic_ids: ["t1"] });
    expect(both.ok && both.request).not.toHaveProperty("unit_ids");
    const unit = buildSessionRequest(form({ unitIds: ["unit-a"] }));
    expect(unit.ok && unit.request).toMatchObject({ unit_ids: ["unit-a"] });
    const lab = buildSessionRequest({ ...defaultForm("design_lab"), unitIds: ["unit-a"], topicIds: ["t1"] });
    expect(lab.ok && lab.request).not.toHaveProperty("unit_ids");
    expect(lab.ok && lab.request).not.toHaveProperty("topic_ids");
  });
  it("sends difficulty only when chosen", () => {
    expect((buildSessionRequest(form()) as { request: object }).request).not.toHaveProperty("difficulty");
    expect((buildSessionRequest(form({ difficulty: "hard" })) as { request: object }).request).toMatchObject({ difficulty: "hard" });
  });
  it("timer rules: optional unless chosen, required for the mock, bounded", () => {
    expect((buildSessionRequest(form()) as { request: object }).request).not.toHaveProperty("timer_minutes");
    expect((buildSessionRequest(form({ useTimer: true, timerMinutes: 12 })) as { request: object }).request).toMatchObject({ timer_minutes: 12 });
    const mock = buildSessionRequest(defaultForm("timed_mock"));
    expect(mock.ok && mock.request).toMatchObject({ mode: "timed_mock", question_count: 20 });
    expect(mock.ok && mock.request).not.toHaveProperty("immediate_feedback");
    expect(buildSessionRequest({ ...defaultForm("timed_mock"), timerMinutes: 0 }).ok).toBe(false);
    expect(buildSessionRequest({ ...defaultForm("timed_mock"), timerMinutes: 181 }).ok).toBe(false);
  });
  it("never includes a user id, score or answer data", () => {
    const r = buildSessionRequest(form({ topicIds: ["t1"], difficulty: "easy", useTimer: true, timerMinutes: 5 }));
    expect(Object.keys((r as { request: object }).request).every((k) => ["mode", "topic_ids", "difficulty", "question_count", "timer_minutes", "immediate_feedback"].includes(k))).toBe(true);
  });
});

describe("availableQuestions and completion", () => {
  it("follows the scope using real counts", () => {
    expect(availableQuestions(null, form())).toBeNull();
    expect(availableQuestions(syllabus(), form())).toBe(70);
    expect(availableQuestions(syllabus(), form({ unitIds: ["unit-a"] }))).toBe(30);
    expect(availableQuestions(syllabus(), form({ topicIds: ["t1", "t3"] }))).toBe(50);
    expect(availableQuestions(syllabus(), defaultForm("design_lab"))).toBe(40);
  });
  it("completion percent is derived, and zero when empty", () => {
    expect(completionPercent(syllabus())).toBe(75);
    expect(completionPercent(null)).toBe(0);
    expect(completionPercent({ ...syllabus(), topics_total: 0 })).toBe(0);
  });
});

describe("session helpers", () => {
  it("isAnswered handles each interaction", () => {
    expect(isAnswered(q())).toBe(false);
    expect(isAnswered(q({ selected_index: 0 }))).toBe(true);
    expect(isAnswered(q({ interaction: "short", text_answer: "  " }))).toBe(false);
    expect(isAnswered(q({ interaction: "short", text_answer: "ABC" }))).toBe(true);
    expect(isAnswered(q({ interaction: "sql", sql_answer: "" }))).toBe(false);
    expect(isAnswered(q({ interaction: "sql", sql_answer: "SELECT 1" }))).toBe(true);
  });
  it("navState prioritises marked, then current, then answered", () => {
    expect(navState(q({ marked_for_review: true, selected_index: 1 }), true)).toBe("marked");
    expect(navState(q(), true)).toBe("current");
    expect(navState(q({ selected_index: 1 }), false)).toBe("answered");
    expect(navState(q(), false)).toBe("unanswered");
  });
  it("sessionCounts", () => {
    expect(sessionCounts([q({ selected_index: 0 }), q({ marked_for_review: true }), q()])).toEqual({ total: 3, answered: 1, unanswered: 2, marked: 1 });
  });
  it("formatCell shows NULL in words", () => {
    expect(formatCell(null)).toBe("NULL");
    expect(formatCell(0)).toBe("0");
    expect(formatCell("")).toBe("");
    expect(formatCell(1.5)).toBe("1.5");
  });
});
