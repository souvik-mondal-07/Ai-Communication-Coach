import { Check, X } from "lucide-react";
import { DIFFICULTY_LABELS } from "@/features/aptitude/aptitudeMeta";
import { DataView } from "@/features/aptitude/DataView";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SessionQuestion } from "@/types/aptitude";

const LETTERS = ["A", "B", "C", "D"];

interface Props {
  question: SessionQuestion;
  index: number;
  total: number;
  onSelect: (optionIndex: number) => void;
  disabled?: boolean;
}

/**
 * One question with four options as a radio group. Selection is by position only. In immediate-feedback
 * practice the option colours appear after the answer locks; in exam mode nothing is ever coloured.
 */
export function QuestionCard({ question, index, total, onSelect, disabled }: Props) {
  const fb = question.feedback;
  const locked = question.locked || disabled;
  return (
    <section aria-labelledby="question-heading" className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
        <span id="question-heading" className="font-medium text-text-primary">Question {index + 1} of {total}</span>
        <Badge tone="neutral">{DIFFICULTY_LABELS[question.difficulty]}</Badge>
        <span>~{question.est_time_seconds}s suggested</span>
      </div>
      <p className="whitespace-pre-line text-base leading-relaxed text-text-primary">{question.statement}</p>
      {question.data && <DataView data={question.data} />}
      <div role="radiogroup" aria-labelledby="question-heading" className="grid gap-2">
        {question.options.map((option, i) => {
          const selected = question.selected_index === i;
          const isCorrect = fb ? fb.correct_index === i : false;
          const isWrongPick = fb ? selected && !fb.is_correct : false;
          return (
            <button
              key={i}
              type="button"
              role="radio"
              aria-checked={selected}
              aria-disabled={locked || undefined}
              disabled={locked && !selected && !fb}
              onClick={() => { if (!locked) onSelect(i); }}
              className={cn(
                "flex w-full items-start gap-3 rounded-[var(--radius-panel)] border px-3.5 py-3 text-left text-sm transition-colors",
                selected && !fb && "border-signal bg-signal/10 text-text-primary",
                !selected && !fb && "border-border bg-surface hover:border-border-input hover:bg-surface-raised",
                isCorrect && "border-success bg-success/10",
                isWrongPick && "border-danger bg-danger/10",
                fb && !isCorrect && !isWrongPick && "border-border bg-surface opacity-80",
                locked && "cursor-default",
              )}
            >
              <span className={cn("mt-px flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold", selected ? "border-signal bg-signal text-on-signal" : "border-border-strong text-text-secondary")} aria-hidden="true">
                {LETTERS[i]}
              </span>
              <span className="min-w-0 flex-1 text-text-primary">{option}</span>
              {isCorrect && <span className="flex items-center gap-1 text-xs font-medium text-success"><Check size={14} aria-hidden="true" /> Correct answer</span>}
              {isWrongPick && <span className="flex items-center gap-1 text-xs font-medium text-danger"><X size={14} aria-hidden="true" /> Your answer</span>}
            </button>
          );
        })}
      </div>
      {fb && (
        <div role="status" className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-4 py-3 text-sm">
          <p className={cn("font-medium", fb.is_correct ? "text-success" : "text-danger")}>{fb.is_correct ? "Correct" : "Not quite"}</p>
          <p className="mt-1 text-text-secondary">{fb.explanation}</p>
          {fb.formula && <p className="mt-2 text-xs text-text-muted"><span className="font-medium text-text-secondary">Formula / shortcut:</span> {fb.formula}</p>}
        </div>
      )}
    </section>
  );
}
