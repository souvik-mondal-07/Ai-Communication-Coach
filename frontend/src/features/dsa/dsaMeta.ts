import { BookOpenCheck, Code2, Gauge, ListTree, MessagesSquare, Target, Timer, type LucideIcon } from "lucide-react";
import type { CoverageStatus, DsaDifficulty, DsaResult, DsaFormat, DsaMode, SessionQuestion, SessionRequest, Syllabus } from "@/types/dsa";

// Timer/format/error helpers are shared with Phase 23 rather than duplicated.
export { accuracyTone, apiErrorCode, formatClock, formatDuration, remainingSeconds } from "@/features/aptitude/aptitudeMeta";

export const MIN_QUESTIONS = 1;
export const MAX_QUESTIONS = 50;
export const MAX_TIMER_MINUTES = 180;
export const MAX_CODE_CHARS = 8000;

/** Which formats each mode draws from. Mirrors the server's MODE_FORMATS; the server is the authority. */
export const MODE_FORMATS: Partial<Record<DsaMode, DsaFormat[]>> = {
  interview: ["conceptual", "scenario", "complexity"],
  tracing: ["trace", "output"],
  complexity: ["complexity"],
  coding: ["coding"],
};

export interface ModeMeta {
  id: DsaMode;
  title: string;
  blurb: string;
  icon: LucideIcon;
  needsTopic: boolean;
  canPickTopics: boolean;
  timer: "none" | "optional" | "required";
  defaultCount: number;
  allowsFeedback: boolean;
}

export const MODES: ModeMeta[] = [
  { id: "topic", title: "Topic practice", blurb: "Pick a topic or subtopic and work through multiple-choice questions in sequence. See each explanation straight away or at the end.", icon: BookOpenCheck, needsTopic: true, canPickTopics: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "interview", title: "Technical interview", blurb: "Direct and scenario-based questions: choose the right data structure or algorithm and justify the trade-offs.", icon: MessagesSquare, needsTopic: false, canPickTopics: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "tracing", title: "Code tracing", blurb: "Predict outputs and trace sorts, searches, recursion, trees, stacks, queues and graphs. Step through the intermediate states afterwards.", icon: ListTree, needsTopic: false, canPickTopics: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "complexity", title: "Complexity challenge", blurb: "Work out time and space complexity, best/average/worst cases, and compare alternative implementations.", icon: Gauge, needsTopic: false, canPickTopics: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "coding", title: "Coding practice", blurb: "Write functions from templates, complete a missing line or fix a bug. Code is not run for you: you compare against the reference and test cases.", icon: Code2, needsTopic: false, canPickTopics: true, timer: "optional", defaultCount: 6, allowsFeedback: true },
  { id: "timed_mock", title: "Timed mock test", blurb: "Exam conditions across the syllabus: countdown, question navigator, mark for review. No answers until you submit.", icon: Timer, needsTopic: false, canPickTopics: true, timer: "required", defaultCount: 20, allowsFeedback: false },
  { id: "weak", title: "Weak topic revision", blurb: "Re-attempt what you got wrong and practise topics where your saved accuracy is low. Needs practice history first.", icon: Target, needsTopic: false, canPickTopics: false, timer: "optional", defaultCount: 10, allowsFeedback: true },
];

export const MODE_BY_ID = Object.fromEntries(MODES.map((m) => [m.id, m])) as Record<DsaMode, ModeMeta>;
export const MODE_LABELS = Object.fromEntries(MODES.map((m) => [m.id, m.title])) as Record<DsaMode, string>;
export const DIFFICULTY_LABELS: Record<DsaDifficulty, string> = { easy: "Easy", medium: "Medium", hard: "Hard" };
export const COVERAGE_LABELS: Record<CoverageStatus, string> = { implemented: "Ready", partial: "Few questions", missing: "No questions yet" };
export const FORMAT_LABELS: Record<DsaFormat, string> = {
  conceptual: "Concept", scenario: "Scenario", output: "Output prediction", trace: "Trace", complexity: "Complexity", coding: "Coding",
};
export const CODING_TYPE_LABELS = { fill_line: "Fill the line", fix_bug: "Fix the bug", write_function: "Write the function" } as const;

export interface SetupForm {
  mode: DsaMode;
  topicIds: string[];
  subtopicIds: string[];
  difficulty: DsaDifficulty | "any";
  questionCount: number;
  useTimer: boolean;
  timerMinutes: number;
  immediateFeedback: boolean;
}

