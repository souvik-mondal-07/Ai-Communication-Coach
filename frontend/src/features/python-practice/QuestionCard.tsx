import { Check, Lightbulb, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CodeBlock } from "@/features/dsa/CodeBlock";
import { DIFFICULTY_LABELS, FORMAT_LABELS, MAX_SHORT_CHARS } from "@/features/python-practice/pythonPracticeMeta";
import { cn } from "@/lib/utils";
import type { CheckOutcome, SessionQuestion } from "@/types/pythonPractice";

const LETTERS = ["A", "B", "C", "D"];

export function QuestionMeta({ question, index, total }: { question: SessionQuestion; index: number; total: number }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
      <span id="question-heading" className="font-medium text-text-primary">Question {index + 1} of {total}</span>
      <Badge tone="neutral">{DIFFICULTY_LABELS[question.difficulty]}</Badge>
      <Badge tone="neutral">{FORMAT_LABELS[question.format]}</Badge>
      {question.python_version && <Badge tone="violet" title="This question depends on the Python version or implementation.">Python {question.python_version}</Badge>}
      <span>~{question.est_time_seconds}s suggested</span>
    </div>
  );
}

interface HintsProps {
  question: SessionQuestion;
  busy: boolean;
  onRequest: () => void;
}

/** Hints are requested from the server one at a time (and counted); a timed mock sends none, so nothing is shown there. */
export function Hints({ question, busy, onRequest }: HintsProps) {
  if (question.hints_total === 0) return null;
  const remaining = question.hints_total - question.hints_used;
  return (
    <div className="space-y-1.5">
      {question.hints.length > 0 && (
        <ol className="space-y-1 text-sm text-text-secondary" aria-label="Hints">
          {question.hints.map((h, i) => <li key={i} className="flex gap-2"><Lightbulb size={14} className="mt-0.5 shrink-0 text-warn" aria-hidden="true" /><span>{h}</span></li>)}
        </ol>
      )}
      {remaining > 0 && !question.locked && (
        <Button type="button" variant="ghost" size="sm" onClick={onRequest} loading={busy}>
          {question.hints_used === 0 ? "Show a hint" : "Show another hint"} ({question.hints_used}/{question.hints_total})
        </Button>
      )}
    </div>
  );
}

interface Props {
  question: SessionQuestion;
  index: number;
  total: number;
  draft: string;
  busy: boolean;
  checkResult?: CheckOutcome;
  canCheck: boolean;
  disabled?: boolean;
  onSelect: (optionIndex: number) => void;
  onDraft: (text: string) => void;
  onCheck: () => void;
  onHint: () => void;
}

/**
 * A theory, scenario, output-prediction or complexity question. Multiple choice uses a radio group (selection is by position only);
 * short answers (typed output, exception names) use a labelled text box and are graded by the server. With immediate feedback the answer,
 * explanation and colours appear once the answer locks; a timed mock never colours or explains anything.
 */
export function QuestionCard({ question, index, total, draft, busy, canCheck, disabled, onSelect, onDraft, onCheck, onHint }: Props) {
  const fb = question.feedback && question.feedback.kind === "mcq" ? question.feedback : null;
  const sfb = question.feedback && question.feedback.kind === "short" ? question.feedback : null;
  const locked = question.locked || disabled;
  return (
    <section aria-labelledby="question-heading" className="space-y-4">
      <QuestionMeta question={question} index={index} total={total} />
      <p className="whitespace-pre-line text-base leading-relaxed text-text-primary">{question.statement}</p>
      {question.code && <CodeBlock code={question.code} label="Code for this question" />}

      {question.interaction === "mcq" ? (
        <div role="radiogroup" aria-labelledby="question-heading" className="grid gap-2">
          {question.options.map((option, i) => {
            const selected = question.selected_index === i;
            const isCorrect = fb ? fb.correct_index === i : false;
            const isWrongPick = fb ? selected && !fb.is_correct : false;
            return (
              <button key={i} type="button" role="radio" aria-checked={selected} aria-disabled={locked || undefined} disabled={locked && !selected && !fb}
                onClick={() => { if (!locked) onSelect(i); }}
                className={cn(
                  "flex w-full items-start gap-3 rounded-[var(--radius-panel)] border px-3.5 py-3 text-left text-sm transition-colors",
                  selected && !fb && "border-signal bg-signal/10 text-text-primary",
                  !selected && !fb && "border-border bg-surface hover:border-border-input hover:bg-surface-raised",
                  isCorrect && "border-success bg-success/10", isWrongPick && "border-danger bg-danger/10",
                  fb && !isCorrect && !isWrongPick && "border-border bg-surface opacity-80", locked && "cursor-default",
                )}>
                <span className={cn("mt-px flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold", selected ? "border-signal bg-signal text-on-signal" : "border-border-strong text-text-secondary")} aria-hidden="true">{LETTERS[i]}</span>
                <span className="min-w-0 flex-1 break-words text-text-primary">{option}</span>
                {isCorrect && <span className="flex items-center gap-1 text-xs font-medium text-success"><Check size={14} aria-hidden="true" /> Correct answer</span>}
                {isWrongPick && <span className="flex items-center gap-1 text-xs font-medium text-danger"><X size={14} aria-hidden="true" /> Your answer</span>}
              </button>
            );
          })}
        </div>
      ) : (
        <div className="space-y-2">
          <label htmlFor={`short-${question.question_id}`} className="block text-sm font-medium text-text-primary">Your answer</label>
          <p id={`short-help-${question.question_id}`} className="text-xs text-text-muted">{question.short?.help}</p>
          <div className="flex flex-wrap items-center gap-2">
            <input id={`short-${question.question_id}`} type="text" value={draft} maxLength={MAX_SHORT_CHARS} disabled={locked} autoComplete="off" spellCheck={false}
              aria-describedby={`short-help-${question.question_id}`} onChange={(e) => onDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && canCheck && !locked && draft.trim()) { e.preventDefault(); onCheck(); } }}
              className="h-9 w-64 max-w-full rounded-[var(--radius-panel)] border border-border-input bg-surface px-3 font-mono text-sm text-text-primary disabled:opacity-70" />
            {canCheck && !locked && <Button type="button" size="sm" onClick={onCheck} loading={busy} disabled={!draft.trim()}>Check answer</Button>}
          </div>
          {!canCheck && <p className="text-xs text-text-muted">Your answer is saved as you type and graded when you submit.</p>}
        </div>
      )}

      {!question.locked && <Hints key={question.question_id} question={question} busy={busy} onRequest={onHint} />}

      {(fb || sfb) && (
        <div role="status" className="space-y-1 rounded-[var(--radius-panel)] border border-border bg-surface-raised px-4 py-3 text-sm">
          <p className={cn("font-medium", (fb ?? sfb)!.is_correct ? "text-success" : "text-danger")}>{(fb ?? sfb)!.is_correct ? "Correct" : "Not quite"}</p>
          {sfb && <p className="text-text-primary">Correct answer: <span className="font-mono">{sfb.answer}</span></p>}
          <p className="text-text-secondary">{(fb ?? sfb)!.explanation}</p>
        </div>
      )}
    </section>
  );
}
