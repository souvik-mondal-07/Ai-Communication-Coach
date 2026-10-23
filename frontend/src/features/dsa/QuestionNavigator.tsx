import { navState, sessionCounts, isAnswered, type NavState } from "@/features/dsa/dsaMeta";
import { cn } from "@/lib/utils";
import type { SessionQuestion } from "@/types/dsa";

const STYLE: Record<NavState, string> = {
  current: "border-signal bg-signal text-on-signal",
  answered: "border-success/60 bg-success/15 text-text-primary",
  marked: "border-warn bg-warn/20 text-text-primary",
  unanswered: "border-border bg-surface text-text-secondary hover:border-border-input",
};
const WORD: Record<NavState, string> = { current: "current question", answered: "answered", marked: "marked for review", unanswered: "not answered" };

interface Props {
  questions: SessionQuestion[];
  currentIndex: number;
  onGo: (index: number) => void;
}

/** Question map. Colour is never the only signal: each button's accessible name states its status (and the kind of question). */
export function QuestionNavigator({ questions, currentIndex, onGo }: Props) {
  const counts = sessionCounts(questions);
  return (
    <nav aria-label="Question navigator" className="space-y-3">
      <ol className="grid grid-cols-5 gap-1.5 sm:grid-cols-8 lg:grid-cols-5">
        {questions.map((q, i) => {
          const state = navState(q, i === currentIndex);
          return (
            <li key={q.question_id}>
              <button
                type="button"
                onClick={() => onGo(i)}
                aria-current={i === currentIndex ? "step" : undefined}
                aria-label={`Question ${i + 1}${q.interaction === "code" ? " (coding)" : ""}, ${WORD[state]}${q.marked_for_review && isAnswered(q) ? ", answered" : ""}`}
                className={cn("relative flex h-9 w-full items-center justify-center rounded-[var(--radius-panel)] border text-xs font-semibold tabular-nums", STYLE[state])}
              >
                {i + 1}
                {q.interaction === "code" && <span className="absolute bottom-0.5 right-1 font-mono text-[9px]" aria-hidden="true">{"</>"}</span>}
                {q.marked_for_review && isAnswered(q) && <span className="absolute right-0.5 top-0.5 h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />}
              </button>
            </li>
          );
        })}
      </ol>
      <dl className="grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded-[var(--radius-panel)] bg-surface-raised px-2 py-1.5"><dt className="text-text-muted">Answered</dt><dd className="font-semibold tabular-nums text-text-primary">{counts.answered}</dd></div>
        <div className="rounded-[var(--radius-panel)] bg-surface-raised px-2 py-1.5"><dt className="text-text-muted">Left</dt><dd className="font-semibold tabular-nums text-text-primary">{counts.unanswered}</dd></div>
        <div className="rounded-[var(--radius-panel)] bg-surface-raised px-2 py-1.5"><dt className="text-text-muted">Marked</dt><dd className="font-semibold tabular-nums text-text-primary">{counts.marked}</dd></div>
      </dl>
    </nav>
  );
}
