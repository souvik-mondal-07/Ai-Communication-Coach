import type {
  PracticeCompleteResult,
  PracticeQuestionState,
  PracticeSessionState,
} from "@/features/cybersecurity/cybersecurityTypes";

/** 125 -> "02:05" */
export function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/** Text progress bar, e.g. progressBar(2, 5) -> "████░░░░░░ 2/5" (10 cells). */
export function progressBar(done: number, total: number, cells = 10): string {
  const safeTotal = Math.max(1, total);
  const filled = Math.round((Math.min(Math.max(done, 0), safeTotal) / safeTotal) * cells);
  return `${"█".repeat(filled)}${"░".repeat(cells - filled)} ${done}/${total}`;
}

/** The question to show on load/resume: the first unanswered one, else the last. */
export function firstOpenIndex(questions: PracticeQuestionState[]): number {
  const open = questions.findIndex((q) => !q.answered);
  return open === -1 ? Math.max(0, questions.length - 1) : open;
}

/** Answered questions, counting toward the progress bar. */
export function answeredCount(session: Pick<PracticeSessionState, "questions">): number {
  return session.questions.filter((q) => q.answered).length;
}

/** Hint ladder state for the UI: which control to offer next. */
export function nextHintStep(
  q: Pick<PracticeQuestionState, "hints_used" | "hints_available" | "answered">,
  maxHints: number
): "hint" | "explanation" | "none" {
  if (q.answered || q.hints_available === 0) return "none";
  return q.hints_used < maxHints ? "hint" : "explanation";
}

export const MAX_ANSWER_LENGTH = 5000;

export function recommendationRoute(next: NonNullable<PracticeCompleteResult["recommended_next"]>): string {
  if (!next.topic_slug) return "/practice";
  const query = next.difficulty ? `?difficulty=${next.difficulty}` : "";
  return `/cybersecurity/${next.topic_slug}${query}`;
}
