import {
  BookOpenCheck, Boxes, Bug, CircleDashed, Code, FileSearch, Footprints, Gauge, Layers, MessagesSquare, Rocket, ShieldCheck, Target, Timer, type LucideIcon,
} from "lucide-react";
import type { PyDifficulty, PyFormat, PyMode, SessionQuestion, SessionRequest, Syllabus, TopicRow } from "@/types/pythonPractice";

// Timer / format / error helpers are shared with Phase 23 rather than duplicated.
export { accuracyTone, apiErrorCode, formatClock, formatDuration, remainingSeconds } from "@/features/aptitude/aptitudeMeta";

export const MIN_QUESTIONS = 1;
export const MAX_QUESTIONS = 40;
export const MAX_TIMER_MINUTES = 180;
export const MAX_CODE_CHARS = 10000;
export const MAX_SHORT_CHARS = 400;
export type CoverageStatus = TopicRow["status"];

export interface ModeMeta {
  id: PyMode;
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
  { id: "topic", title: "Topic practice", blurb: "Pick one or more syllabus topics and practise their questions: theory, output prediction and coding.", icon: BookOpenCheck, needsTopic: true, canPickScope: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "mixed", title: "Mixed Python MCQs", blurb: "Questions interleaved from several units. Leave the scope empty to draw from everything.", icon: Layers, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "interview", title: "Interview theory", blurb: "Direct concept and scenario questions in the way interviewers ask them.", icon: MessagesSquare, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "predict_output", title: "Predict the output", blurb: "Read a snippet and work out exactly what it prints, including mutation, scope and evaluation-order traps.", icon: FileSearch, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "trace", title: "Trace the code", blurb: "Step through algorithms by hand and state the final values.", icon: Footprints, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 6, allowsFeedback: true },
  { id: "debug", title: "Debug the code", blurb: "Find and fix real bugs. Your fix is graded by running it against hidden tests. Needs the code runner.", icon: Bug, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 5, allowsFeedback: true },
  { id: "complete", title: "Complete the code", blurb: "Fill in the blanks so the function passes its tests. Needs the code runner.", icon: CircleDashed, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 5, allowsFeedback: true },
  { id: "coding", title: "Coding challenges", blurb: "Interview-style problems with examples, hidden tests, hints and a reference solution after you try. Needs the code runner.", icon: Code, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 3, allowsFeedback: true },
  { id: "complexity", title: "Complexity analysis", blurb: "Time and space complexity of loops, recursion and data-structure operations.", icon: Gauge, needsTopic: false, canPickScope: true, timer: "optional", defaultCount: 6, allowsFeedback: true },
  { id: "oop", title: "OOP interview", blurb: "Classes, inheritance, MRO, dunder methods, properties and dataclasses.", icon: Boxes, needsTopic: false, canPickScope: false, timer: "optional", defaultCount: 10, allowsFeedback: true, fixedUnits: ["unit-d"] },
  { id: "advanced", title: "Advanced Python", blurb: "Generators, decorators, itertools, asyncio, concurrency, the GIL and memory.", icon: Rocket, needsTopic: false, canPickScope: false, timer: "optional", defaultCount: 10, allowsFeedback: true, fixedUnits: ["unit-f"] },
  { id: "security", title: "Cybersecurity automation", blurb: "Defensive, offline Python: log parsing, hashing, validation, safe subprocess and secret handling.", icon: ShieldCheck, needsTopic: false, canPickScope: false, timer: "optional", defaultCount: 10, allowsFeedback: true, fixedUnits: ["unit-h"] },
  { id: "timed_mock", title: "Timed mock interview", blurb: "Exam conditions across the syllabus: countdown, navigator, mark for review. You can run examples, but nothing is checked or revealed until you submit.", icon: Timer, needsTopic: false, canPickScope: true, timer: "required", defaultCount: 10, allowsFeedback: false },
  { id: "weak", title: "Weak-topic revision", blurb: "Re-attempt what you got wrong and practise topics where your recorded accuracy is low. Needs practice history first.", icon: Target, needsTopic: false, canPickScope: false, timer: "optional", defaultCount: 10, allowsFeedback: true },
];

export const MODE_BY_ID = Object.fromEntries(MODES.map((m) => [m.id, m])) as Record<PyMode, ModeMeta>;
export const MODE_LABELS = Object.fromEntries(MODES.map((m) => [m.id, m.title])) as Record<PyMode, string>;
export const CODE_MODES: PyMode[] = ["coding", "debug", "complete"];
export const DIFFICULTY_LABELS: Record<PyDifficulty, string> = { easy: "Easy", medium: "Medium", hard: "Hard" };
export const COVERAGE_LABELS: Record<CoverageStatus, string> = { implemented: "Ready", partial: "Few questions", missing: "No questions yet" };
export const FORMAT_LABELS: Record<PyFormat, string> = {
  concept: "Concept", scenario: "Scenario", output: "Predict the output", trace: "Trace", debug: "Debug", complete: "Complete", coding: "Coding", complexity: "Complexity",
};

export interface SetupForm {
  mode: PyMode;
  unitIds: string[];
  topicIds: string[];
  difficulty: PyDifficulty | "any";
  questionCount: number;
  useTimer: boolean;
  timerMinutes: number;
  immediateFeedback: boolean;
}

export function defaultForm(mode: PyMode = "topic"): SetupForm {
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
  return Boolean(q.code_answer?.trim());
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