export function defaultForm(mode: DsaMode = "topic"): SetupForm {
  const meta = MODE_BY_ID[mode];
  return {
    mode, topicIds: [], subtopicIds: [], difficulty: "any", questionCount: meta.defaultCount,
    useTimer: meta.timer === "required", timerMinutes: Math.max(1, Math.ceil(meta.defaultCount * 1.5)), immediateFeedback: meta.allowsFeedback,
  };
}

export type RequestResult = { ok: true; request: SessionRequest } | { ok: false; error: string };

/** Client-side validation mirrors the server's rules so mistakes are caught early (the server still enforces them). */
export function buildSessionRequest(form: SetupForm): RequestResult {
  const meta = MODE_BY_ID[form.mode];
  if (meta.needsTopic && form.topicIds.length === 0 && form.subtopicIds.length === 0) return { ok: false, error: "Choose at least one topic or subtopic." };
  if (!Number.isInteger(form.questionCount) || form.questionCount < MIN_QUESTIONS || form.questionCount > MAX_QUESTIONS) {
    return { ok: false, error: `Choose between ${MIN_QUESTIONS} and ${MAX_QUESTIONS} questions.` };
  }
  const timed = meta.timer === "required" || (meta.timer === "optional" && form.useTimer);
  if (timed && (!Number.isInteger(form.timerMinutes) || form.timerMinutes < 1 || form.timerMinutes > MAX_TIMER_MINUTES)) {
    return { ok: false, error: `Set a time limit between 1 and ${MAX_TIMER_MINUTES} minutes.` };
  }
  const request: SessionRequest = {
    mode: form.mode,
    topic_ids: meta.canPickTopics ? form.topicIds : [],
    subtopic_ids: meta.canPickTopics ? form.subtopicIds : [],
    question_count: form.questionCount,
  };
  if (form.difficulty !== "any") request.difficulty = form.difficulty;
  if (timed) request.timer_minutes = form.timerMinutes;
  if (meta.allowsFeedback) request.immediate_feedback = form.immediateFeedback;
  return { ok: true, request };
}

/**
 * How many questions this mode can draw from for the chosen scope, from the real per-format counts.
 * Difficulty narrows the real number further, but the syllabus does not break counts down by format AND difficulty, so
 * it is not applied here; callers say so.
 */
export function availableQuestions(syllabus: Syllabus | null, form: SetupForm): number | null {
  if (!syllabus) return null;
  const formats = MODE_FORMATS[form.mode];
  let total = 0;
  for (const t of syllabus.topics) {
    for (const s of t.subtopics) {
      const inScope = form.subtopicIds.length ? form.subtopicIds.includes(s.id) : form.topicIds.length ? form.topicIds.includes(t.id) : true;
      if (!inScope) continue;
      total += formats ? formats.reduce((n, f) => n + (s.by_format[f] ?? 0), 0) : s.auto_graded;
    }
  }
  return total;
}

export function completionPercent(syllabus: Syllabus | null): number {
  if (!syllabus || syllabus.totals.subtopics === 0) return 0;
  return Math.round((100 * syllabus.totals.subtopics_implemented) / syllabus.totals.subtopics);
}

export type NavState = "current" | "answered" | "marked" | "unanswered";

export const isAnswered = (q: Pick<SessionQuestion, "selected_index" | "code_answer">) => q.selected_index !== null || Boolean(q.code_answer?.trim());

export function navState(q: SessionQuestion, isCurrent: boolean): NavState {
  if (q.marked_for_review) return "marked";
  if (isCurrent) return "current";
  return isAnswered(q) ? "answered" : "unanswered";
}

export function sessionCounts(questions: SessionQuestion[]) {
  const answered = questions.filter(isAnswered).length;
  return { total: questions.length, answered, unanswered: questions.length - answered, marked: questions.filter((q) => q.marked_for_review).length };
}

/** Questions in a result that received an answer: a selected option, or submitted code. */
export function answeredCount(result: DsaResult): number {
  return result.questions.filter((q) => (q.interaction === "mcq" ? q.selected_index !== null : Boolean(q.code_answer?.trim()))).length;
}

/** Compact display of a test argument list, e.g. `[1, 2], 3`. */
export function formatArgs(args: unknown[]): string {
  return args.map((a) => JSON.stringify(a)).join(", ");
}
export function formatValue(value: unknown): string {
  return JSON.stringify(value);
}
