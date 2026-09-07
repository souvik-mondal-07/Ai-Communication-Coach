import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { PublicQuestion } from "@/features/cybersecurity/cybersecurityTypes";

interface QuestionCardProps {
  question: PublicQuestion;
  onSubmit: (answer: string) => Promise<void>;
  isSubmitting: boolean;
}

export function QuestionCard({ question, onSubmit, isSubmitting }: QuestionCardProps) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [shortAnswer, setShortAnswer] = useState("");

  const answer = question.type === "multiple_choice" ? selectedOption : shortAnswer;
  const canSubmit = !!answer && answer.trim().length > 0 && !isSubmitting;

  async function handleSubmit() {
    if (!canSubmit || !answer) return;
    await onSubmit(answer);
  }

  return (
    <div className="space-y-4">
      <p className="text-base font-medium leading-relaxed text-text-primary">
        {question.question}
      </p>

      {question.type === "multiple_choice" && question.options ? (
        <div className="space-y-2" role="radiogroup" aria-label="Answer options">
          {question.options.map((option, idx) => {
            const letter = String.fromCharCode(65 + idx);
            const isSelected = selectedOption === option;
            return (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={isSelected}
                disabled={isSubmitting}
                onClick={() => setSelectedOption(option)}
                className={`flex w-full items-center gap-3 rounded-[var(--radius-panel)] border px-3.5 py-2.5 text-left text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                  isSelected
                    ? "border-signal bg-signal/10 text-text-primary"
                    : "border-border bg-surface-raised text-text-secondary hover:border-border-strong"
                }`}
              >
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-medium ${
                    isSelected
                      ? "border-signal bg-signal text-[#08120f]"
                      : "border-border-strong text-text-muted"
                  }`}
                >
                  {letter}
                </span>
                {option}
              </button>
            );
          })}
        </div>
      ) : (
        <textarea
          value={shortAnswer}
          onChange={(e) => setShortAnswer(e.target.value)}
          disabled={isSubmitting}
          rows={4}
          placeholder="Write your answer here..."
          aria-label="Your answer"
          className="w-full resize-none rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3.5 py-2.5 text-sm text-text-primary placeholder:text-text-muted disabled:cursor-not-allowed disabled:opacity-60"
        />
      )}

      <div className="flex justify-end">
        <Button onClick={() => void handleSubmit()} disabled={!canSubmit}>
          {isSubmitting ? "Submitting…" : "Submit"}
        </Button>
      </div>
    </div>
  );
}
