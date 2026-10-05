import { Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AnswerResult } from "@/features/cybersecurity/cybersecurityTypes";

interface AnswerFeedbackProps {
  result: AnswerResult;
  isLastQuestion: boolean;
  onNext: () => void;
  isBusy?: boolean;
}

const DIMENSIONS: { key: "technical" | "completeness" | "reasoning" | "practicality"; label: string }[] = [
  { key: "technical", label: "Technical accuracy" },
  { key: "completeness", label: "Completeness" },
  { key: "reasoning", label: "Reasoning" },
  { key: "practicality", label: "Practicality" },
];

function List({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-text-muted">{title}</p>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-1.5 text-sm text-text-secondary">
            <span className={`mt-0.5 ${tone}`}>•</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AnswerFeedback({ result, isLastQuestion, onNext, isBusy = false }: AnswerFeedbackProps) {
  const hintsUsed = result.hints_used ?? 0;
  const penalty = result.hint_penalty ?? 0;
  const strengths = result.strengths ?? [];

  return (
    <div className="space-y-4 rounded-[var(--radius-panel)] border border-border bg-surface-raised p-4">
      <div className="flex items-center gap-2">
        <span
          className={`flex h-8 w-8 items-center justify-center rounded-[var(--radius-panel)] ${
            result.correct ? "bg-signal/15 text-signal" : "bg-danger/15 text-danger"
          }`}
        >
          {result.correct ? <Check size={16} /> : <X size={16} />}
        </span>
        <div>
          <p className="text-sm font-semibold text-text-primary">Your Score: {result.score}/100</p>
          {hintsUsed > 0 && !result.revealed && (
            <p className="text-xs text-text-muted">
              {hintsUsed} {hintsUsed === 1 ? "hint" : "hints"} used
              {penalty > 0 ? ` (−${penalty} points from ${result.raw_score}/100)` : ""}
            </p>
          )}
        </div>
      </div>

      {result.dimension_scores && (
        <div className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
          {DIMENSIONS.map(({ key, label }) => (
            <div key={key}>
              <div className="flex justify-between text-[11px] text-text-muted">
                <span>{label}</span>
                <span>{result.dimension_scores![key]}</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-border">
                <div
                  className="h-full rounded-full bg-signal"
                  style={{ width: `${result.dimension_scores![key]}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-sm leading-relaxed text-text-secondary">{result.feedback}</p>

      <List title="What you did well:" items={strengths} tone="text-signal" />
      <List title="What you missed:" items={result.missing_points} tone="text-warn" />

      {result.improvement && (
        <div>
          <p className="mb-1 text-xs font-medium text-text-muted">Recommended improvement:</p>
          <p className="text-sm leading-relaxed text-text-secondary">{result.improvement}</p>
        </div>
      )}

      {result.ideal_steps && result.ideal_steps.length > 0 ? (
        <div>
          <p className="mb-1.5 text-xs font-medium text-text-muted">Recommended approach:</p>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-text-secondary">
            {result.ideal_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
      ) : (
        result.ideal_answer && (
          <div>
            <p className="mb-1 text-xs font-medium text-text-muted">Ideal explanation:</p>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">{result.ideal_answer}</p>
          </div>
        )
      )}

      {result.explanation && (
        <div>
          <p className="mb-1 text-xs font-medium text-text-muted">Explanation:</p>
          <p className="text-sm leading-relaxed text-text-secondary">{result.explanation}</p>
        </div>
      )}

      <div className="flex justify-end">
        <Button onClick={onNext} disabled={isBusy}>
          {isBusy ? "Loading…" : isLastQuestion ? "Finish" : "Next Question"}
        </Button>
      </div>
    </div>
  );
}
