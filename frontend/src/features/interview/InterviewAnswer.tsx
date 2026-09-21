import { useState } from "react";
import { Button } from "@/components/ui/button";
import { InputModeToggle } from "@/features/voice/InputModeToggle";
import { VoiceControls } from "@/features/voice/VoiceControls";
import type { InputMode, SendMessageOptions } from "@/features/voice/voiceTypes";
import { isVoiceSupported } from "@/hooks/useVoice";

const MAX_ANSWER_LENGTH = 10_000;

interface InterviewAnswerProps {
  inputMode: InputMode;
  onInputModeChange: (mode: InputMode) => void;
  isSubmitting: boolean;
  /** Rejects on failure; the answer stays in the box so it can be retried. */
  onSubmit: (answer: string, options?: SendMessageOptions) => Promise<void>;
}

/**
 * The answer area. Text mode is a textarea; voice mode reuses the Step 8
 * recording -> transcript preview (edit / send / discard) flow unchanged.
 */
export function InterviewAnswer({ inputMode, onInputModeChange, isSubmitting, onSubmit }: InterviewAnswerProps) {
  const [text, setText] = useState("");
  const voiceSupported = isVoiceSupported();
  const trimmed = text.trim();

  async function handleSubmit() {
    if (!trimmed || isSubmitting) return;
    try {
      await onSubmit(trimmed);
      setText("");
    } catch {
      // The store shows the error; keep the answer so the user can retry.
    }
  }

  return (
    <div className="space-y-3 border-t border-border pt-4">
      <div className="flex items-center justify-between">
        <label htmlFor="interview-answer" className="text-xs font-medium text-text-muted">
          Your Answer:
        </label>
        <InputModeToggle
          value={inputMode}
          onChange={onInputModeChange}
          voiceSupported={voiceSupported}
          disabled={isSubmitting}
        />
      </div>

      {inputMode === "voice" ? (
        <VoiceControls onSendVoice={onSubmit} isSending={isSubmitting} />
      ) : (
        <>
          <textarea
            id="interview-answer"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            maxLength={MAX_ANSWER_LENGTH}
            disabled={isSubmitting}
            placeholder="Type your answer…"
            className="w-full resize-y rounded-[var(--radius-panel)] border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted disabled:opacity-60"
          />
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-text-muted">
              {text.length.toLocaleString()} / {MAX_ANSWER_LENGTH.toLocaleString()}
            </span>
            <Button onClick={() => void handleSubmit()} disabled={!trimmed || isSubmitting}>
              {isSubmitting ? "Submitting…" : "Submit Answer"}
            </Button>
          </div>
        </>
      )}

      {isSubmitting && (
        <p className="text-xs text-text-muted" role="status" aria-live="polite">
          The interviewer is considering your answer…
        </p>
      )}
    </div>
  );
}
