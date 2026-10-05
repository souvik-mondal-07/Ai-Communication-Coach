import { useState } from "react";
import { Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PracticeQuestionState } from "@/features/cybersecurity/cybersecurityTypes";
import { nextHintStep } from "@/features/cybersecurity/practice/practiceUtils";

interface PracticeHintsProps {
  question: PracticeQuestionState;
  maxHints: number;
  isBusy: boolean;
  onHint: () => void;
  onReveal: () => void;
}

/** Progressive help: Hint 1 → Hint 2 → Hint 3 → explanation. Never shows the answer up front. */
export function PracticeHints({ question, maxHints, isBusy, onHint, onReveal }: PracticeHintsProps) {
  const [confirming, setConfirming] = useState(false);
  const step = nextHintStep(question, maxHints);
  if (step === "none" && question.hints.length === 0) return null;

  return (
    <div className="space-y-3 border-t border-border pt-4">
      {question.hints.map((hint, i) => (
        <div key={i} className="rounded-[var(--radius-panel)] border border-border bg-surface-raised p-3">
          <p className="mb-1 text-xs font-medium text-signal">Hint {i + 1}</p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">{hint}</p>
        </div>
      ))}

      {step === "hint" && (
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="secondary" size="sm" disabled={isBusy} onClick={onHint} className="gap-1.5">
            <Lightbulb size={13} />
            {question.hints_used === 0 ? "Need a hint?" : "Need another?"}
          </Button>
          {question.hints_used > 0 && (
            <button
              type="button"
              disabled={isBusy}
              onClick={() => setConfirming(true)}
              className="text-xs text-link hover:underline disabled:opacity-50"
            >
              Show final explanation
            </button>
          )}
          <span className="text-[11px] text-text-muted">Each hint lowers the maximum score slightly.</span>
        </div>
      )}

      {step === "explanation" && (
        <Button variant="secondary" size="sm" disabled={isBusy} onClick={() => setConfirming(true)}>
          Show final explanation
        </Button>
      )}

      {confirming && (
        <div className="rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 p-3 text-sm text-text-secondary">
          <p>Showing the explanation ends this question, and it will count as 0. Continue?</p>
          <div className="mt-2 flex gap-2">
            <Button
              size="sm"
              disabled={isBusy}
              onClick={() => {
                setConfirming(false);
                onReveal();
              }}
            >
              Show explanation
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
              Keep trying
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
