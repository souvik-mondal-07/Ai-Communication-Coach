import { BookOpenCheck, Briefcase, Layers, Target, Timer, type LucideIcon } from "lucide-react";
import axios from "axios";
import type { AptitudeDifficulty, AptitudeMode, CoverageStatus, SessionQuestion, SessionRequest, Syllabus } from "@/types/aptitude";

export const MIN_QUESTIONS = 1;
export const MAX_QUESTIONS = 60;
export const MAX_TIMER_MINUTES = 180;

export interface ModeMeta {
  id: AptitudeMode;
  title: string;
  blurb: string;
  icon: LucideIcon;
  /** Needs the user to choose at least one topic or subtopic. */
  needsTopic: boolean;
  /** Offers topic selection at all. */
  canPickTopics: boolean;
  timer: "none" | "optional" | "required";
  defaultCount: number;
  /** Whether answers can be shown immediately after each question. */
  allowsFeedback: boolean;
}

export const MODES: ModeMeta[] = [
  { id: "topic", title: "Topic practice", blurb: "Drill one topic or subtopic. Optional timer; see the explanation after each answer or at the end.", icon: BookOpenCheck, needsTopic: true, canPickTopics: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "scenario", title: "Scenario practice", blurb: "Placement-style situations and multi-step problems that mix quantitative and logical reasoning. All settings are fictional.", icon: Briefcase, needsTopic: false, canPickTopics: true, timer: "optional", defaultCount: 10, allowsFeedback: true },
  { id: "timed_mock", title: "Timed mock test", blurb: "Exam conditions: countdown, shuffled questions, mark for review, auto-submit. No answers until you submit.", icon: Timer, needsTopic: false, canPickTopics: true, timer: "required", defaultCount: 20, allowsFeedback: false },
  { id: "mixed", title: "Mixed practice", blurb: "Questions spread across every topic you choose (or all of them), with your own difficulty, length and timing.", icon: Layers, needsTopic: false, canPickTopics: true, timer: "optional", defaultCount: 15, allowsFeedback: true },
  { id: "weak", title: "Weak topic practice", blurb: "Re-attempt what you got wrong and practise topics with low accuracy. Needs some practice history first.", icon: Target, needsTopic: false, canPickTopics: false, timer: "optional", defaultCount: 10, allowsFeedback: true },
];

export const MODE_BY_ID = Object.fromEntries(MODES.map((m) => [m.id, m])) as Record<AptitudeMode, ModeMeta>;
export const DIFFICULTY_LABELS: Record<AptitudeDifficulty, string> = { easy: "Easy", medium: "Medium", hard: "Hard" };
export const COVERAGE_LABELS: Record<CoverageStatus, string> = { implemented: "Ready", partial: "Few questions", missing: "No questions yet" };
export const MODE_LABELS: Record<AptitudeMode, string> = Object.fromEntries(MODES.map((m) => [m.id, m.title])) as Record<AptitudeMode, string>;

export interface SetupForm {
  mode: AptitudeMode;
  topicIds: string[];
  subtopicIds: string[];
  difficulty: AptitudeDifficulty | "any";
  questionCount: number;
  useTimer: boolean;
  timerMinutes: number;
  immediateFeedback: boolean;
}

export function defaultForm(mode: AptitudeMode = "topic"): SetupForm {
  const meta = MODE_BY_ID[mode];
  return {
    mode, topicIds: [], subtopicIds: [], difficulty: "any", questionCount: meta.defaultCount,
    useTimer: meta.timer === "required", timerMinutes: Math.max(1, Math.ceil(meta.defaultCount * 1.5)), immediateFeedback: meta.allowsFeedback && mode !== "mixed",
  };
}

export type RequestResult = { ok: true; request: SessionRequest } | { ok: false; error: string };

/** Client-side validation mirrors the server's rules so mistakes are caught before a round trip (the server still enforces them). */
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

/** How many active questions match the chosen filters, from the real syllabus counts. */
export function availableQuestions(syllabus: Syllabus | null, form: SetupForm): number | null {
  if (!syllabus) return null;
  let total = 0;
  for (const t of syllabus.topics) {
    for (const s of t.subtopics) {
      const inScope = form.subtopicIds.length ? form.subtopicIds.includes(s.id) : form.topicIds.length ? form.topicIds.includes(t.id) : true;
      if (!inScope) continue;
      total += form.difficulty === "any" ? s.question_count : s.by_difficulty[form.difficulty];
    }
  }
  return total;
}

export function completionPercent(syllabus: Syllabus | null): number {
  if (!syllabus || syllabus.totals.subtopics === 0) return 0;
  return Math.round((100 * syllabus.totals.subtopics_implemented) / syllabus.totals.subtopics);
}

/** mm:ss, or h:mm:ss from one hour up. */
export function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = String(m).padStart(h > 0 ? 2 : 1, "0");
  return `${h > 0 ? `${h}:` : ""}${mm}:${String(sec).padStart(2, "0")}`;
}

export function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds));
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  const rest = s % 60;
  return rest ? `${m} min ${rest} s` : `${m} min`;
}

/** Seconds left, from the server's expiry and the offset between the server's and this device's clocks. Null = untimed. */
export function remainingSeconds(expiresAt: string | null, nowMs: number, clockOffsetMs: number): number | null {
  if (!expiresAt) return null;
  return Math.max(0, Math.ceil((Date.parse(expiresAt) - (nowMs + clockOffsetMs)) / 1000));
}

export function accuracyTone(accuracy: number): "success" | "warn" | "danger" {
  if (accuracy >= 70) return "success";
  if (accuracy >= 40) return "warn";
  return "danger";
}

export type NavState = "current" | "answered" | "marked" | "unanswered";

export function navState(q: SessionQuestion, isCurrent: boolean): NavState {
  if (q.marked_for_review) return "marked";
  if (isCurrent) return "current";
  return q.selected_index !== null ? "answered" : "unanswered";
}

export function sessionCounts(questions: SessionQuestion[]) {
  const answered = questions.filter((q) => q.selected_index !== null).length;
  return { total: questions.length, answered, unanswered: questions.length - answered, marked: questions.filter((q) => q.marked_for_review).length };
}

/** The server's machine-readable error code, if this is an API error. */
export function apiErrorCode(error: unknown): string | null {
  if (axios.isAxiosError(error)) {
    const code = (error.response?.data as { error_code?: unknown } | undefined)?.error_code;
    return typeof code === "string" ? code : null;
  }
  return null;
}
