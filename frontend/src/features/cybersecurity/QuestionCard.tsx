import { Button } from "@/components/ui/button";
import type { QuestionType } from "@/features/cybersecurity/cybersecurityTypes";
import { MAX_ANSWER_LENGTH } from "@/features/cybersecurity/practice/practiceUtils";

interface QuestionCardProps {
  question: { question: string; type: QuestionType; options: string[] | null };
  /** Controlled answer text (the store keeps it, so a timer expiry can still save a draft). */
  value: string;
  onChange: (value: string) => void;
  onSubmit: (answer: string) => Promise<void>;
  isSubmitting: boolean;
}

const PLACEHOLDERS: Record<QuestionType, string> = {
  multiple_choice: "",
  short_answer: "Write your answer here...",
  scenario: "Describe what you would investigate, in order, and why...",
  troubleshooting: "Walk through your investigation: what you check first, which commands/tools, and why...",
  command: "Type the command (and a short note on what it does)...",
};

export function QuestionCard({ question, value, onChange, onSubmit, isSubmitting }: QuestionCardProps) {
  const isChoice = question.type === "multiple_choice" && !!question.options;
  const canSubmit = value.trim().length > 0 && value.length <= MAX_ANSWER_LENGTH && !isSubmitting;

  async function handleSubmit() {
    if (!canSubmit) return;
    await onSubmit(value);
  }

  return (
    <div className="space-y-4">
      <p className="whitespace-pre-wrap text-base font-medium leading-relaxed text-text-primary">
        {question.question}
      </p>

      {isChoice ? (
        <div className="space-y-2" role="radiogroup" aria-label="Answer options">
          {question.options!.map((option, idx) => {
            const letter = String.fromCharCode(65 + idx);
            const isSelected = value === option;
            return (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={isSelected}
                disabled={isSubmitting}
                onClick={() => onChange(option)}
                className={`flex w-full items-center gap-3 rounded-[var(--radius-panel)] border px-3.5 py-2.5 text-left text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                  isSelected
                    ? "border-signal bg-signal/10 text-text-primary"
                    : "border-border bg-surface-raised text-text-secondary hover:border-border-strong"
                }`}
              >
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-medium ${
                    isSelected ? "border-signal bg-signal text-[#08120f]" : "border-border-strong text-text-muted"
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
        <div>
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={isSubmitting}
            rows={question.type === "command" ? 3 : 6}
            maxLength={MAX_ANSWER_LENGTH}
            placeholder={PLACEHOLDERS[question.type]}
            aria-label="Your answer"
            spellCheck={question.type !== "command"}
            className={`w-full resize-y rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3.5 py-2.5 text-sm text-text-primary placeholder:text-text-muted disabled:cursor-not-allowed disabled:opacity-60 ${
              question.type === "command" ? "font-mono" : ""
            }`}
          />
          <p className="mt-1 text-right text-[11px] text-text-muted">
            {value.length}/{MAX_ANSWER_LENGTH}
          </p>
        </div>
      )}

      <div className="flex items-center justify-end gap-3">
        {isSubmitting && <span className="text-xs text-text-muted">Evaluating…</span>}
        <Button onClick={() => void handleSubmit()} disabled={!canSubmit}>
          {isSubmitting ? "Evaluating…" : "Submit Answer"}
        </Button>
      </div>
    </div>
  );
}
