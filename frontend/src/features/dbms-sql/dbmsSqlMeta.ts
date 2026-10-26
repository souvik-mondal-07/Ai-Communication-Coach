import {
  BookOpenCheck, Bug, CircleDashed, Database, FileSearch, GitCompareArrows, Layers, MessagesSquare, Network, Table2, Target, Timer, type LucideIcon,
} from "lucide-react";
import type {
  Cell, CoverageStatus, DbmsDialect, DbmsDifficulty, DbmsFormat, DbmsMode, SessionQuestion, SessionRequest, Syllabus,
} from "@/types/dbmsSql";

// Timer / format / error helpers are shared with Phase 23 rather than duplicated.
export { accuracyTone, apiErrorCode, formatClock, formatDuration, remainingSeconds } from "@/features/aptitude/aptitudeMeta";

export const MIN_QUESTIONS = 1;
export const MAX_QUESTIONS = 50;
export const MAX_TIMER_MINUTES = 180;
export const MAX_SQL_CHARS = 4000;
export const MAX_SHORT_CHARS = 200;

export interface ModeMeta {
  id: DbmsMode;
  title: string;
  blurb: string;
  icon: LucideIcon;
  needsTopic: boolean;
  canPickScope: boolean;
  timer: "none" | "optional" | "required";
  defaultCount: number;
  allowsFeedback: boolean;
  /** Unit ids the mode always uses (the scope picker is replaced by this). */
  fixedUnits?: string[];
}

export const MODES: ModeMeta[] = [
  { id: "topic", title: "Topic practice", blurb: "Pick one or more syllabus topics and practise their questions: theory, SQL exercises and analysis problems.", icon: BookOpenCheck, needsTopic: true, canPickScope: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "mixed", title: "Mixed practice", blurb: "Questions interleaved from several syllabus units. Leave the scope empty to draw from everything.", icon: Layers, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 15, allowsFeedback: true },
  { id: "interview", title: "Technical interview", blurb: "Direct and scenario-based questions in the way interviewers ask them.", icon: MessagesSquare, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "sql_lab", title: "SQL query lab", blurb: "Write queries against the sample tables, run them, compare with the expected result and learn from the feedback.", icon: Database, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 5, allowsFeedback: true },
  { id: "predict_output", title: "Predict the output", blurb: "Read a query (or plan) and work out exactly what it returns, including NULL and duplicate behaviour.", icon: FileSearch, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "debug", title: "Debug the query", blurb: "Find and fix syntax errors and logic bugs. Your fix is graded by running it.", icon: Bug, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 5, allowsFeedback: true },
  { id: "complete", title: "Complete the query", blurb: "Fill in the missing keyword, clause or expression so the query returns the right result.", icon: CircleDashed, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 5, allowsFeedback: true },
  { id: "design_lab", title: "Database design lab", blurb: "Keys, functional dependencies, closures, normal forms and lossless decomposition. Answers are computed, not guessed.", icon: Table2, needsTopic: false, canPickScope: false, timer: "optional", defaultCount: 10, allowsFeedback: true, fixedUnits: ["unit-d"] },
  { id: "transaction_lab", title: "Transaction scenario lab", blurb: "Schedules, serializability, recoverability, locking, deadlocks and isolation anomalies.", icon: GitCompareArrows, needsTopic: false, canPickScope: false, timer: "optional", defaultCount: 10, allowsFeedback: true, fixedUnits: ["unit-f"] },
  { id: "nosql_lab", title: "NoSQL & MongoDB lab", blurb: "Document modelling, MongoDB CRUD and indexing, DynamoDB, serverless and vector databases.", icon: Network, needsTopic: false, canPickScope: false, timer: "optional", defaultCount: 10, allowsFeedback: true, fixedUnits: ["unit-g"] },
  { id: "timed_mock", title: "Timed mock interview", blurb: "Exam conditions across the syllabus: countdown, question navigator, mark for review. No answers or checking until you submit.", icon: Timer, needsTopic: false, canPickScope: true, timer: "required", defaultCount: 20, allowsFeedback: false },
  { id: "weak", title: "Weak topics", blurb: "Re-attempt what you got wrong and practise topics where your recorded accuracy is low. Needs practice history first.", icon: Target, needsTopic: false, canPickScope: false, timer: "optional", defaultCount: 10, allowsFeedback: true },
];

export const MODE_BY_ID = Object.fromEntries(MODES.map((m) => [m.id, m])) as Record<DbmsMode, ModeMeta>;
export const MODE_LABELS = Object.fromEntries(MODES.map((m) => [m.id, m.title])) as Record<DbmsMode, string>;
export const DIFFICULTY_LABELS: Record<DbmsDifficulty, string> = { easy: "Easy", medium: "Medium", hard: "Hard" };
export const COVERAGE_LABELS: Record<CoverageStatus, string> = { implemented: "Ready", partial: "Few questions", missing: "No questions yet" };
export const FORMAT_LABELS: Record<DbmsFormat, string> = {
  concept: "Concept", scenario: "Scenario", output: "Output prediction", debug: "Debug", complete: "Complete", query: "Query writing", design: "Design", transaction: "Transaction",
};
export const DIALECT_LABELS: Record<DbmsDialect, string> = {
  standard: "General concept", sqlite: "SQLite", mysql: "MySQL", postgresql: "PostgreSQL", oracle: "Oracle", sqlserver: "SQL Server", mongodb: "MongoDB", dynamodb: "DynamoDB",
};

