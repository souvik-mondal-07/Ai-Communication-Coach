import { useState } from "react";
import { Check, Lightbulb, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { CODING_TYPE_LABELS, DIFFICULTY_LABELS, FORMAT_LABELS } from "@/features/dsa/dsaMeta";
import { CodeBlock } from "@/features/dsa/CodeBlock";
import { ComplexityPanel } from "@/features/dsa/ComplexityPanel";
import { TraceViewer } from "@/features/dsa/TraceViewer";
import { cn } from "@/lib/utils";
import type { SessionQuestion } from "@/types/dsa";

const LETTERS = ["A", "B", "C", "D"];

export function QuestionMeta({ question, index, total }: { question: SessionQuestion; index: number; total: number }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
      <span id="question-heading" className="font-medium text-text-primary">Question {index + 1} of {total}</span>
      <Badge tone="neutral">{DIFFICULTY_LABELS[question.difficulty]}</Badge>
      <Badge tone="neutral">{question.coding_type ? CODING_TYPE_LABELS[question.coding_type] : FORMAT_LABELS[question.format]}</Badge>
      <span>~{question.est_time_seconds}s suggested</span>
    </div>
  );
}

/** Progressive hints. Hidden entirely in timed mocks (the server sends none). */
export function Hints({ hints }: { hints: string[] }) {
  const [shown, setShown] = useState(0);
  if (hints.length === 0) return null;
  return (
    <div className="space-y-1.5">
      {shown > 0 && (
        <ol className="space-y-1 text-sm text-text-secondary" aria-label="Hints">
          {hints.slice(0, shown).map((h, i) => <li key={i} className="flex gap-2"><Lightbulb size={14} className="mt-0.5 shrink-0 text-warn" aria-hidden="true" /><span>{h}</span></li>)}
        </ol>
      )}
      {shown < hints.length && (
        <button type="button" onClick={() => setShown((n) => n + 1)} className="text-xs font-medium text-link underline-offset-2 hover:underline">
          {shown === 0 ? "Show a hint" : "Show another hint"} ({shown}/{hints.length})
        </button>
      )}
    </div>
  );
}

interface Props {
  question: SessionQuestion;
  index: number;
  total: number;
  onSelect: (optionIndex: number) => void;
  disabled?: boolean;
}

/**
 * A multiple-choice question: statement, optional code snippet, four options as a radio group. Selection is by position
 * only. With immediate feedback the option colours, explanation, complexity and trace appear after the answer locks;
 * in a timed mock nothing is ever coloured or explained.
 */
export function QuestionCard({ question, index, total, onSelect, disabled }: Props) {
  const fb = question.feedback && question.feedback.kind === "mcq" ? question.feedback : null;
  const locked = question.locked || disabled;
  return (
    <section aria-labelledby="question-heading" className="space-y-4">
      <QuestionMeta question={question} index={index} total={total} />
      <p className="whitespace-pre-line text-base leading-relaxed text-text-primary">{question.statement}</p>
      {question.code && <CodeBlock code={question.code} label="Code for this question" />}
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
              <span className={cn("mt-px flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold", selected ? "border-signal bg-signal text-on-signal" : "border-border-strong text-text-secondary")} aria-hidden="true">{LETTERS[i]}</span>
              <span className="min-w-0 flex-1 break-words text-text-primary">{option}</span>
              {isCorrect && <span className="flex items-center gap-1 text-xs font-medium text-success"><Check size={14} aria-hidden="true" /> Correct answer</span>}
              {isWrongPick && <span className="flex items-center gap-1 text-xs font-medium text-danger"><X size={14} aria-hidden="true" /> Your answer</span>}
            </button>
          );
        })}
      </div>
      {!fb && <Hints key={question.question_id} hints={question.hints} />}
      {fb && (
        <div className="space-y-3">
          <div role="status" className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-4 py-3 text-sm">
            <p className={cn("font-medium", fb.is_correct ? "text-success" : "text-danger")}>{fb.is_correct ? "Correct" : "Not quite"}</p>
            <p className="mt-1 text-text-secondary">{fb.explanation}</p>
          </div>
          {fb.trace && <TraceViewer steps={fb.trace} />}
          <ComplexityPanel complexity={fb.complexity} />
        </div>
      )}
    </section>
  );
}
