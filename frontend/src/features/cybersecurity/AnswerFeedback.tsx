import { Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AnswerResult } from "@/features/cybersecurity/cybersecurityTypes";

interface AnswerFeedbackProps {
  result: AnswerResult;
  isLastQuestion: boolean;
  onNext: () => void;
}

export function AnswerFeedback({ result, isLastQuestion, onNext }: AnswerFeedbackProps) {
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
        <p className="text-sm font-semibold text-text-primary">Score: {result.score}/100</p>
      </div>

      <p className="text-sm leading-relaxed text-text-secondary">{result.feedback}</p>

      {result.missing_points.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-medium text-text-muted">You missed:</p>
          <ul className="space-y-1">
            {result.missing_points.map((point) => (
              <li key={point} className="flex items-start gap-1.5 text-sm text-text-secondary">
                <span className="mt-0.5 text-warn">•</span>
                {point}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.ideal_answer && (
        <div>
          <p className="mb-1 text-xs font-medium text-text-muted">Ideal explanation:</p>
          <p className="text-sm leading-relaxed text-text-secondary">{result.ideal_answer}</p>
        </div>
      )}

      <div className="flex justify-end">
        <Button onClick={onNext}>{isLastQuestion ? "Finish" : "Next Question"}</Button>
      </div>
    </div>
  );
}
