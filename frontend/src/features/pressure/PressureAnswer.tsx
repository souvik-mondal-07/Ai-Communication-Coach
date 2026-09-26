import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { InputModeToggle } from "@/features/voice/InputModeToggle";
import { VoiceControls } from "@/features/voice/VoiceControls";
import type { InputMode, SendMessageOptions } from "@/features/voice/voiceTypes";
import { isVoiceSupported } from "@/hooks/useVoice";

const MAX_ANSWER_LENGTH = 10_000;

interface SubmitExtras extends SendMessageOptions {
  timedOut?: boolean;
}

interface PressureAnswerProps {
  inputMode: InputMode;
  onInputModeChange: (mode: InputMode) => void;
  isSubmitting: boolean;
  /** Rejects on failure; the answer stays in the box so it can be retried. */
  onSubmit: (answer: string, options?: SubmitExtras) => Promise<void>;
  /** True once the on-screen timer has hit zero for this prompt. */
  timedOut: boolean;
}

/**
 * The answer area for a pressure prompt. Text mode auto-submits (as a timeout,
 * never silently discarded) the moment the timer expires — whatever the user
 * had typed, or nothing at all. Voice mode reuses the Step 8 recording flow
 * unchanged; an in-progress recording is not cut off by the timer.
 */
export function PressureAnswer({ inputMode, onInputModeChange, isSubmitting, onSubmit, timedOut }: PressureAnswerProps) {
  const [text, setText] = useState("");
  const voiceSupported = isVoiceSupported();
  const trimmed = text.trim();
  const autoSubmitted = useRef(false);

  useEffect(() => {
    autoSubmitted.current = false;
  }, [inputMode]);

  useEffect(() => {
    if (timedOut && inputMode === "text" && !autoSubmitted.current && !isSubmitting) {
      autoSubmitted.current = true;
      void onSubmit(trimmed, { timedOut: true }).then(() => setText(""));
    }
    // Only re-run when the timeout flag flips — not on every keystroke.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timedOut]);

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
        <label htmlFor="pressure-answer" className="text-xs font-medium text-text-muted">
          Your Answer:
        </label>
        <InputModeToggle
          value={inputMode}
          onChange={onInputModeChange}
          voiceSupported={voiceSupported}
          disabled={isSubmitting || timedOut}
        />
      </div>

      {inputMode === "voice" ? (
        <VoiceControls onSendVoice={onSubmit} isSending={isSubmitting} disabled={timedOut} />
      ) : (
        <>
          <textarea
            id="pressure-answer"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            maxLength={MAX_ANSWER_LENGTH}
            disabled={isSubmitting || timedOut}
            placeholder={timedOut ? "Time's up — submitting…" : "Type your answer…"}
            className="w-full resize-y rounded-[var(--radius-panel)] border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted disabled:opacity-60"
          />
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-text-muted">
              {text.length.toLocaleString()} / {MAX_ANSWER_LENGTH.toLocaleString()}
            </span>
            <Button onClick={() => void handleSubmit()} disabled={!trimmed || isSubmitting || timedOut}>
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