export interface SetupForm {
  mode: DbmsMode;
  unitIds: string[];
  topicIds: string[];
  difficulty: DbmsDifficulty | "any";
  questionCount: number;
  useTimer: boolean;
  timerMinutes: number;
  immediateFeedback: boolean;
}

export function defaultForm(mode: DbmsMode = "topic"): SetupForm {
  const meta = MODE_BY_ID[mode];
  return {
    mode, unitIds: [], topicIds: [], difficulty: "any", questionCount: meta.defaultCount,
    useTimer: meta.timer === "required", timerMinutes: Math.max(1, Math.ceil(meta.defaultCount * 1.5)), immediateFeedback: meta.allowsFeedback,
  };
}

export type RequestResult = { ok: true; request: SessionRequest } | { ok: false; error: string };

/** Client-side validation mirrors the server's rules so mistakes are caught early (the server still enforces them). */
export function buildSessionRequest(form: SetupForm): RequestResult {
  const meta = MODE_BY_ID[form.mode];
  if (meta.needsTopic && form.topicIds.length === 0) return { ok: false, error: "Choose at least one topic." };
  if (!Number.isInteger(form.questionCount) || form.questionCount < MIN_QUESTIONS || form.questionCount > MAX_QUESTIONS) {
    return { ok: false, error: `Choose between ${MIN_QUESTIONS} and ${MAX_QUESTIONS} questions.` };
  }
  const timed = meta.timer === "required" || (meta.timer === "optional" && form.useTimer);
  if (timed && (!Number.isInteger(form.timerMinutes) || form.timerMinutes < 1 || form.timerMinutes > MAX_TIMER_MINUTES)) {
    return { ok: false, error: `Set a time limit between 1 and ${MAX_TIMER_MINUTES} minutes.` };
  }
  const request: SessionRequest = { mode: form.mode, question_count: form.questionCount };
  if (meta.canPickScope) {
    if (form.topicIds.length) request.topic_ids = form.topicIds;
    else if (form.unitIds.length) request.unit_ids = form.unitIds;
  }
  if (form.difficulty !== "any") request.difficulty = form.difficulty;
  if (timed) request.timer_minutes = form.timerMinutes;
  if (meta.allowsFeedback) request.immediate_feedback = form.immediateFeedback;
  return { ok: true, request };
}

/** Questions in the chosen scope according to the REAL syllabus counts (an upper bound; mode and difficulty filters narrow it). */
export function availableQuestions(syllabus: Syllabus | null, form: SetupForm): number | null {
  if (!syllabus) return null;
  const meta = MODE_BY_ID[form.mode];
  const fixed = meta.fixedUnits;
  const units = fixed ? syllabus.units.filter((u) => fixed.includes(u.id)) : syllabus.units;
  if (!meta.canPickScope) return units.reduce((n, u) => n + u.question_count, 0);
  const topics = units.flatMap((u) => u.topics);
  if (form.topicIds.length) return topics.filter((t) => form.topicIds.includes(t.id)).reduce((n, t) => n + t.question_count, 0);
  if (form.unitIds.length) return units.filter((u) => form.unitIds.includes(u.id)).reduce((n, u) => n + u.question_count, 0);
  return syllabus.question_total;
}

export function completionPercent(syllabus: Syllabus | null): number {
  if (!syllabus || syllabus.topics_total === 0) return 0;
  return Math.round((100 * syllabus.topics_implemented) / syllabus.topics_total);
}

// --- Session helpers ---------------------------------------------------------------------------------

export type NavState = "current" | "answered" | "marked" | "unanswered";

export function isAnswered(q: SessionQuestion): boolean {
  if (q.interaction === "mcq") return q.selected_index !== null;
  if (q.interaction === "short") return Boolean(q.text_answer?.trim());
  return Boolean(q.sql_answer?.trim());
}

export function navState(q: SessionQuestion, isCurrent: boolean): NavState {
  if (q.marked_for_review) return "marked";
  if (isCurrent) return "current";
  return isAnswered(q) ? "answered" : "unanswered";
}

export function sessionCounts(questions: SessionQuestion[]) {
  const answered = questions.filter(isAnswered).length;
  return { total: questions.length, answered, unanswered: questions.length - answered, marked: questions.filter((q) => q.marked_for_review).length };
}

export function formatCell(value: Cell): string {
  return value === null ? "NULL" : String(value);
}
