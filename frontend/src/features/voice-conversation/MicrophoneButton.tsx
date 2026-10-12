import { Loader2, Mic, MicOff, Square } from "lucide-react";
import { cn } from "@/lib/utils";

export type MicButtonState = "start" | "requesting" | "listening" | "transcribing" | "processing" | "disabled";

interface MicrophoneButtonProps {
  state: MicButtonState;
  onStart: () => void;
  onStop: () => void;
  /** Why the button is disabled (shown to screen readers and as a tooltip). */
  disabledReason?: string;
}

const LABELS: Record<MicButtonState, string> = {
  start: "Start recording your answer",
  requesting: "Waiting for microphone permission",
  listening: "Stop recording. Your answer is transcribed automatically",
  transcribing: "Transcribing your answer",
  processing: "Processing your answer",
  disabled: "Microphone unavailable",
};

/**
 * One large control for the whole answer cycle. State is conveyed by the icon,
 * the visible caption and the accessible label, never by colour alone. It is a
 * native <button>, so Enter/Space work and focus is visible.
 */
export function MicrophoneButton({ state, onStart, onStop, disabledReason }: MicrophoneButtonProps) {
  const isBusy = state === "requesting" || state === "transcribing" || state === "processing";
  const isDisabled = state === "disabled" || isBusy;
  const label = state === "disabled" && disabledReason ? disabledReason : LABELS[state];
  const caption =
    state === "start"
      ? "Tap to answer"
      : state === "requesting"
        ? "Allow the microphone…"
        : state === "listening"
          ? "Tap when you're done"
          : state === "transcribing"
            ? "Transcribing..."
            : state === "processing"
              ? "Processing..."
              : "Unavailable";

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={state === "listening" ? onStop : onStart}
        disabled={isDisabled}
        aria-label={label}
        title={label}
        aria-pressed={state === "listening"}
        aria-busy={isBusy}
        className={cn(
          "relative flex h-20 w-20 items-center justify-center rounded-full border-2 transition-[background-color,border-color,color,box-shadow,transform] duration-200 active:scale-95",
          "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-signal/50 focus-visible:ring-offset-2 focus-visible:ring-offset-base",
          "disabled:cursor-not-allowed",
          state === "start" && "border-signal bg-signal text-on-signal hover:bg-signal/90",
          state === "listening" && "border-danger bg-danger text-white shadow-[0_0_28px_-4px_rgb(255_122_133/0.7)] hover:bg-danger/90",
          isBusy && "border-border-strong bg-surface-raised text-text-secondary",
          state === "disabled" && "border-border bg-surface text-text-muted"
        )}
      >
        {/* Only rendered while the recorder is actually running. */}
        {state === "listening" && (
          <>
            <span aria-hidden="true" className="animate-mic-ring pointer-events-none absolute -inset-0.5 rounded-full border-2 border-danger/70 motion-reduce:hidden" />
            <span aria-hidden="true" className="animate-mic-ring pointer-events-none absolute -inset-0.5 rounded-full border-2 border-danger/50 [animation-delay:800ms] motion-reduce:hidden" />
          </>
        )}
        {state === "start" && <Mic size={30} aria-hidden="true" />}
        {state === "listening" && <Square size={26} fill="currentColor" aria-hidden="true" />}
        {isBusy && <Loader2 size={28} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />}
        {state === "disabled" && <MicOff size={28} aria-hidden="true" />}
      </button>
      <span className="text-xs font-medium text-text-secondary" aria-hidden="true">
        {caption}
      </span>
    </div>
  );
}
