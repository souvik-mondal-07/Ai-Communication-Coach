// @vitest-environment jsdom
/** Phase 25 integration points: History Center detail rendering, history metadata, and the dashboard Quick Access link. */
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { QuickAccessCard } from "@/features/dashboard/QuickAccessCard";
import { ActivityDetailBody } from "@/features/history/ActivityDetailBody";
import { ACTIVITY_TYPES, TYPE_META } from "@/features/history/historyMeta";
import { ResultView } from "@/features/dbms-sql/ResultView";
import type { DbmsResult, DbmsSession } from "@/types/dbmsSql";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let container: HTMLDivElement;
beforeEach(() => {
  (globalThis as Record<string, unknown>).ResizeObserver ??= class { observe() {} unobserve() {} disconnect() {} };
  window.HTMLElement.prototype.animate ??= (() => ({ cancel() {}, finished: Promise.resolve() })) as never;
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
const render = (el: React.ReactElement) => act(async () => { root.render(<MemoryRouter>{el}</MemoryRouter>); });

const completed = {
  session_id: "s1", mode: "sql_lab", status: "completed", total_questions: 2, correct: 1, incorrect: 1, unanswered: 0, score: 1, accuracy: 50, time_taken_seconds: 120, average_seconds_per_question: 60,
  auto_submitted: true, started_at: "2025-01-01T00:00:00Z", finished_at: "2025-01-01T00:02:00Z", scoring_policy: "Each correct answer scores 1 mark.",
  topic_performance: [{ topic_id: "joins", topic_title: "Joins", unit_id: "unit-c", total: 2, correct: 1, incorrect: 1, unanswered: 0, accuracy: 50 }],
  revision_topics: [{ topic_id: "joins", topic_title: "Joins", accuracy: 50 }],
  questions: [
    { question_id: "dbq-0000000001", unit_id: "unit-c", topic_id: "joins", format: "concept", interaction: "mcq", dialect: "standard", difficulty: "easy", statement: "Which join keeps unmatched left rows?", code: null, dataset_id: null,
      options: ["INNER", "LEFT", "CROSS", "NATURAL"], selected_index: 1, correct_index: 1, outcome: "correct", explanation: "LEFT keeps them.", marked_for_review: false, time_spent_seconds: 4, hints_used: 0, text_answer: null,
      sql_answer: null, sql_checks: 0, revealed: false, note: null, verdict: null, actual: null, correct_answer: null, reference_sql: null, expected: null },
    { question_id: "dbq-0000000002", unit_id: "unit-c", topic_id: "joins", format: "query", interaction: "sql", dialect: "sqlite", difficulty: "medium", statement: "List unmatched departments.", code: null, dataset_id: "practice",
      options: [], selected_index: null, correct_index: null, outcome: "incorrect", explanation: "Use a LEFT JOIN.", marked_for_review: false, time_spent_seconds: 40, hints_used: 2, text_answer: null,
      sql_answer: "SELECT 1", sql_checks: 3, revealed: false, note: null, verdict: { code: "row_count", messages: ["Your query returned 1 row(s); the expected result has 2."] },
      actual: { columns: ["x"], rows: [[1]], row_count: 1, truncated: false }, correct_answer: null, reference_sql: "SELECT dept_name FROM departments", expected: { columns: ["dept_name"], rows: [["Legal"], ["HR"]], row_count: 2, truncated: false } },
  ],
} as unknown as DbmsResult;

describe("history", () => {
  it("registers the dbms_sql type with a label, module link and empty state", () => {
    const meta = TYPE_META.dbms_sql;
    expect(ACTIVITY_TYPES).toContain("dbms_sql");
    expect(meta.tab).toBe("DBMS & SQL");
    expect(meta.modulePath).toBe("/dbms-sql");
    expect(meta.sessionPath).toBe("/dbms-sql/session");
    expect(meta.empty.cta).toContain("DBMS");
  });

  it("renders a completed session as the full scored review, including your query against the reference", async () => {
    await render(<ActivityDetailBody type="dbms_sql" detail={completed} />);
    const t = container.textContent ?? "";
    expect(t).toContain("1 / 2");
    expect(t).toContain("submitted automatically when time ran out");
    expect(t).toContain("Your query");
    expect(t).toContain("SELECT dept_name FROM departments");
    expect(t).toContain("3 checks");
    expect(t).toContain("2 hints used");
    expect(t).toContain("Dialect: SQLite");
    expect(container.querySelector('a[aria-label="Practise Joins"]')?.getAttribute("href")).toBe("/dbms-sql?mode=topic&topic=joins");
  });

  it("renders an unfinished session without any answers and links back to continue it", async () => {
    const inProgress = { session_id: "s2", status: "in_progress", question_count: 3, questions: [{ selected_index: 1, sql_answer: null, text_answer: null }, { selected_index: null, sql_answer: "  ", text_answer: null }, { selected_index: null, sql_answer: "SELECT 1", text_answer: null }] } as unknown as DbmsSession;
    await render(<ActivityDetailBody type="dbms_sql" detail={inProgress} />);
    const t = container.textContent ?? "";
    expect(t).toContain("still in progress (2 of 3 answered)");
    expect(t).toContain("appear after you submit");
    expect(container.querySelector("a")?.getAttribute("href")).toBe("/dbms-sql/session/s2");
  });
});

describe("result view", () => {
  it("shows accuracy with text as well as colour, and filters questions", async () => {
    await render(<ResultView result={completed} />);
    expect(container.querySelector('[aria-label="Score 1 out of 2"]')).not.toBeNull();
    expect(container.textContent).toContain("50% accuracy");
    const incorrect = [...container.querySelectorAll<HTMLElement>('[role="radio"]')].find((b) => b.textContent?.startsWith("Incorrect"))!;
    await act(async () => incorrect.click());
    expect(container.querySelectorAll("section[aria-labelledby='review-title'] > ol > li")).toHaveLength(1);
    expect(container.textContent).toContain("Expected result");
  });
});

describe("dashboard", () => {
  it("Quick Access links to the DBMS & SQL lab", async () => {
    await render(<QuickAccessCard />);
    const link = [...container.querySelectorAll("a")].find((a) => a.textContent === "DBMS & SQL Lab");
    expect(link?.getAttribute("href")).toBe("/dbms-sql");
  });
});
